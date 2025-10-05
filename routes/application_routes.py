from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import datetime
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import ApplicationModel, ValidationUtils, NotificationModel
from utils.database import db_utils
from routes.auth_routes import token_required
from config import Config

application_bp = Blueprint('applications', __name__)

@application_bp.route('/', methods=['POST'])
@token_required
def create_application(current_user_id):
    """Create a new job application (students only)"""
    try:
        data = request.get_json()
        
        # Verify user is a student
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'student':
            return jsonify({
                'message': 'Access denied. Only students can submit job applications!',
                'success': False
            }), 403
        
        # Validate required fields
        if not data or not data.get('job_id'):
            return jsonify({
                'message': 'Job ID is required!',
                'success': False
            }), 400
        
        job_id = data['job_id']
        
        # Check if job exists and is active
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': job_id, 'status': 'active'})
        
        if not job:
            return jsonify({
                'message': 'Job not found or no longer active!',
                'success': False
            }), 404
        
        # Check if user has already applied for this job
        applications_collection = db_utils.get_collection('applications')
        existing_application = applications_collection.find_one({
            'job_id': job_id,
            'student_id': current_user_id
        })
        
        if existing_application:
            return jsonify({
                'message': 'You have already applied for this job!',
                'success': False
            }), 409
        
        # Check application deadline
        if job.get('application_deadline'):
            if datetime.datetime.utcnow() > job['application_deadline']:
                return jsonify({
                    'message': 'Application deadline has passed!',
                    'success': False
                }), 400
        
        # Create application document
        application_data = ApplicationModel.create_application_schema(
            job_id=job_id,
            student_id=current_user_id,
            full_name=data.get('full_name', user['profile']['full_name']),
            email=data.get('email', user['email']),
            phone=data.get('phone', user['profile']['phone']),
            linkedin=data.get('linkedin', user['profile']['linkedin']),
            github=data.get('github', user['profile']['github']),
            location=data.get('location', user['profile']['location']),
            resume_file_id=data.get('resume_file_id'),
            cover_letter=data.get('cover_letter', '')
        )
        
        # Insert application into database
        result = applications_collection.insert_one(application_data)
        
        if result.inserted_id:
            # Update application count for the job
            jobs_collection.update_one(
                {'_id': job_id},
                {'$inc': {'applications_count': 1}}
            )
            
            # Create notification for recruiter
            notifications_collection = db_utils.get_collection('notifications')
            notification_data = NotificationModel.create_notification_schema(
                user_id=job['recruiter_id'],
                title='New Job Application',
                message=f"New application received for {job['title']}",
                type='info',
                related_id=application_data['_id'],
                related_type='application'
            )
            notifications_collection.insert_one(notification_data)
            
            return jsonify({
                'message': 'Application submitted successfully!',
                'success': True,
                'application_id': application_data['_id'],
                'application': {
                    'id': application_data['_id'],
                    'job_id': job_id,
                    'job_title': job['title'],
                    'company': job['company'],
                    'status': application_data['status'],
                    'applied_at': application_data['applied_at'].isoformat()
                }
            }), 201
        else:
            return jsonify({
                'message': 'Failed to submit application!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to create application: {str(e)}',
            'success': False
        }), 500

