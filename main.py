"""
FastAPI service for School Management Chatbot.
"""
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from config import get_settings
from auth import get_auth_service, AuthService, AuthPayload
from database import get_db_service, DatabaseService
from agent import create_chatbot_agent, SchoolChatbotAgent
from models import UserRole

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic Models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("Starting School Management Chatbot Service")
    
    # Initialize database
    db_service = get_db_service()
    await db_service.initialize_public_schema()
    logger.info("Database initialized")
    
    yield
    
    # Cleanup
    await db_service.close()
    logger.info("Shutting down School Management Chatbot Service")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered chatbot for school management with RBAC and multi-tenant support",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Extract auth from JWT
async def get_current_user(
    authorization: str = Header(..., description="Bearer token")
) -> AuthPayload:
    """
    Extract and validate user from JWT token.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        AuthPayload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Extract token
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'"
            )
        
        token = authorization.replace("Bearer ", "")
        
        # Decode token
        auth_service = get_auth_service()
        auth_payload = auth_service.decode_token(token)
        
        if not auth_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        logger.info(f"Authenticated user: {auth_payload.email} ({auth_payload.role})")
        return auth_payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# Dependency: Create chatbot agent
async def get_agent(
    auth: AuthPayload = Depends(get_current_user)
) -> SchoolChatbotAgent:
    """
    Create chatbot agent for the authenticated user.
    
    Args:
        auth: Authentication payload
        
    Returns:
        SchoolChatbotAgent instance
    """
    try:
        agent = create_chatbot_agent(
            schema_name=auth.schema_name,
            auth_payload=auth
        )
        return agent
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize chatbot agent"
        )


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "School Management Chatbot API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version
    )


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def chat(
    request: ChatRequest,
    agent: SchoolChatbotAgent = Depends(get_agent),
    auth: AuthPayload = Depends(get_current_user)
):
    """
    Chat with the school management assistant.
    
    This endpoint allows authenticated users to interact with the chatbot.
    The chatbot respects RBAC rules and only returns data the user has permission to access.
    
    - **Students** can query their own academic data, attendance, and performance
    - **Teachers** can access their students' data and class statistics
    - **Admins** have full access to all school data
    
    Args:
        request: Chat request with user message
        agent: Chatbot agent (injected by dependency)
        auth: Authentication payload (injected by dependency)
        
    Returns:
        ChatResponse with agent's reply
    """
    try:
        logger.info(f"Chat request from {auth.email}: {request.message[:100]}")
        
        # Get response from agent
        response = await agent.chat(request.message)
        
        logger.info(f"Generated response for {auth.email}")
        
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request"
        )


@app.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(auth: AuthPayload = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Returns basic information about the authenticated user including:
    - User ID
    - Email
    - Role
    - Tenant schema
    - Student/Teacher ID (if applicable)
    """
    return {
        "user_id": auth.user_id,
        "email": auth.email,
        "role": auth.role,
        "schema_name": auth.schema_name,
        "student_id": auth.student_id,
        "teacher_id": auth.teacher_id
    }


@app.get("/permissions", response_model=Dict[str, Any])
async def get_user_permissions(auth: AuthPayload = Depends(get_current_user)):
    """
    Get permissions for the current user based on their role.
    
    Returns a list of actions the user is authorized to perform.
    """
    from auth import RBACService
    
    role = UserRole(auth.role)
    permissions = RBACService.PERMISSIONS.get(role, set())
    
    return {
        "role": role.value,
        "permissions": list(permissions)
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.debug else None
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
