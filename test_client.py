"""
Test client for School Management Chatbot.
Simulates user interactions with the chatbot API.
"""
import requests
import json
from typing import Optional
from datetime import datetime, timedelta
from auth import get_auth_service, AuthPayload
from models import UserRole


class ChatbotClient:
    """Client for interacting with the chatbot API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client."""
        self.base_url = base_url
        self.token: Optional[str] = None
        self.headers = {"Content-Type": "application/json"}
    
    def create_token(
        self,
        email: str,
        role: str,
        schema_name: str = "demo_school",
        user_id: str = "test_user",
        student_id: Optional[str] = None,
        teacher_id: Optional[str] = None
    ) -> str:
        """
        Create a test JWT token.
        
        Args:
            email: User email
            role: User role (student, teacher, admin)
            schema_name: Tenant schema name
            user_id: User ID
            student_id: Student ID if role is student
            teacher_id: Teacher ID if role is teacher
            
        Returns:
            JWT token string
        """
        auth_service = get_auth_service()
        
        token = auth_service.create_access_token(
            user_id=user_id,
            email=email,
            role=UserRole(role),
            schema_name=schema_name,
            student_id=student_id,
            teacher_id=teacher_id,
            expires_delta=timedelta(hours=1)
        )
        
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"
        return token
    
    def set_token(self, token: str):
        """Set authentication token."""
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"
    
    def health_check(self) -> dict:
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def get_user_info(self) -> dict:
        """Get current user information."""
        response = requests.get(
            f"{self.base_url}/me",
            headers=self.headers
        )
        return response.json()
    
    def get_permissions(self) -> dict:
        """Get user permissions."""
        response = requests.get(
            f"{self.base_url}/permissions",
            headers=self.headers
        )
        return response.json()
    
    def chat(self, message: str, conversation_id: Optional[str] = None) -> dict:
        """
        Send a chat message.
        
        Args:
            message: User message
            conversation_id: Optional conversation ID
            
        Returns:
            Chat response
        """
        data = {"message": message}
        if conversation_id:
            data["conversation_id"] = conversation_id
        
        response = requests.post(
            f"{self.base_url}/chat",
            headers=self.headers,
            json=data
        )
        
        return response.json()


def demo_student_session():
    """Demo session as a student."""
    print("\n" + "="*60)
    print("STUDENT SESSION DEMO")
    print("="*60)
    
    client = ChatbotClient()
    
    # Create token for student
    print("\n1. Creating student token...")
    token = client.create_token(
        email="ld@kvs.com",
        role="student",
        schema_name="test_org",
        user_id="ld@kvs.com",
        student_id="63"
    )
    print(f"Token created: {token[:50]}...")
    
    # Get user info
    print("\n2. Getting user info...")
    user_info = client.get_user_info()
    print(json.dumps(user_info, indent=2))
    
    # Get permissions
    print("\n3. Getting permissions...")
    permissions = client.get_permissions()
    print(json.dumps(permissions, indent=2))
    
    # Chat examples
    queries = [
        "What's my attendance percentage?",
        "Show me my latest exam results",
        "How am I performing overall?",
        "Which subjects do I need to improve in?",
    ]
    
    print("\n4. Testing chat queries...")
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        response = client.chat(query)
        print(f"\nResponse:\n{response.get('response', 'No response')}")
    
    print("\n" + "="*60)


def demo_teacher_session():
    """Demo session as a teacher."""
    print("\n" + "="*60)
    print("TEACHER SESSION DEMO")
    print("="*60)
    
    client = ChatbotClient()
    
    # Create token for teacher
    print("\n1. Creating teacher token...")
    token = client.create_token(
        email="john.smith@demo.school.com",
        role="teacher",
        schema_name="demo_school",
        user_id="USR_JOHN",
        teacher_id="TCH_JOHN"
    )
    print(f"Token created: {token[:50]}...")
    
    # Get permissions
    print("\n2. Getting permissions...")
    permissions = client.get_permissions()
    print(json.dumps(permissions, indent=2))
    
    # Chat examples
    queries = [
        "Show me the performance of students in my class",
        "What's the average attendance in class 10A?",
        "Which students need extra attention?",
    ]
    
    print("\n3. Testing chat queries...")
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        response = client.chat(query)
        print(f"\nResponse:\n{response.get('response', 'No response')}")
    
    print("\n" + "="*60)


def demo_admin_session():
    """Demo session as an admin."""
    print("\n" + "="*60)
    print("ADMIN SESSION DEMO")
    print("="*60)
    
    client = ChatbotClient()
    
    # Create token for admin
    print("\n1. Creating admin token...")
    token = client.create_token(
        email="admin@demo.school.com",
        role="admin",
        schema_name="demo_school",
        user_id="USR_ADMIN"
    )
    print(f"Token created: {token[:50]}...")
    
    # Get permissions
    print("\n2. Getting permissions...")
    permissions = client.get_permissions()
    print(json.dumps(permissions, indent=2))
    
    # Chat examples
    queries = [
        "Show me overall school performance statistics",
        "Which classes have the best attendance?",
        "Generate a report on student performance trends",
    ]
    
    print("\n3. Testing chat queries...")
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        response = client.chat(query)
        print(f"\nResponse:\n{response.get('response', 'No response')}")
    
    print("\n" + "="*60)


def interactive_mode():
    """Interactive chat mode."""
    print("\n" + "="*60)
    print("INTERACTIVE CHAT MODE")
    print("="*60)
    
    client = ChatbotClient()
    
    # Select role
    print("\nSelect role:")
    print("1. Student")
    print("2. Teacher")
    print("3. Admin")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        client.create_token(
            email="alice.williams@demo.school.com",
            role="student",
            schema_name="demo_school",
            user_id="USR_ALICE",
            student_id="STU_ALICE"
        )
        role_name = "Student"
    elif choice == "2":
        client.create_token(
            email="john.smith@demo.school.com",
            role="teacher",
            schema_name="demo_school",
            user_id="USR_JOHN",
            teacher_id="TCH_JOHN"
        )
        role_name = "Teacher"
    else:
        client.create_token(
            email="admin@demo.school.com",
            role="admin",
            schema_name="demo_school",
            user_id="USR_ADMIN"
        )
        role_name = "Admin"
    
    print(f"\n✓ Logged in as {role_name}")
    print("Type 'exit' to quit\n")
    
    while True:
        try:
            query = input("You: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                continue
            
            response = client.chat(query)
            print(f"\nAssistant: {response.get('response', 'No response')}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    """Main test function."""
    print("\n" + "="*60)
    print("School Management Chatbot - Test Client")
    print("="*60)
    
    # Check health
    client = ChatbotClient()
    try:
        health = client.health_check()
        print(f"\n✓ API Health: {health.get('status')}")
    except Exception as e:
        print(f"\n✗ API not accessible: {e}")
        print("Please ensure the API server is running (python main.py)")
        return
    
    # Show options
    print("\nSelect test mode:")
    print("1. Demo Student Session")
    print("2. Demo Teacher Session")
    print("3. Demo Admin Session")
    print("4. Interactive Chat Mode")
    print("5. Run All Demos")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        demo_student_session()
    elif choice == "2":
        demo_teacher_session()
    elif choice == "3":
        demo_admin_session()
    elif choice == "4":
        interactive_mode()
    elif choice == "5":
        demo_student_session()
        demo_teacher_session()
        demo_admin_session()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