@application_bp.route('/my-applications', methods=['GET'])
@token_required
def get_my_applications(current_user_id):
    """Get applications submitted by the current student"""
    try:
        # Verify user is a student
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'student':
            return jsonify({
                'message': 'Access denied. Only students can view their applications!',
                'success': False
            }), 403
        
        # Get query parameters
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Build query
        query = {'student_id': current_user_id}
        if status and ValidationUtils.validate_application_status(status):
            query['status'] = status
        
        # Execute query with pagination
        applications_collection = db_utils.get_collection('applications')
        skip = (page - 1) * limit
        
        cursor = applications_collection.find(query).sort([('applied_at', -1)]).skip(skip).limit(limit)
        applications = list(cursor)
        total_count = applications_collection.count_documents(query)
        
        # Get job information for each application
        jobs_collection = db_utils.get_collection('jobs')
        application_list = []
        
        for application in applications:
            job = jobs_collection.find_one({'_id': application['job_id']})
            
            app_data = {
                'id': application['_id'],
                'job_id': application['job_id'],
                'job_title': job['title'] if job else 'Unknown',
                'company': job['company'] if job else 'Unknown',
                'location': job['location'] if job else 'Unknown',
                'status': application['status'],
                'applied_at': application['applied_at'].isoformat(),
                'updated_at': application['updated_at'].isoformat(),
                'personal_details': application['personal_details']
            }
            application_list.append(app_data)
        
        return jsonify({
            'message': 'Applications retrieved successfully!',
            'success': True,
            'applications': application_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve applications: {str(e)}',
            'success': False
        }), 500

@application_bp.route('/job/<job_id>', methods=['GET'])
@token_required
def get_applications_for_job(current_user_id, job_id):
    """Get all applications for a specific job (recruiters only)"""
    try:
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can view job applications!',
                'success': False
            }), 403
        
        # Check if job exists and user is the owner
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': job_id})
        
        if not job:
            return jsonify({
                'message': 'Job not found!',
                'success': False
            }), 404
        
        if job['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only view applications for your own jobs!',
                'success': False
            }), 403
        
        # Get query parameters
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Build query
        query = {'job_id': job_id}
        if status and ValidationUtils.validate_application_status(status):
            query['status'] = status
        
        # Execute query with pagination
        applications_collection = db_utils.get_collection('applications')
        skip = (page - 1) * limit
        
        cursor = applications_collection.find(query).sort([('applied_at', -1)]).skip(skip).limit(limit)
        applications = list(cursor)
        total_count = applications_collection.count_documents(query)
        
        # Get student information for each application
        application_list = []
        for application in applications:
            student = users_collection.find_one(
                {'_id': application['student_id']},
                {'password_hash': 0}
            )
            
            app_data = {
                'id': application['_id'],
                'student_id': application['student_id'],
                'student_name': application['personal_details']['full_name'],
                'student_email': application['personal_details']['email'],
                'student_phone': application['personal_details']['phone'],
                'student_profile': student['profile'] if student else {},
                'status': application['status'],
                'applied_at': application['applied_at'].isoformat(),
                'updated_at': application['updated_at'].isoformat(),
                'personal_details': application['personal_details'],
                'cover_letter': application.get('cover_letter', ''),
                'resume_file_id': application.get('resume_file_id'),
                'notes': application.get('notes', [])
            }
            application_list.append(app_data)
        
        return jsonify({
            'message': 'Applications retrieved successfully!',
            'success': True,
            'job_title': job['title'],
            'applications': application_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve applications: {str(e)}',
            'success': False
        }), 500

@application_bp.route('/<application_id>', methods=['GET'])
@token_required
def get_application_details(current_user_id, application_id):
    """Get detailed application information"""
    try:
        applications_collection = db_utils.get_collection('applications')
        application = applications_collection.find_one({'_id': application_id})
        
        if not application:
            return jsonify({
                'message': 'Application not found!',
                'success': False
            }), 404
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        # Check if user has permission to view this application
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': application['job_id']})
        
        can_view = False
        if user['role'] == 'student' and application['student_id'] == current_user_id:
            can_view = True
        elif user['role'] == 'recruiter' and job and job['recruiter_id'] == current_user_id:
            can_view = True
        elif user['role'] == 'college':
            can_view = True
        
        if not can_view:
            return jsonify({
                'message': 'Access denied!',
                'success': False
            }), 403
        
        # Get student information
        student = users_collection.find_one(
            {'_id': application['student_id']},
            {'password_hash': 0}
        )
        
        # Prepare detailed response
        app_data = {
            'id': application['_id'],
            'job_id': application['job_id'],
            'job_title': job['title'] if job else 'Unknown',
            'company': job['company'] if job else 'Unknown',
            'student_id': application['student_id'],
            'student_profile': student['profile'] if student else {},
            'personal_details': application['personal_details'],
            'status': application['status'],
            'cover_letter': application.get('cover_letter', ''),
            'resume_file_id': application.get('resume_file_id'),
            'notes': application.get('notes', []),
            'applied_at': application['applied_at'].isoformat(),
            'updated_at': application['updated_at'].isoformat()
        }
        
        return jsonify({
            'message': 'Application details retrieved successfully!',
            'success': True,
            'application': app_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve application details: {str(e)}',
            'success': False
        }), 500

