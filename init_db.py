"""
Database initialization script with sample data.
Creates a demo tenant and populates with sample students, teachers, and data.
"""
import asyncio
import sys
from datetime import datetime, date, timedelta
import random

from sqlalchemy import text
from database import get_db_service
from models import (
    Tenant, User, Student, Teacher, Class, Subject, 
    ExamResult, Attendance, UserRole, AttendanceStatus, 
    ExamType, generate_id
)
from auth import get_auth_service
from config import get_settings


async def create_demo_tenant():
    """Create a demo tenant."""
    db_service = get_db_service()
    settings = get_settings()
    
    # Initialize public schema
    print("Initializing public schema...")
    await db_service.initialize_public_schema()
    
    # Create demo tenant
    schema_name = "demo_school"
    
    if await db_service.schema_exists(schema_name):
        print(f"Schema {schema_name} already exists")
        return schema_name
    
    print(f"Creating tenant schema: {schema_name}")
    success = await db_service.create_tenant_schema(schema_name)
    
    if not success:
        print("Failed to create schema")
        return None
    
    # Add tenant to public.tenants
    async with db_service.get_session() as session:
        tenant = Tenant(
            tenant_id=generate_id("TNT"),
            schema_name=schema_name,
            name="Demo High School",
            domain="demo.school.com",
            is_active=True,
            contact_email="admin@demo.school.com",
            contact_phone="+1-555-0100",
            address="123 Education Street, Learning City, ED 12345"
        )
        session.add(tenant)
        await session.commit()
        print(f"Created tenant: {tenant.name}")
    
    return schema_name


