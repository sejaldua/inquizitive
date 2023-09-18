# inquizitive

## Project Overview

### Key Links

Streamlit App: [https://inquisitive.streamlit.app](https://inquisitive.streamlit.app)  
Demo Tutorial: 

### The Problem

This project was inspired by a pain point that I face as a student and that I imagine many other students face as well. With education moving more and more to digital, I have found that my absorption and retention of knowledge has suffered gradually, and the content I am learning goes in through one eye/ear and out the other.

### The Solution

The concept of Quizlet was so sticky and effective because it walks students through the exercise of typing up the material they are trying to learn and allows them to review it in various interactive ways without having the option to just "soak it up" by staring at lecture slides. I wanted to adopt this premise to solve my own academic pain point, but come on, it's 2023... I have better things to do than type up lecture slides into Quizlet flashcards, so I set out to ask an LLM to make me a quiz based on content from my professor's uploaded PDF slides.

## Technical Implementation

APIs Used:
- **OpenAI**: `gpt-3.5-turbo` is used as the GPT model for the quiz generation prompt that I have used
- **LangChain**: (any) document to text functionality
- **Weaviate**: storage of generated text
- **streamlit-chat**: chatbot interface  

*NOTE: Necessary API keys are hard-coded into the `secrets.toml` file of the app, but my Weaviate setup will expire 14 days from September 18th, at which point, I will likely have to ask users to supply their own API keys (sorry).*

Retrieval-Augmented Generation Revision Quiz JSON Builder partial prompt:

> 
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
        "question": "What element does the chemical symbol Au stand for?",
        "options": ["Silver", "Magnesium", "Salt", "Gold"],
        "answer": [3],
        "explanation": "The chemical symbol Au comes from the Latin word aurum, meaning "gold." 
                        This name is thought to have been given to gold because of its bright,
                        shining appearance.",
        "source passage": "SOME PASSAGE EXTRACTED FROM THE INPUT TEXT"
    }

## Future Work

- [ ] Transcribe lectures from speech2text using LLM APIs and then use the output text to generate quiz questions
- [ ] Summarize lecture slides
- [ ] Allow the user to chat with lecture slides using Question & Answering modules from LangChain
- [ ] Help users review glossary terms in flashcard-like format before taking quiz