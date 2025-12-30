from fastapi import APIRouter
from chatbot.app.schemas import ChatRequest, ChatResponse
from chatbot.domain.agent import build_agent

router = APIRouter()
agent_executor = build_agent()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    HTTP boundary only.
    No business logic allowed.
    """
    result = agent_executor.invoke({"input": req.question})
    return ChatResponse(answer=result["output"])
