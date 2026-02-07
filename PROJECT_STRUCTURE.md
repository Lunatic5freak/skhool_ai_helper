# School Management Chatbot - Project Structure

```
school_chatbot/
│
├── README.md                    # Comprehensive documentation
├── requirements.txt             # Python dependencies
├── .env.template               # Environment variables template
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-container orchestration
│
├── config.py                   # Configuration management with Pydantic
├── models.py                   # SQLAlchemy database models
├── database.py                 # Database service with multi-tenant support
├── auth.py                     # Authentication & RBAC service
├── db_tools.py                 # Database query tools for the agent
├── agent.py                    # LangGraph-based chatbot agent
├── main.py                     # FastAPI application
│
├── init_db.py                  # Database initialization script
├── test_client.py              # Test client for API testing
│
└── tests/                      # Test suite (to be created)
    ├── __init__.py
    ├── test_auth.py
    ├── test_agent.py
    ├── test_api.py
    └── test_database.py
```

## File Descriptions

### Core Application Files

**config.py**
- Pydantic settings management
- Environment variable handling
- Configuration validation
- Database URL construction

**models.py**
- SQLAlchemy ORM models
- Multi-tenant schema support
- User, Student, Teacher, Class, Subject models
- ExamResult, Attendance models
- Enums for roles, attendance status, exam types

**database.py**
- Async database service
- Multi-tenant schema isolation
- Session management with context managers
- Schema creation and validation
- Connection pooling

**auth.py**
- JWT token creation and validation
- Password hashing with bcrypt
- RBAC (Role-Based Access Control) service
- Permission checking logic
- Token payload extraction

**db_tools.py**
- Database query tools for the agent
- RBAC-aware data access methods
- Student info retrieval
- Attendance reporting
- Exam results queries
- Performance analysis
- Recommendation generation

**agent.py**
- LangGraph-based multi-step agent
- Tool creation and binding
- Agent state management
- Workflow definition (agent → tools → response)
- Role-specific system prompts
- Tool execution and orchestration

**main.py**
- FastAPI application setup
- API endpoints (chat, health, user info, permissions)
- Authentication middleware
- CORS configuration
- Error handling
- Request/response models

### Utility Files

**init_db.py**
- Database initialization script
- Creates demo tenant
- Populates sample data
- Creates admin, teacher, student users
- Generates exam results and attendance records

**test_client.py**
- Interactive test client
- Demo sessions for different roles
- JWT token generation for testing
- Example queries for each role
- Interactive chat mode

### Configuration Files

**.env.template**
- Template for environment variables
- Database connection settings
- JWT configuration
- API keys for LLMs
- Observability settings (LangSmith, Langfuse)
- Multi-tenant configuration

**requirements.txt**
- Python package dependencies
- LangChain and LangGraph
- FastAPI and Uvicorn
- SQLAlchemy and PostgreSQL drivers
- Pydantic for validation
- JWT libraries
- Observability tools

**docker-compose.yml**
- Multi-container orchestration
- PostgreSQL service
- Redis service (caching)
- Chatbot API service
- Volume and network configuration
- Health checks

**Dockerfile**
- Python 3.11 slim base image
- System dependencies installation
- Python package installation
- Application code copying
- Health check configuration
- Uvicorn server startup

## Key Components

### 1. Multi-Tenant Architecture
- Schema-per-tenant isolation
- `public` schema stores tenant metadata
- Each tenant gets dedicated schema
- JWT contains `schema_name` for routing
- Complete data separation

### 2. Role-Based Access Control
- Three roles: Student, Teacher, Admin
- Permission-based data access
- Row-level security through RBAC service
- Students can only access their own data
- Teachers can access their class data
- Admins have full access

### 3. LangGraph Agent
- Multi-step reasoning workflow
- Tool-based architecture
- Async tool execution
- State management
- Conditional edges for flow control
- Role-specific behavior

### 4. Database Tools
- Structured query methods
- RBAC enforcement
- Performance analysis
- Attendance reporting
- Exam result retrieval
- Recommendation engine

### 5. Observability
- LangSmith tracing integration
- Langfuse analytics support
- Structured logging
- Error tracking
- Performance monitoring

## Data Flow

1. **Authentication**
   ```
   User → JWT Token → Auth Service → Decode → AuthPayload
   ```

2. **Chat Request**
   ```
   Client → FastAPI → Auth Check → Create Agent → Process Query
   ```

3. **Agent Processing**
   ```
   Agent → Reasoning → Tool Selection → Tool Execution → Response
   ```

4. **Database Query**
   ```
   Tool → RBAC Check → Set Schema → Query DB → Return Data
   ```

5. **Response Generation**
   ```
   Tool Results → Agent → LLM → Format → Return to Client
   ```

## Security Layers

1. **API Level**: JWT authentication on all endpoints
2. **RBAC Level**: Permission checks before data access
3. **Database Level**: Schema isolation per tenant
4. **Tool Level**: RBAC enforcement in each tool
5. **Input Level**: Validation and sanitization

## Extensibility Points

### Adding New Tools
1. Create method in `DatabaseQueryTools`
2. Define input schema with Pydantic
3. Implement RBAC checks
4. Register tool in `agent.py`

### Adding New Roles
1. Add to `UserRole` enum in `models.py`
2. Define permissions in `auth.py`
3. Update RBAC checks in `db_tools.py`
4. Add role-specific prompt in `agent.py`

### Adding New Features
1. Create database models if needed
2. Implement query methods with RBAC
3. Create tools for agent
4. Update API endpoints if needed
5. Add tests

## Environment Requirements

- Python 3.10+
- PostgreSQL 14+ (multi-schema support)
- Redis (optional, for caching)
- 2GB+ RAM
- API keys: Anthropic (required), OpenAI (optional)

## Performance Considerations

- Connection pooling (10 connections default)
- Async database operations
- Redis caching for frequently accessed data
- Schema-level query optimization
- Indexed database columns
- Batch operations where possible

## Monitoring & Debugging

- Structured logging with levels
- LangSmith for agent trace visualization
- Langfuse for production analytics
- FastAPI automatic API documentation
- Health check endpoints
- Error tracking and reporting
