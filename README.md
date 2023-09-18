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
- LangChain for document to text functionality
- Weaviate for storage of output
- Streamlit Chat for chatbot interface

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
        "question": "What is the capital of France?",
        "options": ["Paris", "London", "Berlin", "Madrid"],
        "answer": [0],
        "explanation": "Paris is the capital of France",
        "source passage": "SOME PASSAGE EXTRACTED FROM THE INPUT TEXT"
    }

## Future Work

- [ ] Transcribe lectures from speech2text using LLM APIs and then use the output text to generate quiz questions
- [ ] Summarize lecture slides
- [ ] Allow the user to chat with lecture slides using Question & Answering modules from LangChain
- [ ] Help users review glossary terms in flashcard-like format before taking quiz