# Quick Start Guide - School Management Chatbot

Get up and running in 5 minutes!

## Prerequisites

- Python 3.10+ installed
- PostgreSQL 14+ installed and running
- Anthropic API key (get from https://console.anthropic.com/)

## Step 1: Setup Environment

```bash
# Navigate to project directory
cd school_chatbot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

```bash
# Copy template
cp .env.template .env

# Edit .env file with your settings
nano .env  # or use your favorite editor
```

**Minimum required settings:**
```env
# Your Anthropic API key (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Database settings
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=school_admin
DATABASE_PASSWORD=your_password
DATABASE_NAME=school_management

# JWT secret (change this!)
JWT_SECRET_KEY=your-super-secret-key-change-this
```

## Step 3: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# In PostgreSQL shell:
CREATE DATABASE school_management;
CREATE USER school_admin WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE school_management TO school_admin;
\q
```

## Step 4: Initialize Database with Demo Data

```bash
# Run initialization script
python init_db.py
```

This creates:
- Demo tenant (demo_school)
- 1 Admin user
- 3 Teachers
- 6 Students
- Sample classes, subjects, exams, and attendance

**Demo Credentials:**
```
Admin:     admin@demo.school.com / admin123
Teacher:   john.smith@demo.school.com / teacher123
Student:   alice.williams@demo.school.com / student123
```

## Step 5: Start the Server

```bash
# Run the server
python main.py

# Server starts at http://localhost:8000
```

## Step 6: Test the API

### Option A: Use the Test Client

```bash
# In a new terminal (with venv activated)
python test_client.py

# Select option 4 for interactive mode
# Or run demos for different roles
```

### Option B: Use API Documentation

Open your browser: http://localhost:8000/docs

### Option C: Use curl

```bash
# You'll need a JWT token first
# For testing, use the test_client.py to generate tokens

# Example chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "message": "Show me my attendance for this month"
  }'
```

## Quick Test Scenarios

### As a Student

```python
from test_client import ChatbotClient

client = ChatbotClient()
client.create_token(
    email="alice.williams@demo.school.com",
    role="student",
    schema_name="demo_school",
    user_id="STU001",
    student_id="STU_ALICE"
)

# Test queries
response = client.chat("What's my attendance percentage?")
print(response['response'])

response = client.chat("Show me my latest exam results")
print(response['response'])

response = client.chat("How am I performing overall?")
print(response['response'])
```

### As a Teacher

```python
client = ChatbotClient()
client.create_token(
    email="john.smith@demo.school.com",
    role="teacher",
    schema_name="demo_school",
    user_id="TCH001",
    teacher_id="TCH_JOHN"
)

response = client.chat("Show me class 10A performance statistics")
print(response['response'])
```

### As an Admin

```python
client = ChatbotClient()
client.create_token(
    email="admin@demo.school.com",
    role="admin",
    schema_name="demo_school",
    user_id="ADM001"
)

response = client.chat("Generate school-wide performance report")
print(response['response'])
```

## Docker Quick Start

If you prefer Docker:

```bash
# Make sure Docker and Docker Compose are installed

# Copy environment file
cp .env.template .env

# Edit .env with your ANTHROPIC_API_KEY

# Start services
docker-compose up -d

# Initialize database
docker-compose exec chatbot_api python init_db.py

# View logs
docker-compose logs -f chatbot_api

# Stop services
docker-compose down
```

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check credentials in .env match database
psql -U school_admin -d school_management
```

### Module Not Found

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key Error

```bash
# Verify ANTHROPIC_API_KEY in .env
cat .env | grep ANTHROPIC_API_KEY

# Make sure it starts with sk-ant-api03-
```

### Schema Not Found

```bash
# Run initialization script
python init_db.py

# Check schema exists
psql -U school_admin -d school_management -c "\dn"
```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Read the README**: Full documentation in README.md
3. **Review Project Structure**: See PROJECT_STRUCTURE.md
4. **Add Your Data**: Modify init_db.py or create your own data
5. **Customize**: Add new tools, modify prompts, extend functionality

## Common Queries to Try

**Students:**
- "What's my current attendance percentage?"
- "Show me my math exam results"
- "How am I performing compared to last month?"
- "Which subjects should I focus on?"
- "Give me a detailed performance analysis"

**Teachers:**
- "Show me class 10A attendance report"
- "Which students need extra attention?"
- "What's the average performance in my class?"
- "Generate a report on recent exam results"

**Admins:**
- "Show school-wide attendance statistics"
- "Which class has the best overall performance?"
- "Generate a comprehensive performance report"
- "Show me trends in student performance"

## Support

- Check README.md for detailed documentation
- Review PROJECT_STRUCTURE.md for architecture details
- Examine code comments for implementation details

---

**You're all set! Start chatting with your school management assistant!** 🎓
