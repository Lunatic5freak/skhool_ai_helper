from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from chatbot.infra.settings import settings

_vectorstore = None  # module-level cache

def load_vectorstore():
    global _vectorstore

    if _vectorstore is not None:
        return _vectorstore

    if not settings.VECTORSTORE_PATH.exists():
        raise RuntimeError(
            "Vectorstore not found. Run ingestion/ingest_documents.py first."
        )

    embeddings = OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY
    )

    _vectorstore = FAISS.load_local(
        settings.VECTORSTORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return _vectorstore
