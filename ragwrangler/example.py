from typing import Callable
import openai
import os
from weaviate.util import generate_uuid5
import weaviate
import db
import prompts
import utils
import logging


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


GPT_MODELS = ["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"]
ALL_MODELS = GPT_MODELS

openai.api_key = os.environ["OPENAI_APIKEY"]


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

with open("./../doc/test.txt", "r") as f:
    test_source_text = f.read()


def revision_quiz_json_builder(source_text: str) -> str:
    """
    Generate a revision quiz in JSON form.
    :param source_text: The source text to be used.
    :return: The generated quiz; should be parsable into valid JSON.
    """
    prompt = """
        Write a set of multiple-choice quiz questions with three to four options each 
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

        [
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


quiz_rag = RAGTask(task_prompt_builder=revision_quiz_json_builder)
summary_rag = RAGTask(task_prompt_builder=plaintext_summary_builder)
glossary_rag = RAGTask(task_prompt_builder=get_glossary_builder)

for rag_task in [quiz_rag, summary_rag, glossary_rag]:
    output = rag_task.get_output(source_text=test_source_text)
    print(output)
    # print(utils.truncate_text(str(output), max_length=200))