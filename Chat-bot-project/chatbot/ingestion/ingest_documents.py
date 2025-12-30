from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from chatbot.infra.settings import settings

DOCS_PATH = Path("Chat-bot-project/chatbot/data/documents")
VECTORSTORE_PATH = Path(settings.VECTORSTORE_PATH)

def ingest():
    loader = DirectoryLoader(
        path=DOCS_PATH,
        glob="**/*",
        loader_cls=TextLoader
    )

    documents = loader.load()

    embeddings = OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY
    )

    vectorstore = FAISS.from_documents(
        documents,
        embeddings
    )

    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(VECTORSTORE_PATH)

    print("✅ Vectorstore created successfully")

if __name__ == "__main__":
    ingest()
