import json
import chat
import streamlit as st
import os
from rag import *


#Creating the chatbot interface
st.markdown("# inQUIZitive")
st.markdown("###### :disguised_face: :robot_face:  in•quis•i•tive | inˈkwizədiv, iNGˈkwizədiv  :robot_face: :disguised_face:")
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
            input_text = st.chat_input("Ask a question!")
            return input_text

        user_input = get_text()

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message['content'] != user_input:
                    st.markdown(message["content"])

        if user_input:
            output = chat.answer(user_input, docsearch)
            st.session_state.messages.append({"role": "user", "content": user_input})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(user_input)

            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                for char in output:
                    full_response += char
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

