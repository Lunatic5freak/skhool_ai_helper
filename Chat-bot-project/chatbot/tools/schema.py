from langchain.tools import tool
from langchain_community.utilities import SQLDatabase
from chatbot.infra.settings import settings

db = SQLDatabase.from_uri(settings.DATABASE_URL)

@tool("sql_schema_tool")
def get_schema(_: str = "") -> str:
    """
    Provides database schema to the agent.
    Prevents hallucinated table/column names.
    """
    return db.get_table_info()