async def populate_demo_data(schema_name: str):
    """Populate demo data in tenant schema."""
    db_service = get_db_service()
    auth_service = get_auth_service()
    
    async with db_service.get_session(schema_name) as session:
        print("Creating users...")
        
        # Create admin user
        admin_user = User(
            user_id=generate_id("USR"),
            email="admin@demo.school.com",
            password_hash=auth_service.get_password_hash("admin123"),
            role=UserRole.ADMIN,
            first_name="Sarah",
            last_name="Administrator",
            is_active=True
        )
        session.add(admin_user)
        
        # Create teachers
        teachers_data = [
            ("john.smith@demo.school.com", "John", "Smith", "Mathematics"),
            ("emma.johnson@demo.school.com", "Emma", "Johnson", "English"),
            ("michael.brown@demo.school.com", "Michael", "Brown", "Science"),
        ]
        
        teachers = []
        for email, first_name, last_name, specialization in teachers_data:
            user = User(
                user_id=generate_id("USR"),
                email=email,
                password_hash=auth_service.get_password_hash("teacher123"),
                role=UserRole.TEACHER,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            session.add(user)
            await session.flush()
            
            teacher = Teacher(
                teacher_id=generate_id("TCH"),
                user_id=user.id,
                employee_id=f"EMP{1000 + len(teachers)}",
                specialization=specialization,
                date_of_joining=date(2020, 8, 1),
                contact_number=f"+1-555-0{200 + len(teachers)}"
            )
            session.add(teacher)
            teachers.append(teacher)
        
        await session.flush()
        print(f"Created {len(teachers)} teachers")
        
        # Create classes
        classes_data = [
            ("Grade 10 A", 10, "A"),
            ("Grade 10 B", 10, "B"),
            ("Grade 11 A", 11, "A"),
        ]
        
        classes = []
        for idx, (name, grade, section) in enumerate(classes_data):
            class_obj = Class(
                class_id=generate_id("CLS"),
                name=name,
                grade=grade,
                section=section,
                class_teacher_id=teachers[idx % len(teachers)].id,
                academic_year="2024-2025"
            )
            session.add(class_obj)
            classes.append(class_obj)
        
        await session.flush()
        print(f"Created {len(classes)} classes")
        
        # Create students
        students_data = [
            ("alice.williams@demo.school.com", "Alice", "Williams", "R001", 0),
            ("bob.davis@demo.school.com", "Bob", "Davis", "R002", 0),
            ("carol.miller@demo.school.com", "Carol", "Miller", "R003", 0),
            ("david.wilson@demo.school.com", "David", "Wilson", "R004", 1),
            ("emma.moore@demo.school.com", "Emma", "Moore", "R005", 1),
            ("frank.taylor@demo.school.com", "Frank", "Taylor", "R006", 2),
        ]
        
        students = []
        for email, first_name, last_name, roll_number, class_idx in students_data:
            user = User(
                user_id=generate_id("USR"),
                email=email,
                password_hash=auth_service.get_password_hash("student123"),
                role=UserRole.STUDENT,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            session.add(user)
            await session.flush()
            
            student = Student(
                student_id=generate_id("STU"),
                user_id=user.id,
                roll_number=roll_number,
                class_id=classes[class_idx].id,
                date_of_birth=date(2008, random.randint(1, 12), random.randint(1, 28)),
                admission_date=date(2020, 4, 1),
                parent_contact=f"+1-555-{3000 + len(students):04d}",
                parent_email=f"parent.{email}",
                address=f"{100 + len(students)} Main Street, Demo City"
            )
            session.add(student)
            students.append(student)
        
        await session.flush()
        print(f"Created {len(students)} students")
        
        # Create subjects
        subjects_data = [
            ("Mathematics", "MATH101", 0, 0),
            ("English", "ENG101", 0, 1),
            ("Science", "SCI101", 0, 2),
            ("Mathematics", "MATH102", 1, 0),
            ("English", "ENG102", 1, 1),
            ("Science", "SCI102", 1, 2),
            ("Mathematics", "MATH103", 2, 0),
        ]
        
        subjects = []
        for name, code, class_idx, teacher_idx in subjects_data:
            subject = Subject(
                subject_id=generate_id("SUB"),
                name=name,
                code=code,
                class_id=classes[class_idx].id,
                teacher_id=teachers[teacher_idx].id,
                max_marks=100.0
            )
            session.add(subject)
            subjects.append(subject)
        
        await session.flush()
        print(f"Created {len(subjects)} subjects")
        
        # Create exam results
        exam_types = [ExamType.MIDTERM, ExamType.FINAL, ExamType.QUIZ]
        grades_map = {
            (90, 100): "A+",
            (80, 90): "A",
            (70, 80): "B+",
            (60, 70): "B",
            (50, 60): "C",
            (0, 50): "D"
        }
        
        print("Creating exam results...")
        for student in students:
            # Get subjects for student's class
            student_subjects = [s for s in subjects if s.class_id == student.class_id]
            
            for subject in student_subjects:
                for exam_type in exam_types:
                    # Vary marks for realistic data
                    base_score = random.uniform(50, 95)
                    marks = round(base_score + random.uniform(-10, 10), 2)
                    marks = max(0, min(100, marks))  # Clamp between 0-100
                    
                    # Determine grade
                    grade = "F"
                    for (low, high), g in grades_map.items():
                        if low <= marks < high:
                            grade = g
                            break
                    
                    exam_date = date.today() - timedelta(days=random.randint(30, 180))
                    
                    exam_result = ExamResult(
                        result_id=generate_id("RES"),
                        student_id=student.id,
                        subject_id=subject.id,
                        exam_type=exam_type,
                        exam_date=exam_date,
                        marks_obtained=marks,
                        max_marks=100.0,
                        grade=grade,
                        remarks="Good work" if marks >= 70 else "Needs improvement",
                        academic_year="2024-2025"
                    )
                    session.add(exam_result)
        
        await session.flush()
        print("Created exam results")
        
        # Create attendance records (last 60 days)
        print("Creating attendance records...")
        start_date = date.today() - timedelta(days=60)
        
        for student in students:
            for day_offset in range(60):
                attendance_date = start_date + timedelta(days=day_offset)
                
                # Skip weekends
                if attendance_date.weekday() >= 5:
                    continue
                
                # Random attendance with 85% present rate
                status_roll = random.random()
                if status_roll < 0.85:
                    status = AttendanceStatus.PRESENT
                elif status_roll < 0.90:
                    status = AttendanceStatus.LATE
                elif status_roll < 0.95:
                    status = AttendanceStatus.EXCUSED
                else:
                    status = AttendanceStatus.ABSENT
                
                attendance = Attendance(
                    attendance_id=generate_id("ATT"),
                    student_id=student.id,
                    date=attendance_date,
                    status=status,
                    remarks="Regular" if status == AttendanceStatus.PRESENT else None,
                    marked_by=admin_user.id
                )
                session.add(attendance)
        
        await session.flush()
        print("Created attendance records")
        
        await session.commit()
        print("\n✓ Demo data populated successfully!")
        
        # Print sample credentials
        print("\n" + "="*50)
        print("SAMPLE CREDENTIALS")
        print("="*50)
        print("\nAdmin:")
        print("  Email: admin@demo.school.com")
        print("  Password: admin123")
        print("\nTeacher:")
        print("  Email: john.smith@demo.school.com")
        print("  Password: teacher123")
        print("\nStudent:")
        print("  Email: alice.williams@demo.school.com")
        print("  Password: student123")
        print("="*50)


async def main():
    """Main initialization function."""
    try:
        print("School Management Chatbot - Database Initialization")
        print("="*50)
        
        # Create demo tenant
        schema_name = await create_demo_tenant()
        
        if not schema_name:
            print("Failed to create tenant")
            sys.exit(1)
        
        # Populate with demo data
        await populate_demo_data(schema_name)
        
        print("\n✓ Initialization complete!")
        print(f"✓ Tenant schema: {schema_name}")
        
    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
