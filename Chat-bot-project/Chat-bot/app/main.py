import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from app.database import DatabaseManager
from app.llm_services import LLMService
from app.agents import SQLAgent, DirectSQLGenerator
from app.models import ChatRequest, ChatResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db_manager = DatabaseManager()
llm_service = LLMService(db_manager)
sql_agent = SQLAgent(db_manager, llm_service)
direct_generator = DirectSQLGenerator(db_manager, llm_service)

app = FastAPI(
    title="AI SQL Chatbot with Multi-Stage Query Processing",
    description="Advanced chatbot using LangChain for intelligent SQL query generation and execution",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "AI SQL Chatbot with Multi-Stage Query Processing",
        "version": "3.0.0",
        "architecture": {
            "database": "SQLite with comprehensive e-commerce schema",
            "llm": "OpenAI GPT via LangChain",
            "agent": "ReAct agent with tool-based architecture",
            "tools": [
                "Schema Lookup",
                "Query Executor",
                "Sample Data",
                "SQL Generator",
                "Data Analyzer",
                "Multi-Stage Query Planner"
            ]
        },
        "endpoints": {
            "health": "/health",
            "chat_agent": "/chat/agent (POST) - Intelligent agent with tools",
            "chat_direct": "/chat/direct (POST) - Direct SQL generation",
            "tables": "/tables",
            "schema": "/schema/{table_name}",
            "sample": "/sample/{table_name}"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "llm_service": "connected" if llm_service else "disconnected",
        "agent": "initialized" if sql_agent else "not_initialized"
    }


@app.post("/chat/agent", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat endpoint using intelligent agent with tools for multi-stage query processing
    """
    try:
        logger.info(f"Agent chat - User {request.user_id}: {request.message}")

        result = sql_agent.process_query(request.message, request.user_id)

        return ChatResponse(
            response=result["response"],
            sql_query=result.get("sql_queries", [""])[0] if result.get("sql_queries") else None,
            data=result.get("data"),
            session_id=request.session_id or f"agent_{request.user_id}",
            timestamp=datetime.now().isoformat(),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Agent chat error: {str(e)}")
        return ChatResponse(
            response=f"Error: {str(e)}",
            session_id=request.session_id or "error",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@app.post("/chat/direct", response_model=ChatResponse)
async def chat_direct(request: ChatRequest):
    """
    Chat endpoint using direct SQL generation (simpler, faster)
    """
    try:
        logger.info(f"Direct chat - User {request.user_id}: {request.message}")

        result = direct_generator.process_query(request.message, request.user_id)

        return ChatResponse(
            response=result["response"],
            sql_query=result.get("sql_query"),
            data=result.get("data"),
            session_id=request.session_id or f"direct_{request.user_id}",
            timestamp=datetime.now().isoformat(),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Direct chat error: {str(e)}")
        return ChatResponse(
            response=f"Error: {str(e)}",
            session_id=request.session_id or "error",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@app.get("/tables")
async def get_tables():
    """Get list of all tables"""
    schema = db_manager.get_table_schema()
    return {"tables": list(schema.keys())}


@app.get("/schema/{table_name}")
async def get_table_schema(table_name: str):
    """Get schema for specific table"""
    try:
        schema = db_manager.get_table_schema(table_name)
        return schema
    except:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")


@app.get("/sample/{table_name}")
async def get_sample_data(table_name: str, limit: int = 5):
    """Get sample data from table"""
    try:
        data = db_manager.get_sample_data(table_name, limit)
        return {
            "table": table_name,
            "limit": limit,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/query")
async def run_custom_query(query: str):
    """Execute custom SQL query (for testing)"""
    try:
        if not query.strip().upper().startswith("SELECT"):
            raise HTTPException(status_code=400, detail="Only SELECT queries allowed")

        data = db_manager.execute_query(query)
        return {
            "query": query,
            "count": len(data),
            "data": data[:100]  # Limit response size
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )