from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

from chatbot.domain.prompts import SYSTEM_PROMPT
from chatbot.tools.sql import execute_sql
from chatbot.tools.schema import get_schema
from chatbot.tools.retrieval import retrieve_docs

from langchain_openai import ChatOpenAI
from chatbot.infra.settings import settings

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)

def build_agent():
    """
    Single authoritative reasoning agent.
    Compatible with LangChain >= 0.2
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    tools = [
        get_schema,
        execute_sql,
        retrieve_docs
    ]

    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True
    )
