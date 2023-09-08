import chat
import streamlit as st
from streamlit_chat import message

#Creating the chatbot interface
st.title("Core Competency Chatbot")
st.subheader("Job Description to Resume Virtual Assistant")

mode =  st.sidebar.selectbox('Choose demonstration mode', ['Pre-loaded', 'Interactive'])
if mode == 'Pre-loaded':
    docsearch = chat.load_documents()
else:
    R = st.sidebar.file_uploader('Upload a resume', accept_multiple_files=True)
    JD = st.sidebar.file_uploader('Upload a job description', accept_multiple_files=True)
    resume_files = R if R is not None else []
    jd_files = JD if JD is not None else []
    docsearch = chat.load_documents([*resume_files, *jd_files])

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

def main():
    user_input = get_text()

    if user_input:
        output = chat.answer(user_input, docsearch)
        st.session_state.past.append(user_input)
        st.session_state.generated.append(output)

    if st.session_state['generated']:
        for i in range(len(st.session_state['generated'])-1, -1, -1):
            message(st.session_state["generated"][i], key=str(i))
            message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')

# Run the app
if __name__ == "__main__":
    main()

