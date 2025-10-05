from datetime import datetime
from typing import Dict, List, Optional
import uuid

class UserModel:
    """User model for students, recruiters, and college admins"""
    
    @staticmethod
    def create_user_schema(email: str, password_hash: str, role: str, **kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'email': email,
            'password_hash': password_hash,
            'role': role,  # 'student', 'recruiter', 'college'
            'profile': {
                'full_name': kwargs.get('full_name', ''),
                'phone': kwargs.get('phone', ''),
                'linkedin': kwargs.get('linkedin', ''),
                'github': kwargs.get('github', ''),
                'location': kwargs.get('location', ''),
                'department': kwargs.get('department', '') if role == 'student' else '',
                'graduation_year': kwargs.get('graduation_year', 0) if role == 'student' else 0,
                'gpa': kwargs.get('gpa', 0.0) if role == 'student' else 0.0,
                'company_name': kwargs.get('company_name', '') if role == 'recruiter' else '',
                'company_website': kwargs.get('company_website', '') if role == 'recruiter' else '',
                'industry': kwargs.get('industry', '') if role == 'recruiter' else '',
                'college_name': kwargs.get('college_name', '') if role == 'college' else '',
            },
            'settings': {
                'email_notifications': True,
                'sms_notifications': False,
                'profile_visibility': 'public',
            },
            'resume_file_id': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': True
        }

class JobModel:
    """Job posting model"""
    
    @staticmethod
    def create_job_schema(recruiter_id: str, **kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'recruiter_id': recruiter_id,
            'title': kwargs.get('title', ''),
            'company': kwargs.get('company', ''),
            'location': kwargs.get('location', ''),
            'job_type': kwargs.get('job_type', 'full-time'),  # 'full-time', 'part-time', 'internship', 'contract'
            'description': kwargs.get('description', ''),
            'responsibilities': kwargs.get('responsibilities', ''),
            'qualifications': kwargs.get('qualifications', ''),
            'skills_required': kwargs.get('skills_required', []),
            'salary': {
                'min': kwargs.get('min_salary', 0),
                'max': kwargs.get('max_salary', 0),
                'currency': kwargs.get('currency', 'USD')
            },
            'experience_level': kwargs.get('experience_level', 'entry'),  # 'entry', 'mid', 'senior'
            'application_deadline': kwargs.get('application_deadline'),
            'status': 'active',  # 'active', 'paused', 'closed'
            'applications_count': 0,
            'views_count': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

class ApplicationModel:
    """Job application model"""
    
    @staticmethod
    def create_application_schema(job_id: str, student_id: str, **kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'job_id': job_id,
            'student_id': student_id,
            'personal_details': {
                'full_name': kwargs.get('full_name', ''),
                'email': kwargs.get('email', ''),
                'phone': kwargs.get('phone', ''),
                'linkedin': kwargs.get('linkedin', ''),
                'github': kwargs.get('github', ''),
                'location': kwargs.get('location', ''),
            },
            'resume_file_id': kwargs.get('resume_file_id'),
            'cover_letter': kwargs.get('cover_letter', ''),
            'status': 'submitted',  # 'submitted', 'under_review', 'interview_scheduled', 'accepted', 'rejected'
            'notes': [],  # Internal notes from recruiters
            'applied_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

class InterviewModel:
    """Interview scheduling model"""
    
    @staticmethod
    def create_interview_schema(application_id: str, recruiter_id: str, student_id: str, **kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'application_id': application_id,
            'recruiter_id': recruiter_id,
            'student_id': student_id,
            'interview_type': kwargs.get('interview_type', 'technical'),  # 'technical', 'hr', 'behavioral', 'final'
            'scheduled_date': kwargs.get('scheduled_date'),
            'duration_minutes': kwargs.get('duration_minutes', 60),
            'location': kwargs.get('location', ''),  # Can be physical address or video call link
            'instructions': kwargs.get('instructions', ''),
            'status': 'scheduled',  # 'scheduled', 'completed', 'cancelled', 'rescheduled'
            'feedback': {
                'rating': None,  # 1-5 scale
                'comments': '',
                'recommendation': ''  # 'hire', 'no_hire', 'maybe'
            },
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

class CompanyModel:
    """Company information model"""
    
    @staticmethod
    def create_company_schema(**kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'name': kwargs.get('name', ''),
            'website': kwargs.get('website', ''),
            'industry': kwargs.get('industry', ''),
            'size': kwargs.get('size', ''),  # 'startup', 'small', 'medium', 'large', 'enterprise'
            'description': kwargs.get('description', ''),
            'logo_url': kwargs.get('logo_url', ''),
            'headquarters': kwargs.get('headquarters', ''),
            'founded_year': kwargs.get('founded_year', 0),
            'active_jobs_count': 0,
            'total_hires': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

class NotificationModel:
    """Notification model"""
    
    @staticmethod
    def create_notification_schema(user_id: str, **kwargs) -> Dict:
        return {
            '_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': kwargs.get('title', ''),
            'message': kwargs.get('message', ''),
            'type': kwargs.get('type', 'info'),  # 'info', 'success', 'warning', 'error'
            'related_id': kwargs.get('related_id'),  # ID of related job, application, etc.
            'related_type': kwargs.get('related_type'),  # 'job', 'application', 'interview'
            'is_read': False,
            'created_at': datetime.utcnow()
        }

# Validation utilities
class ValidationUtils:
    @staticmethod
    def validate_email(email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_role(role: str) -> bool:
        return role in ['student', 'recruiter', 'college']
    
    @staticmethod
    def validate_job_type(job_type: str) -> bool:
        return job_type in ['full-time', 'part-time', 'internship', 'contract']
    
    @staticmethod
    def validate_application_status(status: str) -> bool:
        return status in ['submitted', 'under_review', 'interview_scheduled', 'accepted', 'rejected']
    
    @staticmethod
    def validate_interview_status(status: str) -> bool:
        return status in ['scheduled', 'completed', 'cancelled', 'rescheduled']