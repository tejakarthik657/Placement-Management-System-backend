#!/usr/bin/env python
"""
Setup script for Placement Management System Backend
This script initializes the database with indexes and optional sample data.
"""

import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import db_utils
from werkzeug.security import generate_password_hash
from models.models import UserModel, JobModel

def create_indexes():
    """Create database indexes for better performance"""
    print("Creating database indexes...")
    try:
        db_utils.create_indexes()
        print("✅ Database indexes created successfully!")
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False
    return True

def create_sample_users():
    """Create sample users for testing"""
    print("Creating sample users...")
    try:
        users_collection = db_utils.get_collection('users')
        
        # Sample College Admin
        college_admin = UserModel.create_user_schema(
            email="admin@college.edu",
            password_hash=generate_password_hash("admin123"),
            role="college",
            full_name="College Administrator",
            phone="+1234567890",
            location="Campus, University",
            college_name="Sample University"
        )
        
        # Sample Recruiter
        recruiter = UserModel.create_user_schema(
            email="recruiter@techcorp.com",
            password_hash=generate_password_hash("recruiter123"),
            role="recruiter",
            full_name="John Recruiter",
            phone="+1234567891",
            location="San Francisco, CA",
            company_name="Tech Innovators Inc.",
            company_website="https://techinnovators.com",
            industry="Technology"
        )
        
        # Sample Student
        student = UserModel.create_user_schema(
            email="student@university.edu",
            password_hash=generate_password_hash("student123"),
            role="student",
            full_name="Jane Student",
            phone="+1234567892",
            location="University City, State",
            department="Computer Science",
            graduation_year=2024,
            gpa=3.8
        )
        
        # Insert sample users
        for user in [college_admin, recruiter, student]:
            existing = users_collection.find_one({'email': user['email']})
            if not existing:
                users_collection.insert_one(user)
                print(f"✅ Created user: {user['email']} ({user['role']})")
            else:
                print(f"⚠️  User already exists: {user['email']}")
                
    except Exception as e:
        print(f"❌ Error creating sample users: {e}")
        return False
    return True

def create_sample_jobs():
    """Create sample job postings"""
    print("Creating sample jobs...")
    try:
        users_collection = db_utils.get_collection('users')
        jobs_collection = db_utils.get_collection('jobs')
        
        # Find the sample recruiter
        recruiter = users_collection.find_one({'email': 'recruiter@techcorp.com'})
        if not recruiter:
            print("⚠️  Sample recruiter not found, skipping job creation")
            return False
        
        sample_jobs = [
            {
                'title': 'Software Engineer Intern',
                'company': 'Tech Innovators Inc.',
                'location': 'San Francisco, CA',
                'job_type': 'internship',
                'description': 'Join our dynamic team as a Software Engineer Intern. You will work on cutting-edge projects and learn from industry experts.',
                'responsibilities': '• Develop and maintain web applications\n• Collaborate with cross-functional teams\n• Participate in code reviews\n• Learn new technologies and frameworks',
                'qualifications': '• Currently pursuing a degree in Computer Science or related field\n• Knowledge of JavaScript, Python, or Java\n• Strong problem-solving skills\n• Excellent communication skills',
                'skills_required': ['JavaScript', 'Python', 'React', 'Git'],
                'min_salary': 4000,
                'max_salary': 6000,
                'experience_level': 'entry',
            },
            {
                'title': 'Data Analyst',
                'company': 'Data Insights Corp.',
                'location': 'New York, NY',
                'job_type': 'full-time',
                'description': 'We are seeking a skilled Data Analyst to join our analytics team and help drive data-driven decision making.',
                'responsibilities': '• Analyze large datasets to identify trends and patterns\n• Create visualizations and reports\n• Collaborate with stakeholders to understand requirements\n• Maintain and improve data pipelines',
                'qualifications': '• Bachelor\'s degree in Statistics, Mathematics, or related field\n• 2+ years of experience in data analysis\n• Proficiency in SQL and Python\n• Experience with data visualization tools',
                'skills_required': ['SQL', 'Python', 'Tableau', 'Excel', 'Statistics'],
                'min_salary': 65000,
                'max_salary': 85000,
                'experience_level': 'mid',
            },
            {
                'title': 'Frontend Developer',
                'company': 'Creative Design Studio',
                'location': 'Los Angeles, CA',
                'job_type': 'full-time',
                'description': 'Looking for a talented Frontend Developer to create amazing user experiences for our web applications.',
                'responsibilities': '• Develop responsive web interfaces\n• Implement UI/UX designs\n• Optimize applications for performance\n• Work closely with designers and backend developers',
                'qualifications': '• Bachelor\'s degree in Computer Science or equivalent experience\n• 3+ years of frontend development experience\n• Strong knowledge of modern JavaScript frameworks\n• Understanding of web standards and accessibility',
                'skills_required': ['React', 'TypeScript', 'CSS3', 'HTML5', 'Webpack'],
                'min_salary': 70000,
                'max_salary': 95000,
                'experience_level': 'mid',
            }
        ]
        
        for job_data in sample_jobs:
            job = JobModel.create_job_schema(
                recruiter_id=recruiter['_id'],
                **job_data
            )
            
            existing = jobs_collection.find_one({'title': job['title'], 'company': job['company']})
            if not existing:
                jobs_collection.insert_one(job)
                print(f"✅ Created job: {job['title']} at {job['company']}")
            else:
                print(f"⚠️  Job already exists: {job['title']}")
                
    except Exception as e:
        print(f"❌ Error creating sample jobs: {e}")
        return False
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Placement Management System Backend...")
    print("=" * 50)
    
    # Test database connection
    try:
        db = db_utils.get_database()
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your MongoDB connection string and try again.")
        return
    
    # Create indexes
    if not create_indexes():
        print("❌ Setup failed during index creation")
        return
    
    # Ask if user wants to create sample data
    print("\n" + "=" * 50)
    create_samples = input("Do you want to create sample data for testing? (y/N): ").lower().strip()
    
    if create_samples in ['y', 'yes']:
        print("\nCreating sample data...")
        
        if create_sample_users():
            create_sample_jobs()
        
        print("\n📝 Sample Credentials Created:")
        print("=" * 30)
        print("College Admin:")
        print("  Email: admin@college.edu")
        print("  Password: admin123")
        print()
        print("Recruiter:")
        print("  Email: recruiter@techcorp.com") 
        print("  Password: recruiter123")
        print()
        print("Student:")
        print("  Email: student@university.edu")
        print("  Password: student123")
        print()
    
    print("=" * 50)
    print("✅ Setup completed successfully!")
    print("🚀 You can now start the Flask application with: python app.py")
    print("📖 API Documentation: See API_DOCUMENTATION.md")
    print("🌐 Health Check: http://localhost:5000/")

if __name__ == '__main__':
    main()