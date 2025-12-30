from chatbot.domain.agent import build_agent

agent = build_agent()

def test_agent_returns_string():
    result = agent.invoke({"input": "Hello"})
    assert isinstance(result["output"], str)

def test_agent_no_reasoning_leak():
    result = agent.invoke({"input": "How many users are there?"})
    output = result["output"].lower()

    forbidden = ["thinking", "sql", "query", "tool"]

    for word in forbidden:
        assert word not in output
