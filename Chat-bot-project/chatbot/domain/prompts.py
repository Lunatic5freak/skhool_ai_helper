from langchain_core.prompts import ChatPromptTemplate

from chatbot.domain.policies import SYSTEM_POLICIES

SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_POLICIES),
    ("human", "{input}")
])
