import json
import chat
import streamlit as st
from streamlit_chat import message
from typing import Callable
import openai
import os
from weaviate.util import generate_uuid5
import weaviate
from rag import db
from rag import prompts
from rag import utils
import logging


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


GPT_MODELS = ["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"]
ALL_MODELS = GPT_MODELS

openai.api_key = st.secrets["OPENAI_APIKEY"]


class RAGTask:
    """
    A class representing a task to be handled by the RAG system.

    Attributes:
        task_prompt_builder (str): A function to build the task prompt using the source text.
        generated_text (str): The text generated as output for the task.
    """
    def __init__(self, task_prompt_builder: Callable[[str], str], client: weaviate.Client = None):
        if not callable(task_prompt_builder):
            raise ValueError('task_prompt_builder must be a callable function')
        self.task_prompt_builder = task_prompt_builder
        self.generated_text = None
        if client is None:
            self.client = db.initialize()
        else:
            self.client = client

    def get_output(self, source_text: str, model_name: str = "gpt-3.5-turbo", overwrite: bool = False) -> str:
        """
        Get the output for the task, either by generating it or fetching from Weaviate.
        :param source_text: The source text based on which the task is created.
        :param model_name: The name of the model to use for generating output.
        :param overwrite: Whether to overwrite the output if it already exists in Weaviate.
        :return: The generated output.
        """

        task_prompt = self.task_prompt_builder(source_text)
        uuid = generate_uuid5(task_prompt)

        # Check if the output can be fetched from Weaviate using the UUID
        fetched_object = db.load_generated_text(self.client, uuid)
        if fetched_object is not None:
            logger.info(f"Found {uuid} in Weaviate")
            if overwrite:
                logger.info(f"Overwrite is true. Deleting object {uuid} in Weaviate")
                self.client.data_object.delete(uuid, class_name=db.OUTPUT_COLLECTION)
                logger.info(f"Deleted {uuid} in Weaviate")
            else:
                return fetched_object
        else:
            logger.warning(f"Could not find {uuid} in Weaviate")

            # Check if there are any similar objects in Weaviate based on vector similarity
            similar_objects = db.find_similar_objects(self.client, task_prompt, similarity_theshold=0.95)
            if similar_objects:
                logger.info(f"Found similar object(s) in Weaviate with similarity above threshold")
                logger.info(f"UUID: {similar_objects[0]['_additional']['id']}")
                logger.info(f"Distance: {similar_objects[0]['_additional']['distance']}")
                # Load the most similar object
                most_similar_object = similar_objects[0]
                return most_similar_object["generated_text"]

        # Generate output using the specified model and save it to Weaviate
        logger.info(f"Generating output for {utils.truncate_text(task_prompt)}")
        generated_text = call_llm(task_prompt, model_name=model_name)
        uuid = db.save_generated_text(self.client, task_prompt, generated_text, uuid)
        logger.info(f"Saved {uuid} to Weaviate")
        return generated_text


def call_llm(prompt: str, model_name: str = "gpt-3.5-turbo") -> str:
    """
    Call the language model with a specific prompt and model name.
    :param prompt: The prompt to be used.
    :param model_name: The name of the model to be used.
    :return: The output from the language model.
    """
    logger.info(f"Calling {model_name} with prompt: {utils.truncate_text(prompt)}")
    if model_name not in ALL_MODELS:
        raise ValueError(f"Model name {model_name} not recognised")

    if "gpt" in model_name:
        return call_chatgpt(prompt, model_name)
    else:
        raise ValueError(f"No function exists to handle for model {model_name}")