@application_bp.route('/<application_id>/status', methods=['PUT'])
@token_required
def update_application_status(current_user_id, application_id):
    """Update application status (recruiters only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('status'):
            return jsonify({
                'message': 'Status is required!',
                'success': False
            }), 400
        
        new_status = data['status']
        if not ValidationUtils.validate_application_status(new_status):
            return jsonify({
                'message': 'Invalid application status!',
                'success': False
            }), 400
        
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can update application status!',
                'success': False
            }), 403
        
        applications_collection = db_utils.get_collection('applications')
        application = applications_collection.find_one({'_id': application_id})
        
        if not application:
            return jsonify({
                'message': 'Application not found!',
                'success': False
            }), 404
        
        # Check if user owns the job
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': application['job_id']})
        
        if not job or job['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only update applications for your own jobs!',
                'success': False
            }), 403
        
        # Update application status
        update_data = {
            'status': new_status,
            'updated_at': datetime.datetime.utcnow()
        }
        
        # Add note if provided
        if data.get('note'):
            note = {
                'content': data['note'],
                'added_by': current_user_id,
                'added_at': datetime.datetime.utcnow()
            }
            applications_collection.update_one(
                {'_id': application_id},
                {'$push': {'notes': note}}
            )
        
        result = applications_collection.update_one(
            {'_id': application_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Create notification for student
            notifications_collection = db_utils.get_collection('notifications')
            notification_data = NotificationModel.create_notification_schema(
                user_id=application['student_id'],
                title='Application Status Updated',
                message=f"Your application for {job['title']} has been updated to: {new_status}",
                type='info',
                related_id=application_id,
                related_type='application'
            )
            notifications_collection.insert_one(notification_data)
            
            return jsonify({
                'message': 'Application status updated successfully!',
                'success': True,
                'application': {
                    'id': application_id,
                    'status': new_status,
                    'updated_at': update_data['updated_at'].isoformat()
                }
            }), 200
        else:
            return jsonify({
                'message': 'Failed to update application status!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to update application status: {str(e)}',
            'success': False
        }), 500

@application_bp.route('/<application_id>/notes', methods=['POST'])
@token_required
def add_application_note(current_user_id, application_id):
    """Add a note to an application (recruiters only)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('note'):
            return jsonify({
                'message': 'Note content is required!',
                'success': False
            }), 400
        
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can add notes!',
                'success': False
            }), 403
        
        applications_collection = db_utils.get_collection('applications')
        application = applications_collection.find_one({'_id': application_id})
        
        if not application:
            return jsonify({
                'message': 'Application not found!',
                'success': False
            }), 404
        
        # Check if user owns the job
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': application['job_id']})
        
        if not job or job['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only add notes to applications for your own jobs!',
                'success': False
            }), 403
        
        # Add note
        note = {
            'content': data['note'],
            'added_by': current_user_id,
            'added_by_name': user['profile']['full_name'],
            'added_at': datetime.datetime.utcnow()
        }
        
        result = applications_collection.update_one(
            {'_id': application_id},
            {
                '$push': {'notes': note},
                '$set': {'updated_at': datetime.datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                'message': 'Note added successfully!',
                'success': True,
                'note': {
                    'content': note['content'],
                    'added_by_name': note['added_by_name'],
                    'added_at': note['added_at'].isoformat()
                }
            }), 201
        else:
            return jsonify({
                'message': 'Failed to add note!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to add note: {str(e)}',
            'success': False
        }), 500