"""
Database query tools for the chatbot agent with RBAC.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from models import (
    Student, Teacher, Class, Subject, ExamResult, 
    Attendance, User, UserRole, AttendanceStatus, ExamType
)
from auth import AuthPayload, RBACService
from database import get_db_service

logger = logging.getLogger(__name__)


class StudentPerformanceData(BaseModel):
    """Student performance data model."""
    student_id: str
    student_name: str
    total_exams: int
    average_percentage: float
    highest_score: float
    lowest_score: float
    subject_wise_performance: Dict[str, float]
    attendance_percentage: float
    grade_distribution: Dict[str, int]


class AttendanceReport(BaseModel):
    """Attendance report model."""
    student_id: str
    student_name: str
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    excused_days: int
    attendance_percentage: float
    recent_absences: List[str]


class ExamReportData(BaseModel):
    """Exam report data model."""
    exam_type: str
    exam_date: str
    subject: str
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: str


class DatabaseQueryTools:
    """Tools for querying school database with RBAC."""
    
    def __init__(self, schema_name: str, auth_payload: AuthPayload):
        """
        Initialize database query tools.
        
        Args:
            schema_name: Tenant schema name
            auth_payload: Authentication payload for RBAC
        """
        self.schema_name = schema_name
        self.auth_payload = auth_payload
        self.db_service = get_db_service()
    
    async def get_student_info(self, student_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get student information.
        
        Args:
            student_id: Student ID (optional, defaults to current user if student)
            
        Returns:
            Student information dictionary
        """
        # Determine which student to query
        if student_id is None:
            if UserRole(self.auth_payload.role) == UserRole.STUDENT:
                student_id = self.auth_payload.student_id
            else:
                return {"error": "Student ID required for non-student users"}
        
        # Check RBAC
        if not RBACService.can_access_student_data(self.auth_payload, student_id):
            return {"error": "Access denied: You don't have permission to view this student's data"}
        
        try:
            async with self.db_service.get_session(self.schema_name) as session:
                result = await session.execute(
                    select(Student, User, Class)
                    .join(User, Student.user_id == User.id)
                    .join(Class, Student.class_id == Class.id)
                    .where(Student.student_id == student_id)
                )
                row = result.first()
                
                if not row:
                    return {"error": f"Student {student_id} not found"}
                
                student, user, class_info = row
                
                return {
                    "student_id": student.student_id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "roll_number": student.roll_number,
                    "class": class_info.name,
                    "grade": class_info.grade,
                    "section": class_info.section,
                    "admission_date": student.admission_date.isoformat(),
                    "parent_contact": student.parent_contact,
                    "parent_email": student.parent_email,
                }
        except Exception as e:
            logger.error(f"Error fetching student info: {e}")
            return {"error": str(e)}
    
    async def get_student_attendance(
        self,
        student_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get student attendance report.
        
        Args:
            student_id: Student ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Attendance report
        """
        # Determine student
        if student_id is None:
            if UserRole(self.auth_payload.role) == UserRole.STUDENT:
                student_id = self.auth_payload.student_id
            else:
                return {"error": "Student ID required"}
        
        # Check RBAC
        if not RBACService.can_access_student_data(self.auth_payload, student_id):
            return {"error": "Access denied"}
        
        try:
            async with self.db_service.get_session(self.schema_name) as session:
                # Get student info
                student_result = await session.execute(
                    select(Student, User)
                    .join(User, Student.user_id == User.id)
                    .where(Student.student_id == student_id)
                )
                student_row = student_result.first()
                
                if not student_row:
                    return {"error": "Student not found"}
                
                student, user = student_row
                
                # Build query for attendance
                query = select(Attendance).where(Attendance.student_id == student.id)
                
                if start_date:
                    query = query.where(Attendance.date >= start_date)
                if end_date:
                    query = query.where(Attendance.date <= end_date)
                
                attendance_result = await session.execute(query.order_by(desc(Attendance.date)))
                attendance_records = attendance_result.scalars().all()
                
                # Calculate statistics
                total_days = len(attendance_records)
                present_days = sum(1 for a in attendance_records if a.status == AttendanceStatus.PRESENT)
                absent_days = sum(1 for a in attendance_records if a.status == AttendanceStatus.ABSENT)
                late_days = sum(1 for a in attendance_records if a.status == AttendanceStatus.LATE)
                excused_days = sum(1 for a in attendance_records if a.status == AttendanceStatus.EXCUSED)
                
                attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
                
                # Recent absences
                recent_absences = [
                    a.date.isoformat() 
                    for a in attendance_records[:10] 
                    if a.status == AttendanceStatus.ABSENT
                ]
                
                return {
                    "student_id": student_id,
                    "student_name": f"{user.first_name} {user.last_name}",
                    "total_days": total_days,
                    "present_days": present_days,
                    "absent_days": absent_days,
                    "late_days": late_days,
                    "excused_days": excused_days,
                    "attendance_percentage": round(attendance_percentage, 2),
                    "recent_absences": recent_absences,
                    "period": {
                        "start": start_date or "Beginning",
                        "end": end_date or "Current"
                    }
                }
        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            return {"error": str(e)}
    
    async def get_exam_results(
        self,
        student_id: Optional[str] = None,
        subject_name: Optional[str] = None,
        exam_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get student exam results.
        
        Args:
            student_id: Student ID
            subject_name: Filter by subject name
            exam_type: Filter by exam type
            
        Returns:
            Exam results
        """
        # Determine student
        if student_id is None:
            if UserRole(self.auth_payload.role) == UserRole.STUDENT:
                student_id = self.auth_payload.student_id
            else:
                return {"error": "Student ID required"}
        
        # Check RBAC
        if not RBACService.can_access_student_data(self.auth_payload, student_id):
            return {"error": "Access denied"}
        
        try:
            async with self.db_service.get_session(self.schema_name) as session:
                # Get student
                student_result = await session.execute(
                    select(Student, User)
                    .join(User, Student.user_id == User.id)
                    .where(Student.student_id == student_id)
                )
                student_row = student_result.first()
                
                if not student_row:
                    return {"error": "Student not found"}
                
                student, user = student_row
                
                # Build query
                query = (
                    select(ExamResult, Subject)
                    .join(Subject, ExamResult.subject_id == Subject.id)
                    .where(ExamResult.student_id == student.id)
                )
                
                if subject_name:
                    query = query.where(Subject.name.ilike(f"%{subject_name}%"))
                
                if exam_type:
                    query = query.where(ExamResult.exam_type == exam_type)
                
                results = await session.execute(query.order_by(desc(ExamResult.exam_date)))
                
                exam_records = []
                for exam, subject in results:
                    exam_records.append({
                        "exam_date": exam.exam_date.isoformat(),
                        "subject": subject.name,
                        "exam_type": exam.exam_type.value,
                        "marks_obtained": exam.marks_obtained,
                        "max_marks": exam.max_marks,
                        "percentage": round(exam.percentage, 2),
                        "grade": exam.grade or "N/A",
                        "remarks": exam.remarks
                    })
                
                return {
                    "student_id": student_id,
                    "student_name": f"{user.first_name} {user.last_name}",
                    "total_exams": len(exam_records),
                    "results": exam_records
                }
        except Exception as e:
            logger.error(f"Error fetching exam results: {e}")
            return {"error": str(e)}
    
    async def get_performance_analysis(
        self,
        student_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance analysis for a student.
        
        Args:
            student_id: Student ID
            
        Returns:
            Performance analysis with insights
        """
        # Determine student
        if student_id is None:
            if UserRole(self.auth_payload.role) == UserRole.STUDENT:
                student_id = self.auth_payload.student_id
            else:
                return {"error": "Student ID required"}
        
        # Check RBAC
        if not RBACService.can_access_student_data(self.auth_payload, student_id):
            return {"error": "Access denied"}
        
        try:
            async with self.db_service.get_session(self.schema_name) as session:
                # Get student
                student_result = await session.execute(
                    select(Student, User)
                    .join(User, Student.user_id == User.id)
                    .where(Student.student_id == student_id)
                )
                student_row = student_result.first()
                
                if not student_row:
                    return {"error": "Student not found"}
                
                student, user = student_row
                
                # Get exam results
                exam_results = await session.execute(
                    select(ExamResult, Subject)
                    .join(Subject, ExamResult.subject_id == Subject.id)
                    .where(ExamResult.student_id == student.id)
                )
                
                exams_data = []
                subject_performance = {}
                grade_distribution = {}
                
                for exam, subject in exam_results:
                    percentage = exam.percentage
                    exams_data.append(percentage)
                    
                    # Subject-wise performance
                    if subject.name not in subject_performance:
                        subject_performance[subject.name] = []
                    subject_performance[subject.name].append(percentage)
                    
                    # Grade distribution
                    grade = exam.grade or "N/A"
                    grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
                
                # Calculate statistics
                avg_performance = sum(exams_data) / len(exams_data) if exams_data else 0
                highest_score = max(exams_data) if exams_data else 0
                lowest_score = min(exams_data) if exams_data else 0
                
                # Subject averages
                subject_averages = {
                    subject: sum(scores) / len(scores)
                    for subject, scores in subject_performance.items()
                }
                
                # Get attendance
                attendance_result = await session.execute(
                    select(Attendance)
                    .where(Attendance.student_id == student.id)
                )
                attendance_records = attendance_result.scalars().all()
                
                total_days = len(attendance_records)
                present_days = sum(
                    1 for a in attendance_records 
                    if a.status == AttendanceStatus.PRESENT
                )
                attendance_percentage = (
                    (present_days / total_days * 100) if total_days > 0 else 0
                )
                
                # Performance insights
                insights = []
                
                if avg_performance >= 90:
                    insights.append("Excellent overall performance! Keep up the great work.")
                elif avg_performance >= 75:
                    insights.append("Good performance. Focus on weaker subjects to excel further.")
                elif avg_performance >= 60:
                    insights.append("Average performance. More effort needed in several subjects.")
                else:
                    insights.append("Performance needs improvement. Consider seeking additional help.")
                
                if attendance_percentage < 75:
                    insights.append("Low attendance detected. Regular attendance is crucial for better performance.")
                
                # Find weak subjects
                weak_subjects = [
                    subject for subject, avg in subject_averages.items() if avg < 60
                ]
                if weak_subjects:
                    insights.append(f"Need improvement in: {', '.join(weak_subjects)}")
                
                # Find strong subjects
                strong_subjects = [
                    subject for subject, avg in subject_averages.items() if avg >= 85
                ]
                if strong_subjects:
                    insights.append(f"Excelling in: {', '.join(strong_subjects)}")
                
                return {
                    "student_id": student_id,
                    "student_name": f"{user.first_name} {user.last_name}",
                    "overall_statistics": {
                        "total_exams": len(exams_data),
                        "average_percentage": round(avg_performance, 2),
                        "highest_score": round(highest_score, 2),
                        "lowest_score": round(lowest_score, 2),
                        "attendance_percentage": round(attendance_percentage, 2)
                    },
                    "subject_wise_performance": {
                        subject: round(avg, 2)
                        for subject, avg in subject_averages.items()
                    },
                    "grade_distribution": grade_distribution,
                    "insights": insights,
                    "recommendations": self._generate_recommendations(
                        avg_performance, 
                        attendance_percentage, 
                        weak_subjects
                    )
                }
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(
        self,
        avg_performance: float,
        attendance_percentage: float,
        weak_subjects: List[str]
    ) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        if attendance_percentage < 85:
            recommendations.append(
                "Improve attendance to at least 85% for better academic outcomes"
            )
        
        if avg_performance < 75:
            recommendations.append(
                "Schedule regular study sessions and seek teacher guidance"
            )
        
        if weak_subjects:
            recommendations.append(
                f"Focus extra study time on: {', '.join(weak_subjects)}"
            )
            recommendations.append(
                "Consider joining study groups or tutoring for weak subjects"
            )
        
        if avg_performance >= 85:
            recommendations.append(
                "Maintain current study habits and explore advanced topics"
            )
        
        recommendations.append(
            "Set specific, measurable goals for each subject"
        )
        recommendations.append(
            "Review and revise regularly instead of last-minute cramming"
        )
        
        return recommendations
    
    async def get_class_performance(self, class_id: str) -> Dict[str, Any]:
        """
        Get class-wide performance statistics (Admin/Teacher only).
        
        Args:
            class_id: Class ID
            
        Returns:
            Class performance data
        """
        # Check permissions
        role = UserRole(self.auth_payload.role)
        if role not in [UserRole.ADMIN, UserRole.TEACHER]:
            return {"error": "Access denied: Only admins and teachers can view class statistics"}
        
        try:
            async with self.db_service.get_session(self.schema_name) as session:
                # Get class info
                class_result = await session.execute(
                    select(Class).where(Class.class_id == class_id)
                )
                class_info = class_result.scalar_one_or_none()
                
                if not class_info:
                    return {"error": "Class not found"}
                
                # Get all students in class
                students_result = await session.execute(
                    select(Student, User)
                    .join(User, Student.user_id == User.id)
                    .where(Student.class_id == class_info.id)
                )
                
                students = students_result.all()
                total_students = len(students)
                
                # Get exam statistics
                exam_stats = await session.execute(
                    select(
                        func.avg(ExamResult.marks_obtained).label("avg_marks"),
                        func.count(ExamResult.id).label("total_exams")
                    )
                    .join(Student, ExamResult.student_id == Student.id)
                    .where(Student.class_id == class_info.id)
                )
                stats = exam_stats.first()
                
                return {
                    "class_id": class_id,
                    "class_name": class_info.name,
                    "total_students": total_students,
                    "average_class_performance": round(float(stats.avg_marks or 0), 2),
                    "total_exams_conducted": stats.total_exams or 0
                }
        except Exception as e:
            logger.error(f"Error fetching class performance: {e}")
            return {"error": str(e)}
