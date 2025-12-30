from chatbot.infra.vectorstore import load_vectorstore

def retrieve_docs(query: str) -> str:
    vectorstore = load_vectorstore()
    docs = vectorstore.similarity_search(query, k=3)
    return "\n".join(d.page_content for d in docs)
