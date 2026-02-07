"""
Database models for School Management System.
Multi-tenant with schema-per-tenant isolation.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, 
    ForeignKey, Text, Date, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class AttendanceStatus(str, Enum):
    """Attendance status."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class ExamType(str, Enum):
    """Exam types."""
    MIDTERM = "midterm"
    FINAL = "final"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    PROJECT = "project"


class User(Base):
    """User model - stores in each tenant schema."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)


class Student(Base):
    """Student profile."""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    roll_number = Column(String(50), unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    admission_date = Column(Date, nullable=False)
    parent_contact = Column(String(20))
    parent_email = Column(String(255))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="student_profile")
    class_info = relationship("Class", back_populates="students")
    exam_results = relationship("ExamResult", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")


class Teacher(Base):
    """Teacher profile."""
    __tablename__ = "teachers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    specialization = Column(String(100))
    date_of_joining = Column(Date, nullable=False)
    contact_number = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="teacher_profile")
    classes = relationship("Class", back_populates="class_teacher")
    subjects = relationship("Subject", back_populates="teacher")


class Class(Base):
    """Class/Grade model."""
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Grade 10 A"
    grade = Column(Integer, nullable=False)  # 1-12
    section = Column(String(10))  # A, B, C
    class_teacher_id = Column(Integer, ForeignKey("teachers.id"))
    academic_year = Column(String(20), nullable=False)  # e.g., "2024-2025"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    class_teacher = relationship("Teacher", back_populates="classes")
    students = relationship("Student", back_populates="class_info")
    subjects = relationship("Subject", back_populates="class_info")
    
    __table_args__ = (
        Index('idx_class_grade_section', 'grade', 'section', 'academic_year'),
    )


class Subject(Base):
    """Subject model."""
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Mathematics"
    code = Column(String(20), unique=True, nullable=False)  # e.g., "MATH101"
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    max_marks = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    class_info = relationship("Class", back_populates="subjects")
    teacher = relationship("Teacher", back_populates="subjects")
    exam_results = relationship("ExamResult", back_populates="subject")


class ExamResult(Base):
    """Exam results model."""
    __tablename__ = "exam_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(50), unique=True, nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    exam_type = Column(SQLEnum(ExamType), nullable=False)
    exam_date = Column(Date, nullable=False)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False)
    grade = Column(String(5))  # A+, A, B+, etc.
    remarks = Column(Text)
    academic_year = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="exam_results")
    subject = relationship("Subject", back_populates="exam_results")
    
    __table_args__ = (
        Index('idx_exam_student_subject', 'student_id', 'subject_id', 'exam_date'),
    )
    
    @property
    def percentage(self) -> float:
        """Calculate percentage."""
        return (self.marks_obtained / self.max_marks) * 100 if self.max_marks > 0 else 0.0


class Attendance(Base):
    """Attendance records."""
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    attendance_id = Column(String(50), unique=True, nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=False)
    remarks = Column(Text)
    marked_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    
    __table_args__ = (
        Index('idx_attendance_student_date', 'student_id', 'date'),
    )


class Tenant(Base):
    """Tenant model - stored in public schema."""
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), unique=True, nullable=False, index=True)
    schema_name = Column(String(63), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # School name
    domain = Column(String(255), unique=True)  # Optional custom domain
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Contact information
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    address = Column(Text)


def generate_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:16]
