from langchain.tools import tool
from langchain_community.utilities import SQLDatabase


from chatbot.infra.settings import settings

db = SQLDatabase.from_uri(settings.DATABASE_URL)

@tool("sql_query_tool")
def execute_sql(query: str) -> str:
    """
    Executes READ-ONLY SQL queries.
    The agent controls usage.
    """
    q = query.lower().strip()
    if not q.startswith("select"):
        return "Only SELECT queries are allowed."

    return db.run(query)
