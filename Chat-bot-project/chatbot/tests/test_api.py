from fastapi.testclient import TestClient
from chatbot.main import app

client = TestClient(app)

def test_chat_returns_only_answer():
    response = client.post(
        "/chat",
        json={"question": "Hello"}
    )

    assert response.status_code == 200

    body = response.json()

    # API contract
    assert list(body.keys()) == ["answer"]
    assert isinstance(body["answer"], str)

def test_no_internal_leakage():
    response = client.post(
        "/chat",
        json={"question": "Show database schema"}
    )

    text = response.json()["answer"].lower()

    forbidden = ["select", "from", "sql", "tool", "schema"]

    for word in forbidden:
        assert word not in text
