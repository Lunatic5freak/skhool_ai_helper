from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: Any
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    session_id: str
    timestamp: str


class SQLQuery(BaseModel):
    query: str
    parameters: Optional[List[Any]] = None
    explanation: Optional[str] = None


class DatabaseSchema(BaseModel):
    tables: Dict[str, List[Dict[str, str]]]


class QueryPlan(BaseModel):
    steps: List[str]
    final_query: str
    intermediate_results: List[Dict[str, Any]]