"""
Authentication and Role-Based Access Control (RBAC).
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
import logging

from config import get_settings
from models import UserRole

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """JWT token data."""
    user_id: str
    email: str
    role: UserRole
    schema_name: str
    exp: Optional[datetime] = None


class AuthPayload(BaseModel):
    """Authentication payload after JWT decode."""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    schema_name: str = Field(..., description="Tenant schema name")
    student_id: Optional[str] = Field(None, description="Student ID if user is student")
    teacher_id: Optional[str] = Field(None, description="Teacher ID if user is teacher")
    exp: int = Field(..., description="Token expiration timestamp")


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = self.settings.jwt_secret_key
        self.algorithm = self.settings.jwt_algorithm
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        schema_name: str,
        student_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            schema_name: Tenant schema name for multi-tenant isolation
            student_id: Student ID if user is a student
            teacher_id: Teacher ID if user is a teacher
            expires_delta: Token expiration time
            
        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=self.settings.jwt_access_token_expire_minutes
            )
        
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "user_id": user_id,
            "email": email,
            "role": role.value if isinstance(role, UserRole) else role,
            "schema_name": schema_name,
            "exp": expire,
        }
        
        if student_id:
            to_encode["student_id"] = student_id
        if teacher_id:
            to_encode["teacher_id"] = teacher_id
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[AuthPayload]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            AuthPayload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            auth_payload = AuthPayload(**payload)
            
            # Check if token is expired
            if datetime.fromtimestamp(auth_payload.exp) < datetime.utcnow():
                logger.warning("Token has expired")
                return None
            
            return auth_payload
            
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None


class RBACService:
    """Role-Based Access Control service."""
    
    # Define permissions for each role
    PERMISSIONS = {
        UserRole.ADMIN: {
            "view_all_students",
            "view_all_teachers",
            "view_all_classes",
            "view_all_attendance",
            "view_all_exams",
            "manage_users",
            "manage_classes",
            "manage_subjects",
            "generate_reports",
            "view_analytics",
        },
        UserRole.TEACHER: {
            "view_own_classes",
            "view_class_students",
            "mark_attendance",
            "enter_grades",
            "view_student_performance",
            "generate_class_reports",
        },
        UserRole.STUDENT: {
            "view_own_data",
            "view_own_attendance",
            "view_own_grades",
            "view_own_performance",
        },
        UserRole.PARENT: {
            "view_child_data",
            "view_child_attendance",
            "view_child_grades",
            "view_child_performance",
        },
    }
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: str) -> bool:
        """
        Check if role has specific permission.
        
        Args:
            role: User role
            permission: Permission to check
            
        Returns:
            True if role has permission, False otherwise
        """
        role_permissions = cls.PERMISSIONS.get(role, set())
        return permission in role_permissions
    
    @classmethod
    def can_access_student_data(
        cls,
        auth_payload: AuthPayload,
        target_student_id: str
    ) -> bool:
        """
        Check if user can access specific student's data.
        
        Args:
            auth_payload: Authentication payload
            target_student_id: Student ID to access
            
        Returns:
            True if access allowed, False otherwise
        """
        role = UserRole(auth_payload.role)
        
        # Admin can access all students
        if role == UserRole.ADMIN:
            return True
        
        # Student can only access their own data
        if role == UserRole.STUDENT:
            return auth_payload.student_id == target_student_id
        
        # Teachers can access students in their classes (needs class check)
        if role == UserRole.TEACHER:
            # This would require checking if student is in teacher's class
            # For now, we'll allow - should be enhanced with actual class check
            return True
        
        return False
    
    @classmethod
    def can_access_class_data(
        cls,
        auth_payload: AuthPayload,
        class_id: str
    ) -> bool:
        """
        Check if user can access specific class data.
        
        Args:
            auth_payload: Authentication payload
            class_id: Class ID to access
            
        Returns:
            True if access allowed, False otherwise
        """
        role = UserRole(auth_payload.role)
        
        # Admin can access all classes
        if role == UserRole.ADMIN:
            return True
        
        # Teachers can access their own classes
        if role == UserRole.TEACHER:
            # Should check if class belongs to teacher
            return True
        
        return False
    
    @classmethod
    def filter_query_by_role(
        cls,
        auth_payload: AuthPayload,
        base_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add role-based filters to database query.
        
        Args:
            auth_payload: Authentication payload
            base_filters: Base query filters
            
        Returns:
            Filters with RBAC constraints
        """
        role = UserRole(auth_payload.role)
        
        if role == UserRole.STUDENT:
            # Students can only see their own data
            base_filters["student_id"] = auth_payload.student_id
        elif role == UserRole.TEACHER:
            # Teachers can see their students' data
            # This would need enhancement to filter by teacher's classes
            pass
        # Admin sees everything - no additional filters
        
        return base_filters


# Singleton instances
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