def call_chatgpt(prompt: str, model_name: str = "gpt-3.5-turbo") -> str:
    """
    Call the ChatGPT model with a specific prompt.
    :param prompt: The prompt to be used.
    :param model_name: The name of the model to be used.
    :return:
    """

    completion = openai.ChatCompletion.create(
        model=model_name,
        messages=[
            prompts.SYSTEM_PROMPTS["Default"],
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return completion.choices[0].message["content"]

def revision_quiz_json_builder(source_text: str) -> str:
    """
    Generate a revision quiz in JSON form.
    :param source_text: The source text to be used.
    :return: The generated quiz; should be parsable into valid JSON.
    """
    prompt = """
        Write a set of multiple-choice quiz questions with four options each 
        to review and internalise the following information.

        The quiz should be returned in a JSON format so that it can be displayed and undertaken by the user.
        The answer should be a list of integers corresponding to the indices of the correct answers.
        If there is only one correct answer, the answer should be a list of one integer.
        Also return an explanation for each answer, and a quote from the source text to support the answer.

        The goal of the quiz is to provide a revision exercise, 
        so that the user can internalise the information presented in this passage.
        The quiz questions should only cover information explicitly presented in this passage. 
        The number of questions can be anything from one to 10, depending on the volume of information presented.     

        Sample quiz question:

        {
            "question": "What is the capital of France?",
            "options": ["Paris", "London", "Berlin", "Madrid"],
            "answer": [0],
            "explanation": "Paris is the capital of France",
            "source passage": "SOME PASSAGE EXTRACTED FROM THE INPUT TEXT"
        }

        Sample quiz set:
        
        {
            "quiz": [
                {
                    "question": "What is the capital of France?",
                    "options": ["Paris", "London", "Berlin", "Madrid"],
                    "answer": [0],
                    "explanation": "Paris is the capital of France",
                    "source passage": "SOME PASSAGE EXTRACTED FROM THE INPUT TEXT"
                },
                {
                    "question": "What is the capital of Spain?",
                    "options": ["Paris", "London", "Berlin", "Madrid"],
                    "answer": [3],
                    "explanation": "Madrid is the capital of Spain",
                    "source passage": "SOME PASSAGE EXTRACTED FROM THE INPUT TEXT"
                }
            ]
        }
            

        ======= Source Text =======

        """ + source_text + """

        ======= Questions =======

    """
    return prompt


def plaintext_summary_builder(source_text: str) -> str:
    """
    Generate a plaintext summary of the source text.
    :param source_text: The source text to be used.
    :return: The summary.
    """
    prompt = f"""
    Summarize the following into bullet points that presents the core concepts.
    This should be in plain language that will help the reader best understand the core concepts,
    so that they can internalise the ideas presented in this passage.

    The bullet points should start at a high level,
    and nested to go into further details if necessary

    ==============

    {source_text}

    ==============

    Summary:

    """
    return prompt


def get_glossary_builder(source_text: str) -> str:
    prompt = f"""
    Return a glossary of key terms or jargon from the source text
    to help someone reading this material understand the text.
    Each explanation should be in as plain and clear language as possible.
    For this task, it is acceptable to rely on information outside of the source text.

    The output should be in the following Markdown format:

    - **TERM A**: EXPLANATION A 
    - **TERM B**: EXPLANATION B
    - ...

    ====== Source text =======

    {source_text}

    ====== Glossary =======

    """
    return prompt

#Creating the chatbot interface
st.markdown("# inQUIZitive")
st.markdown("###### 🥸🤖  in•quis•i•tive | inˈkwizədiv, iNGˈkwizədiv  🤖🥸")
st.caption("Your LLM-powered AI study buddy, here to help you review your study materials and increase knowledge retention through \
(1) summarization (2) glossary review (3) quizzes and (4) document question and answering")

mode =  st.sidebar.selectbox('Choose demonstration mode', ['Pre-loaded', 'Interactive'])
if mode == 'Pre-loaded':
    text, documents = chat.load_documents()
else:
    files = st.sidebar.file_uploader('Upload notes or lecture slides', accept_multiple_files=True, type=['pdf', 'docx', 'pptx', 'txt', 'md'])
    learning_files = files if files is not None else []
    text, documents = chat.load_documents(learning_files)

@st.cache_data()
def generate_quiz(text):

    test_source_text = text
    quiz_rag = RAGTask(task_prompt_builder=revision_quiz_json_builder)
    summary_rag = RAGTask(task_prompt_builder=plaintext_summary_builder)
    glossary_rag = RAGTask(task_prompt_builder=get_glossary_builder)

    outputs = []
    for rag_task in [quiz_rag, summary_rag, glossary_rag]:
        output = rag_task.get_output(source_text=test_source_text)
        outputs.append(output)
    
    return outputs

def decrement_question_num():
    if st.session_state['curr_question'] > 0:
        st.session_state['curr_question'] -= 1
        ClearAll()

def increment_question_num():
    print('Incrementing question', st.session_state['curr_question'])
    if st.session_state['curr_question'] < st.session_state['quiz_length'] - 1:
        st.session_state['curr_question'] += 1
        ClearAll()

page = st.selectbox('Select a study mode', ['Summary', 'Glossary', 'Quiz', 'Chatbot'], index=0)

if st.sidebar.button('Process Study Materials'):
    st.session_state['materials_processed'] = True
    st.session_state['curr_question'] = 0

if 'materials_processed' in st.session_state and st.session_state['materials_processed']:
    outputs = generate_quiz(text)
    
    # render summary page
    if page == 'Summary':
        summary = outputs[1]
        st.write(summary)

    # render glossary page
    elif page == 'Glossary':
        glossary = outputs[2]
        st.write(glossary)

    # render quiz page
    elif page == 'Quiz':
        try:
            quiz_json = json.loads(outputs[0])["quiz"]
            st.session_state['quiz_length'] = len(quiz_json)
            questions = [q['question'] for q in quiz_json]
            options = [q['options'] for q in quiz_json]
            answers = [q["answer"] for q in quiz_json]
            explanations = [q['explanation'] for q in quiz_json]
            
            # user selects which question they want to answer
            # question_num = st.number_input('Choose a question', min_value=1, max_value = len(quiz_json), value=1)
            question_num = st.session_state['curr_question']

            answer_choices = options[question_num]
            col1, col2 = st.columns(2)
            with col1:
                st.button('Previous Question', use_container_width=True, on_click=decrement_question_num)
            with col2:
                st.button('Next Question', use_container_width=True, on_click=increment_question_num)

            st.markdown(f"##### Question {question_num + 1} of {len(quiz_json)}: {questions[question_num]}")

            if 'a' not in st.session_state:
                st.session_state.a = 0
                st.session_state.b = 0
                st.session_state.c = 0
                st.session_state.d = 0

            def ChangeA():
                st.session_state.a,st.session_state.b,st.session_state.c,st.session_state.d = 1,0,0,0
            def ChangeB():
                st.session_state.a,st.session_state.b,st.session_state.c,st.session_state.d = 0,1,0,0
            def ChangeC():
                st.session_state.a,st.session_state.b,st.session_state.c,st.session_state.d = 0,0,1,0
            def ChangeD():
                st.session_state.a,st.session_state.b,st.session_state.c,st.session_state.d = 0,0,0,1
            def ClearAll():
                st.session_state.a,st.session_state.b,st.session_state.c,st.session_state.d = 0,0,0,0

            checkboxA = st.checkbox(answer_choices[0], value = st.session_state.a, on_change = ChangeA)
            checkboxB = st.checkbox(answer_choices[1], value = st.session_state.b, on_change = ChangeB)
            checkboxC = st.checkbox(answer_choices[2], value = st.session_state.c, on_change = ChangeC)
            checkboxD = st.checkbox(answer_choices[3], value = st.session_state.d, on_change = ChangeD)

            if st.session_state.a:
                user_answer = answer_choices[0]
            elif st.session_state.b:
                user_answer = answer_choices[1]
            elif st.session_state.c:
                user_answer = answer_choices[2]
            elif st.session_state.d:
                user_answer = answer_choices[3]
            else:
                user_answer = None

            if user_answer is not None:
                user_answer_num = answer_choices.index(user_answer)
                if st.button('Submit Answer', type='secondary'):
                    if user_answer_num == answers[question_num][0]:
                        st.success(f'Correct! {explanations[question_num]}')
                    else:
                        st.error(f'Incorrect :( \n\n The correct answer was: {answer_choices[answers[question_num][0]]}\n\n {explanations[question_num]}')
        except:
            st.info('Uh oh... could not generate a quiz for ya! Happy studying!')
        
        
    elif page == 'Chatbot':
        docsearch = chat.create_doc_embeddings(documents)

        # Storing the chat
        if 'generated' not in st.session_state:
            st.session_state['generated'] = []

        if 'past' not in st.session_state:
            st.session_state['past'] = []

        # Define a function to clear the input text
        def clear_input_text():
            global input_text
            input_text = ""

        # We will get the user's input by calling the get_text function
        def get_text():
            global input_text
            input_text = st.text_input("Ask a question! ", key="input", on_change=clear_input_text)
            return input_text

        user_input = get_text()

        if user_input:
            output = chat.answer(user_input, docsearch)
            st.session_state.past.append(user_input)
            st.session_state.generated.append(output)

        if st.session_state['generated']:
            for i in range(len(st.session_state['generated'])-1, -1, -1):
                message(st.session_state["generated"][i], key=str(i))
                message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')


