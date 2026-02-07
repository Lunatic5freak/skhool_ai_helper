# School Management Chatbot

An intelligent AI-powered chatbot for school management with Role-Based Access Control (RBAC), multi-tenant support, and comprehensive observability.

## Features

### Core Capabilities
- **Multi-tenant Architecture**: Schema-per-tenant isolation for data security
- **Role-Based Access Control (RBAC)**: Students, Teachers, Admins with appropriate permissions
- **Intelligent Query Processing**: LangGraph-based agent with multi-step reasoning
- **Database Integration**: Query student records, attendance, exam results
- **Performance Analysis**: Comprehensive analytics with personalized recommendations
- **Real-time Insights**: Attendance patterns, grade trends, subject-wise performance

### Security & Compliance
- JWT-based authentication with schema isolation
- Content filtering and input validation guardrails
- Privacy-first design - students can only access their own data
- Encrypted credentials and secure token handling

### Observability
- LangSmith integration for tracing
- Langfuse support for production monitoring
- Detailed logging and error tracking
- Performance metrics and analytics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Service                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Layer   │  │ RBAC Service │  │  Guardrails  │      │
│  │ (JWT)        │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Agent                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Reasoning  │→ │ Tool         │→ │ Response     │      │
│  │   Node       │  │ Execution    │  │ Generation   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  Tools: Student Info | Attendance | Exams | Performance     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│             PostgreSQL (Multi-tenant)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ public       │  │ tenant_1     │  │ tenant_2     │      │
│  │ (tenants)    │  │ (school A)   │  │ (school B)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis (optional, for caching)

### Setup

1. **Clone and navigate to the project**
```bash
cd school_chatbot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.template .env
# Edit .env with your configuration
```

Required environment variables:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `DATABASE_*`: PostgreSQL connection details
- `JWT_SECRET_KEY`: Secret key for JWT signing

5. **Initialize database**
```bash
python init_db.py
```

This creates a demo tenant with sample data including:
- 1 Admin user
- 3 Teachers
- 6 Students
- 3 Classes
- Multiple subjects, exams, and attendance records

## Usage

### Starting the Server

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Interactive API docs: `http://localhost:8000/docs`

### Authentication

1. **Get JWT Token** (you'll need to implement a login endpoint or use the credentials below)

Sample credentials from demo data:
```
Admin:
  Email: admin@demo.school.com
  Password: admin123

Teacher:
  Email: john.smith@demo.school.com
  Password: teacher123

Student:
  Email: alice.williams@demo.school.com
  Password: student123
```

2. **Make authenticated requests**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "Show me my attendance for this month"}'
```

### Example Queries

**Student queries:**
```
- "What's my current attendance percentage?"
- "Show me my latest exam results"
- "How am I performing in Mathematics?"
- "Give me a detailed performance analysis"
- "What subjects do I need to improve in?"
```

**Teacher queries:**
```
- "Show me the performance of class 10A"
- "What's the average attendance in my class?"
- "Which students need extra attention?"
```

**Admin queries:**
```
- "Show me school-wide attendance statistics"
- "Which classes are performing best?"
- "Generate a performance report for grade 10"
```

## API Endpoints

### Health Check
```http
GET /health
```

### User Info
```http
GET /me
Headers: Authorization: Bearer <token>
```

### Permissions
```http
GET /permissions
Headers: Authorization: Bearer <token>
```

### Chat
```http
POST /chat
Headers: Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "message": "Your query here",
  "conversation_id": "optional-conversation-id"
}
```

## Role-Based Access Control (RBAC)

### Student Role
**Permissions:**
- View own personal information
- View own attendance records
- View own exam results
- View own performance analysis
- Get personalized recommendations

**Restrictions:**
- Cannot access other students' data
- Cannot view class-wide statistics
- Cannot modify any records

### Teacher Role
**Permissions:**
- View students in their classes
- View class attendance records
- View student exam results (for their subjects)
- Generate class performance reports
- Mark attendance (if implemented)
- Enter grades (if implemented)

**Restrictions:**
- Cannot access students from other classes
- Cannot view school-wide statistics
- Cannot modify system settings

### Admin Role
**Permissions:**
- Full access to all data
- View all students, teachers, classes
- Generate school-wide reports
- View comprehensive analytics
- Manage users and classes (if implemented)

## Multi-Tenant Architecture

### Schema Isolation
Each school/tenant gets its own PostgreSQL schema:
- `public` schema stores tenant metadata
- Each tenant has a dedicated schema (e.g., `demo_school`)
- Complete data isolation between tenants

### JWT Payload
The JWT token contains:
```json
{
  "user_id": "USR123",
  "email": "user@school.com",
  "role": "student",
  "schema_name": "demo_school",
  "student_id": "STU456",  // if student
  "teacher_id": "TCH789",  // if teacher
  "exp": 1234567890
}
```

The `schema_name` is automatically used to route all database queries to the correct tenant.

## Database Schema

### Main Tables

**Users**: Base user accounts
- `id`, `user_id`, `email`, `role`, `password_hash`

**Students**: Student profiles
- `student_id`, `roll_number`, `class_id`, `admission_date`

**Teachers**: Teacher profiles  
- `teacher_id`, `employee_id`, `specialization`, `date_of_joining`

**Classes**: Class/Grade information
- `class_id`, `name`, `grade`, `section`, `class_teacher_id`

**Subjects**: Subject details
- `subject_id`, `name`, `code`, `class_id`, `teacher_id`

**ExamResults**: Exam scores
- `student_id`, `subject_id`, `exam_type`, `marks_obtained`, `grade`

**Attendance**: Attendance records
- `student_id`, `date`, `status`, `remarks`

## Customization

### Adding New Tools

Edit `db_tools.py` and add new methods to `DatabaseQueryTools`:

```python
async def get_custom_report(self, param: str) -> Dict[str, Any]:
    """Your custom database query."""
    # Implement RBAC checks
    # Query database
    # Return results
```

Then register in `agent.py`:

```python
StructuredTool.from_function(
    func=self.db_tools.get_custom_report,
    name="custom_report",
    description="Description for the LLM",
    args_schema=CustomReportInput
)
```

### Adding New Roles

1. Update `UserRole` enum in `models.py`
2. Add permissions to `PERMISSIONS` dict in `auth.py`
3. Update RBAC checks in `db_tools.py`
4. Update system prompt in `agent.py`

## Observability

### LangSmith
Set in `.env`:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=school-chatbot
```

View traces at: https://smith.langchain.com

### Langfuse
Set in `.env`:
```
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_secret
```

View analytics at: https://cloud.langfuse.com

## Testing

```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=.
```

## Production Deployment

### Environment Variables
- Set `ENVIRONMENT=production`
- Set `DEBUG=false`
- Use strong `JWT_SECRET_KEY`
- Configure production database
- Enable SSL for database connections

### Security Checklist
- [ ] Change all default passwords
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable database connection pooling
- [ ] Configure proper backup strategy
- [ ] Set up monitoring and alerting

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check connection credentials in `.env`
- Ensure database exists and user has permissions

### JWT Token Issues
- Verify `JWT_SECRET_KEY` matches between token generation and validation
- Check token expiration time
- Ensure `Authorization` header format: `Bearer <token>`

### Schema Not Found
- Run `init_db.py` to create schemas
- Verify schema_name in JWT matches existing schema
- Check database permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License

## Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Email: support@yourschool.com

---

Built with ❤️ using LangChain, LangGraph, and FastAPI
