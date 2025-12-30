from chatbot.tools.sql import execute_sql

def test_sql_tool_blocks_writes():
    result = execute_sql("DROP TABLE users")
    assert "only select" in result.lower()

def test_sql_tool_allows_select():
    result = execute_sql("SELECT 1")
    assert result is not None
