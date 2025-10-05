from flask import Blueprint, request, jsonify
import datetime
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JobModel, ValidationUtils
from utils.database import db_utils
from routes.auth_routes import token_required

job_bp = Blueprint('jobs', __name__)

@job_bp.route('/', methods=['GET'])
@job_bp.route('', methods=['GET'])
def get_jobs():
    """Get all jobs with filtering and pagination"""
    try:
        # Get query parameters
        search = request.args.get('search', '')
        location = request.args.get('location', '')
        job_type = request.args.get('job_type', '')
        experience_level = request.args.get('experience_level', '')
        company = request.args.get('company', '')
        min_salary = request.args.get('min_salary')
        max_salary = request.args.get('max_salary')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = {'status': 'active'}
        
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'company': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}},
                {'skills_required': {'$regex': search, '$options': 'i'}}
            ]
        
        if location:
            query['location'] = {'$regex': location, '$options': 'i'}
        
        if job_type and ValidationUtils.validate_job_type(job_type):
            query['job_type'] = job_type
        
        if experience_level:
            query['experience_level'] = experience_level
        
        if company:
            query['company'] = {'$regex': company, '$options': 'i'}
        
        # Salary range filtering
        if min_salary:
            try:
                query['salary.min'] = {'$gte': int(min_salary)}
            except ValueError:
                pass
        
        if max_salary:
            try:
                query['salary.max'] = {'$lte': int(max_salary)}
            except ValueError:
                pass
        
        # Sorting
        sort_direction = 1 if sort_order == 'asc' else -1
        sort_criteria = [(sort_by, sort_direction)]
        
        # Execute query with pagination
        jobs_collection = db_utils.get_collection('jobs')
        skip = (page - 1) * limit
        
        cursor = jobs_collection.find(query).sort(sort_criteria).skip(skip).limit(limit)
        jobs = list(cursor)
        total_count = jobs_collection.count_documents(query)
        
        # Format jobs data
        job_list = []
        for job in jobs:
            job_data = {
                'id': job['_id'],
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'job_type': job['job_type'],
                'description': job['description'],
                'responsibilities': job['responsibilities'],
                'qualifications': job['qualifications'],
                'skills_required': job['skills_required'],
                'salary': job['salary'],
                'experience_level': job['experience_level'],
                'application_deadline': job.get('application_deadline'),
                'applications_count': job.get('applications_count', 0),
                'views_count': job.get('views_count', 0),
                'created_at': job['created_at'].isoformat(),
                'updated_at': job['updated_at'].isoformat()
            }
            job_list.append(job_data)
        
        return jsonify({
            'message': 'Jobs retrieved successfully!',
            'success': True,
            'jobs': job_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve jobs: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/<job_id>', methods=['GET'])
def get_job_by_id(job_id):
    """Get a specific job by ID and increment view count"""
    try:
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': job_id, 'status': 'active'})
        
        if not job:
            return jsonify({
                'message': 'Job not found!',
                'success': False
            }), 404
        
        # Increment view count
        jobs_collection.update_one(
            {'_id': job_id},
            {'$inc': {'views_count': 1}}
        )
        
        # Get recruiter information
        users_collection = db_utils.get_collection('users')
        recruiter = users_collection.find_one({
            '_id': job['recruiter_id'],
            'is_active': True
        }, {'password_hash': 0})
        
        job_data = {
            'id': job['_id'],
            'title': job['title'],
            'company': job['company'],
            'location': job['location'],
            'job_type': job['job_type'],
            'description': job['description'],
            'responsibilities': job['responsibilities'],
            'qualifications': job['qualifications'],
            'skills_required': job['skills_required'],
            'salary': job['salary'],
            'experience_level': job['experience_level'],
            'application_deadline': job.get('application_deadline'),
            'applications_count': job.get('applications_count', 0),
            'views_count': job.get('views_count', 1),
            'recruiter': recruiter['profile'] if recruiter else None,
            'created_at': job['created_at'].isoformat(),
            'updated_at': job['updated_at'].isoformat()
        }
        
        return jsonify({
            'message': 'Job retrieved successfully!',
            'success': True,
            'job': job_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve job: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/', methods=['POST'])
@job_bp.route('', methods=['POST'])
@token_required
def create_job(current_user_id):
    """Create a new job posting (recruiters only)"""
    try:
        data = request.get_json()
        
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can create job postings!',
                'success': False
            }), 403
        
        # Validate required fields
        required_fields = ['title', 'company', 'location', 'job_type', 'description']
        for field in required_fields:
            if not data or not data.get(field):
                return jsonify({
                    'message': f'{field} is required!',
                    'success': False
                }), 400
        
        # Validate job type
        if not ValidationUtils.validate_job_type(data['job_type']):
            return jsonify({
                'message': 'Invalid job type!',
                'success': False
            }), 400
        
        # Parse application deadline if provided
        application_deadline = None
        if data.get('application_deadline'):
            try:
                application_deadline = datetime.datetime.fromisoformat(
                    data['application_deadline'].replace('Z', '+00:00')
                )
            except ValueError:
                return jsonify({
                    'message': 'Invalid application deadline format!',
                    'success': False
                }), 400
        
        # Create job document
        job_data = JobModel.create_job_schema(
            recruiter_id=current_user_id,
            title=data['title'],
            company=data['company'],
            location=data['location'],
            job_type=data['job_type'],
            description=data['description'],
            responsibilities=data.get('responsibilities', ''),
            qualifications=data.get('qualifications', ''),
            skills_required=data.get('skills_required', []),
            min_salary=data.get('min_salary', 0),
            max_salary=data.get('max_salary', 0),
            currency=data.get('currency', 'USD'),
            experience_level=data.get('experience_level', 'entry'),
            application_deadline=application_deadline
        )
        
        # Insert job into database
        jobs_collection = db_utils.get_collection('jobs')
        result = jobs_collection.insert_one(job_data)
        
        if result.inserted_id:
            return jsonify({
                'message': 'Job created successfully!',
                'success': True,
                'job_id': job_data['_id'],
                'job': {
                    'id': job_data['_id'],
                    'title': job_data['title'],
                    'company': job_data['company'],
                    'location': job_data['location'],
                    'job_type': job_data['job_type'],
                    'created_at': job_data['created_at'].isoformat()
                }
            }), 201
        else:
            return jsonify({
                'message': 'Failed to create job!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to create job: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/<job_id>', methods=['PUT'])
@token_required
def update_job(current_user_id, job_id):
    """Update a job posting (job owner only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'message': 'No update data provided!',
                'success': False
            }), 400
        
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': job_id})
        
        if not job:
            return jsonify({
                'message': 'Job not found!',
                'success': False
            }), 404
        
        # Check if user is the job owner
        if job['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only update your own job postings!',
                'success': False
            }), 403
        
        # Prepare update data
        update_data = {}
        updatable_fields = [
            'title', 'company', 'location', 'job_type', 'description', 
            'responsibilities', 'qualifications', 'skills_required',
            'experience_level', 'status'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field == 'job_type' and not ValidationUtils.validate_job_type(data[field]):
                    return jsonify({
                        'message': 'Invalid job type!',
                        'success': False
                    }), 400
                update_data[field] = data[field]
        
        # Update salary if provided
        if 'min_salary' in data or 'max_salary' in data or 'currency' in data:
            salary_update = job.get('salary', {})
            if 'min_salary' in data:
                salary_update['min'] = data['min_salary']
            if 'max_salary' in data:
                salary_update['max'] = data['max_salary']
            if 'currency' in data:
                salary_update['currency'] = data['currency']
            update_data['salary'] = salary_update
        
        # Update application deadline if provided
        if 'application_deadline' in data:
            try:
                if data['application_deadline']:
                    update_data['application_deadline'] = datetime.datetime.fromisoformat(
                        data['application_deadline'].replace('Z', '+00:00')
                    )
                else:
                    update_data['application_deadline'] = None
            except ValueError:
                return jsonify({
                    'message': 'Invalid application deadline format!',
                    'success': False
                }), 400
        
        if update_data:
            update_data['updated_at'] = datetime.datetime.utcnow()
            
            result = jobs_collection.update_one(
                {'_id': job_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                # Get updated job data
                updated_job = jobs_collection.find_one({'_id': job_id})
                
                job_data = {
                    'id': updated_job['_id'],
                    'title': updated_job['title'],
                    'company': updated_job['company'],
                    'location': updated_job['location'],
                    'job_type': updated_job['job_type'],
                    'status': updated_job['status'],
                    'updated_at': updated_job['updated_at'].isoformat()
                }
                
                return jsonify({
                    'message': 'Job updated successfully!',
                    'success': True,
                    'job': job_data
                }), 200
            else:
                return jsonify({
                    'message': 'No changes were made to the job!',
                    'success': True
                }), 200
        else:
            return jsonify({
                'message': 'No valid fields provided for update!',
                'success': False
            }), 400
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to update job: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/<job_id>', methods=['DELETE'])
@token_required
def delete_job(current_user_id, job_id):
    """Delete/deactivate a job posting (job owner only)"""
    try:
        jobs_collection = db_utils.get_collection('jobs')
        job = jobs_collection.find_one({'_id': job_id})
        
        if not job:
            return jsonify({
                'message': 'Job not found!',
                'success': False
            }), 404
        
        # Check if user is the job owner
        if job['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only delete your own job postings!',
                'success': False
            }), 403
        
        # Instead of deleting, mark as closed
        result = jobs_collection.update_one(
            {'_id': job_id},
            {
                '$set': {
                    'status': 'closed',
                    'closed_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                'message': 'Job deleted successfully!',
                'success': True
            }), 200
        else:
            return jsonify({
                'message': 'Failed to delete job!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to delete job: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/my-jobs', methods=['GET'])
@token_required
def get_my_jobs(current_user_id):
    """Get jobs posted by the current recruiter"""
    try:
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can view their job postings!',
                'success': False
            }), 403
        
        # Get query parameters
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Build query
        query = {'recruiter_id': current_user_id}
        if status != 'all':
            query['status'] = status
        
        # Execute query with pagination
        jobs_collection = db_utils.get_collection('jobs')
        skip = (page - 1) * limit
        
        cursor = jobs_collection.find(query).sort([('created_at', -1)]).skip(skip).limit(limit)
        jobs = list(cursor)
        total_count = jobs_collection.count_documents(query)
        
        # Format jobs data with application counts
        applications_collection = db_utils.get_collection('applications')
        job_list = []
        
        for job in jobs:
            # Get application count for this job
            app_count = applications_collection.count_documents({'job_id': job['_id']})
            
            job_data = {
                'id': job['_id'],
                'title': job['title'],
                'company': job['company'],
                'location': job['location'],
                'job_type': job['job_type'],
                'status': job['status'],
                'applications_count': app_count,
                'views_count': job.get('views_count', 0),
                'application_deadline': job.get('application_deadline'),
                'created_at': job['created_at'].isoformat(),
                'updated_at': job['updated_at'].isoformat()
            }
            job_list.append(job_data)
        
        return jsonify({
            'message': 'Your jobs retrieved successfully!',
            'success': True,
            'jobs': job_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve your jobs: {str(e)}',
            'success': False
        }), 500

@job_bp.route('/statistics', methods=['GET'])
@token_required
def get_job_statistics(current_user_id):
    """Get job statistics for the current user"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        jobs_collection = db_utils.get_collection('jobs')
        applications_collection = db_utils.get_collection('applications')
        
        if user['role'] == 'recruiter':
            # Statistics for recruiters
            stats = {
                'total_jobs': jobs_collection.count_documents({'recruiter_id': current_user_id}),
                'active_jobs': jobs_collection.count_documents({'recruiter_id': current_user_id, 'status': 'active'}),
                'closed_jobs': jobs_collection.count_documents({'recruiter_id': current_user_id, 'status': 'closed'}),
                'total_applications': applications_collection.count_documents({
                    'job_id': {'$in': [job['_id'] for job in jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1})]}
                })
            }
            
        elif user['role'] == 'student':
            # Statistics for students
            stats = {
                'total_applications': applications_collection.count_documents({'student_id': current_user_id}),
                'pending_applications': applications_collection.count_documents({
                    'student_id': current_user_id, 
                    'status': {'$in': ['submitted', 'under_review']}
                }),
                'interview_scheduled': applications_collection.count_documents({
                    'student_id': current_user_id, 
                    'status': 'interview_scheduled'
                }),
                'accepted_applications': applications_collection.count_documents({
                    'student_id': current_user_id, 
                    'status': 'accepted'
                })
            }
            
        elif user['role'] == 'college':
            # Statistics for college admins
            total_jobs = jobs_collection.count_documents({'status': 'active'})
            total_applications = applications_collection.count_documents({})
            stats = {
                'total_active_jobs': total_jobs,
                'total_applications': total_applications,
                'total_students': users_collection.count_documents({'role': 'student', 'is_active': True}),
                'total_recruiters': users_collection.count_documents({'role': 'recruiter', 'is_active': True})
            }
        
        return jsonify({
            'message': 'Statistics retrieved successfully!',
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve statistics: {str(e)}',
            'success': False
        }), 500