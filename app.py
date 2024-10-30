import logging
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader

from htmlTemplates import css, bot_template, user_template

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)

logger = logging.getLogger(__name__)


def load_files(files):
    logger.info("Loading files...")
    text = ""

    for file in files:
        file_path = os.path.join("docs/", file.name)
        loader = UnstructuredLoader(file_path)
        docs = loader.load()

        for doc in docs:
            text += doc.page_content

    return text

def get_text_chunks(text):
    logger.info("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=7500, chunk_overlap=100)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks, embedding):
    logger.info("Creating vectorstore...")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embedding)
    return vectorstore

def get_conversation_chain(vectorstore):
    logger.info("Get conversation chain...")

    llm = ChatOllama(model="llama3", temperature=0)

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple files",
                       page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Chat with multiple files :books:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your documents")
        files = st.file_uploader(
            "Upload your files here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing"):
                # get pdf text
                raw_text = load_files(files)

                # get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # create vector store
                embedding = OllamaEmbeddings(model="nomic-embed-text")
                vectorstore = get_vectorstore(text_chunks, embedding)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)


if __name__ == '__main__':
    main()