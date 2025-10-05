from flask import Blueprint, request, jsonify
import datetime
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import InterviewModel, ValidationUtils, NotificationModel
from utils.database import db_utils
from routes.auth_routes import token_required

interview_bp = Blueprint('interviews', __name__)

@interview_bp.route('/', methods=['POST'])
@token_required
def schedule_interview(current_user_id):
    """Schedule a new interview (recruiters only)"""
    try:
        data = request.get_json()
        
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can schedule interviews!',
                'success': False
            }), 403
        
        # Validate required fields
        required_fields = ['application_id', 'scheduled_date', 'duration_minutes']
        for field in required_fields:
            if not data or not data.get(field):
                return jsonify({
                    'message': f'{field} is required!',
                    'success': False
                }), 400
        
        application_id = data['application_id']
        
        # Check if application exists
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
                'message': 'Access denied. You can only schedule interviews for your own job applications!',
                'success': False
            }), 403
        
        # Parse scheduled date
        try:
            scheduled_date = datetime.datetime.fromisoformat(
                data['scheduled_date'].replace('Z', '+00:00')
            )
        except ValueError:
            return jsonify({
                'message': 'Invalid scheduled date format!',
                'success': False
            }), 400
        
        # Check if scheduled date is in the future
        if scheduled_date <= datetime.datetime.utcnow():
            return jsonify({
                'message': 'Scheduled date must be in the future!',
                'success': False
            }), 400
        
        # Check if there's already an interview scheduled for this application
        interviews_collection = db_utils.get_collection('interviews')
        existing_interview = interviews_collection.find_one({
            'application_id': application_id,
            'status': {'$in': ['scheduled', 'rescheduled']}
        })
        
        if existing_interview:
            return jsonify({
                'message': 'An interview is already scheduled for this application!',
                'success': False
            }), 409
        
        # Create interview document
        interview_data = InterviewModel.create_interview_schema(
            application_id=application_id,
            recruiter_id=current_user_id,
            student_id=application['student_id'],
            interview_type=data.get('interview_type', 'technical'),
            scheduled_date=scheduled_date,
            duration_minutes=data['duration_minutes'],
            location=data.get('location', ''),
            instructions=data.get('instructions', '')
        )
        
        # Insert interview into database
        result = interviews_collection.insert_one(interview_data)
        
        if result.inserted_id:
            # Update application status to interview_scheduled
            applications_collection.update_one(
                {'_id': application_id},
                {
                    '$set': {
                        'status': 'interview_scheduled',
                        'updated_at': datetime.datetime.utcnow()
                    }
                }
            )
            
            # Create notifications for both student and recruiter
            notifications_collection = db_utils.get_collection('notifications')
            
            # Notification for student
            student_notification = NotificationModel.create_notification_schema(
                user_id=application['student_id'],
                title='Interview Scheduled',
                message=f"Interview scheduled for {job['title']} on {scheduled_date.strftime('%B %d, %Y at %I:%M %p')}",
                type='info',
                related_id=interview_data['_id'],
                related_type='interview'
            )
            notifications_collection.insert_one(student_notification)
            
            return jsonify({
                'message': 'Interview scheduled successfully!',
                'success': True,
                'interview_id': interview_data['_id'],
                'interview': {
                    'id': interview_data['_id'],
                    'application_id': application_id,
                    'interview_type': interview_data['interview_type'],
                    'scheduled_date': scheduled_date.isoformat(),
                    'duration_minutes': interview_data['duration_minutes'],
                    'location': interview_data['location'],
                    'status': interview_data['status'],
                    'created_at': interview_data['created_at'].isoformat()
                }
            }), 201
        else:
            return jsonify({
                'message': 'Failed to schedule interview!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to schedule interview: {str(e)}',
            'success': False
        }), 500

@interview_bp.route('/my-interviews', methods=['GET'])
@token_required
def get_my_interviews(current_user_id):
    """Get interviews for the current user (students or recruiters)"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Get query parameters
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Build query based on user role
        query = {}
        if user['role'] == 'student':
            query['student_id'] = current_user_id
        elif user['role'] == 'recruiter':
            query['recruiter_id'] = current_user_id
        else:
            return jsonify({
                'message': 'Access denied!',
                'success': False
            }), 403
        
        if status and ValidationUtils.validate_interview_status(status):
            query['status'] = status
        
        # Execute query with pagination
        interviews_collection = db_utils.get_collection('interviews')
        skip = (page - 1) * limit
        
        cursor = interviews_collection.find(query).sort([('scheduled_date', 1)]).skip(skip).limit(limit)
        interviews = list(cursor)
        total_count = interviews_collection.count_documents(query)
        
        # Get additional information for each interview
        applications_collection = db_utils.get_collection('applications')
        jobs_collection = db_utils.get_collection('jobs')
        interview_list = []
        
        for interview in interviews:
            # Get application and job information
            application = applications_collection.find_one({'_id': interview['application_id']})
            job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
            
            # Get other party's information
            if user['role'] == 'student':
                # Student view - get recruiter info
                other_user = users_collection.find_one(
                    {'_id': interview['recruiter_id']},
                    {'password_hash': 0}
                )
            else:
                # Recruiter view - get student info
                other_user = users_collection.find_one(
                    {'_id': interview['student_id']},
                    {'password_hash': 0}
                )
            
            interview_data = {
                'id': interview['_id'],
                'application_id': interview['application_id'],
                'job_title': job['title'] if job else 'Unknown',
                'company': job['company'] if job else 'Unknown',
                'interview_type': interview['interview_type'],
                'scheduled_date': interview['scheduled_date'].isoformat() if interview.get('scheduled_date') else None,
                'duration_minutes': interview['duration_minutes'],
                'location': interview['location'],
                'instructions': interview['instructions'],
                'status': interview['status'],
                'other_party': {
                    'name': other_user['profile']['full_name'] if other_user else 'Unknown',
                    'email': other_user['email'] if other_user else 'Unknown'
                },
                'feedback': interview.get('feedback', {}),
                'created_at': interview['created_at'].isoformat(),
                'updated_at': interview['updated_at'].isoformat()
            }
            interview_list.append(interview_data)
        
        return jsonify({
            'message': 'Interviews retrieved successfully!',
            'success': True,
            'interviews': interview_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve interviews: {str(e)}',
            'success': False
        }), 500

@interview_bp.route('/<interview_id>', methods=['GET'])
@token_required
def get_interview_details(current_user_id, interview_id):
    """Get detailed interview information"""
    try:
        interviews_collection = db_utils.get_collection('interviews')
        interview = interviews_collection.find_one({'_id': interview_id})
        
        if not interview:
            return jsonify({
                'message': 'Interview not found!',
                'success': False
            }), 404
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        # Check if user has permission to view this interview
        can_view = False
        if user['role'] == 'student' and interview['student_id'] == current_user_id:
            can_view = True
        elif user['role'] == 'recruiter' and interview['recruiter_id'] == current_user_id:
            can_view = True
        elif user['role'] == 'college':
            can_view = True
        
        if not can_view:
            return jsonify({
                'message': 'Access denied!',
                'success': False
            }), 403
        
        # Get application and job information
        applications_collection = db_utils.get_collection('applications')
        jobs_collection = db_utils.get_collection('jobs')
        
        application = applications_collection.find_one({'_id': interview['application_id']})
        job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
        
        # Get student and recruiter information
        student = users_collection.find_one(
            {'_id': interview['student_id']},
            {'password_hash': 0}
        )
        recruiter = users_collection.find_one(
            {'_id': interview['recruiter_id']},
            {'password_hash': 0}
        )
        
        interview_data = {
            'id': interview['_id'],
            'application_id': interview['application_id'],
            'job': {
                'id': job['_id'] if job else None,
                'title': job['title'] if job else 'Unknown',
                'company': job['company'] if job else 'Unknown'
            },
            'student': {
                'id': student['_id'] if student else None,
                'name': student['profile']['full_name'] if student else 'Unknown',
                'email': student['email'] if student else 'Unknown',
                'profile': student['profile'] if student else {}
            },
            'recruiter': {
                'id': recruiter['_id'] if recruiter else None,
                'name': recruiter['profile']['full_name'] if recruiter else 'Unknown',
                'email': recruiter['email'] if recruiter else 'Unknown',
                'company': recruiter['profile'].get('company_name', '') if recruiter else ''
            },
            'interview_type': interview['interview_type'],
            'scheduled_date': interview['scheduled_date'].isoformat() if interview.get('scheduled_date') else None,
            'duration_minutes': interview['duration_minutes'],
            'location': interview['location'],
            'instructions': interview['instructions'],
            'status': interview['status'],
            'feedback': interview.get('feedback', {}),
            'created_at': interview['created_at'].isoformat(),
            'updated_at': interview['updated_at'].isoformat()
        }
        
        return jsonify({
            'message': 'Interview details retrieved successfully!',
            'success': True,
            'interview': interview_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve interview details: {str(e)}',
            'success': False
        }), 500

@interview_bp.route('/<interview_id>/reschedule', methods=['PUT'])
@token_required
def reschedule_interview(current_user_id, interview_id):
    """Reschedule an interview"""
    try:
        data = request.get_json()
        
        if not data or not data.get('scheduled_date'):
            return jsonify({
                'message': 'New scheduled date is required!',
                'success': False
            }), 400
        
        interviews_collection = db_utils.get_collection('interviews')
        interview = interviews_collection.find_one({'_id': interview_id})
        
        if not interview:
            return jsonify({
                'message': 'Interview not found!',
                'success': False
            }), 404
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        # Check if user has permission to reschedule (recruiter or student)
        can_reschedule = False
        if user['role'] == 'student' and interview['student_id'] == current_user_id:
            can_reschedule = True
        elif user['role'] == 'recruiter' and interview['recruiter_id'] == current_user_id:
            can_reschedule = True
        
        if not can_reschedule:
            return jsonify({
                'message': 'Access denied. You can only reschedule your own interviews!',
                'success': False
            }), 403
        
        # Parse new scheduled date
        try:
            new_scheduled_date = datetime.datetime.fromisoformat(
                data['scheduled_date'].replace('Z', '+00:00')
            )
        except ValueError:
            return jsonify({
                'message': 'Invalid scheduled date format!',
                'success': False
            }), 400
        
        # Check if new scheduled date is in the future
        if new_scheduled_date <= datetime.datetime.utcnow():
            return jsonify({
                'message': 'New scheduled date must be in the future!',
                'success': False
            }), 400
        
        # Update interview
        update_data = {
            'scheduled_date': new_scheduled_date,
            'status': 'rescheduled',
            'updated_at': datetime.datetime.utcnow()
        }
        
        if data.get('location'):
            update_data['location'] = data['location']
        if data.get('instructions'):
            update_data['instructions'] = data['instructions']
        
        result = interviews_collection.update_one(
            {'_id': interview_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Create notifications for both parties
            notifications_collection = db_utils.get_collection('notifications')
            applications_collection = db_utils.get_collection('applications')
            jobs_collection = db_utils.get_collection('jobs')
            
            application = applications_collection.find_one({'_id': interview['application_id']})
            job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
            
            # Notification for the other party
            other_user_id = interview['student_id'] if user['role'] == 'recruiter' else interview['recruiter_id']
            notification_data = NotificationModel.create_notification_schema(
                user_id=other_user_id,
                title='Interview Rescheduled',
                message=f"Interview for {job['title'] if job else 'Job'} has been rescheduled to {new_scheduled_date.strftime('%B %d, %Y at %I:%M %p')}",
                type='info',
                related_id=interview_id,
                related_type='interview'
            )
            notifications_collection.insert_one(notification_data)
            
            return jsonify({
                'message': 'Interview rescheduled successfully!',
                'success': True,
                'interview': {
                    'id': interview_id,
                    'scheduled_date': new_scheduled_date.isoformat(),
                    'status': 'rescheduled',
                    'updated_at': update_data['updated_at'].isoformat()
                }
            }), 200
        else:
            return jsonify({
                'message': 'Failed to reschedule interview!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to reschedule interview: {str(e)}',
            'success': False
        }), 500

@interview_bp.route('/<interview_id>/feedback', methods=['PUT'])
@token_required
def add_interview_feedback(current_user_id, interview_id):
    """Add feedback to an interview (recruiters only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'message': 'Feedback data is required!',
                'success': False
            }), 400
        
        # Verify user is a recruiter
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can add interview feedback!',
                'success': False
            }), 403
        
        interviews_collection = db_utils.get_collection('interviews')
        interview = interviews_collection.find_one({'_id': interview_id})
        
        if not interview:
            return jsonify({
                'message': 'Interview not found!',
                'success': False
            }), 404
        
        # Check if user is the recruiter for this interview
        if interview['recruiter_id'] != current_user_id:
            return jsonify({
                'message': 'Access denied. You can only add feedback to your own interviews!',
                'success': False
            }), 403
        
        # Prepare feedback data
        feedback = {}
        if 'rating' in data:
            rating = data['rating']
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({
                    'message': 'Rating must be an integer between 1 and 5!',
                    'success': False
                }), 400
            feedback['rating'] = rating
        
        if 'comments' in data:
            feedback['comments'] = data['comments']
        
        if 'recommendation' in data:
            recommendation = data['recommendation']
            if recommendation not in ['hire', 'no_hire', 'maybe']:
                return jsonify({
                    'message': 'Recommendation must be hire, no_hire, or maybe!',
                    'success': False
                }), 400
            feedback['recommendation'] = recommendation
        
        # Update interview with feedback
        update_data = {
            'feedback': feedback,
            'status': 'completed',
            'updated_at': datetime.datetime.utcnow()
        }
        
        result = interviews_collection.update_one(
            {'_id': interview_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Update application status based on recommendation
            applications_collection = db_utils.get_collection('applications')
            if feedback.get('recommendation') == 'hire':
                new_status = 'accepted'
            elif feedback.get('recommendation') == 'no_hire':
                new_status = 'rejected'
            else:
                new_status = 'under_review'
            
            applications_collection.update_one(
                {'_id': interview['application_id']},
                {
                    '$set': {
                        'status': new_status,
                        'updated_at': datetime.datetime.utcnow()
                    }
                }
            )
            
            # Create notification for student
            notifications_collection = db_utils.get_collection('notifications')
            jobs_collection = db_utils.get_collection('jobs')
            application = applications_collection.find_one({'_id': interview['application_id']})
            job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
            
            notification_data = NotificationModel.create_notification_schema(
                user_id=interview['student_id'],
                title='Interview Completed',
                message=f"Your interview for {job['title'] if job else 'Job'} has been completed",
                type='info',
                related_id=interview_id,
                related_type='interview'
            )
            notifications_collection.insert_one(notification_data)
            
            return jsonify({
                'message': 'Interview feedback added successfully!',
                'success': True,
                'interview': {
                    'id': interview_id,
                    'feedback': feedback,
                    'status': 'completed',
                    'application_status': new_status,
                    'updated_at': update_data['updated_at'].isoformat()
                }
            }), 200
        else:
            return jsonify({
                'message': 'Failed to add interview feedback!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to add interview feedback: {str(e)}',
            'success': False
        }), 500

@interview_bp.route('/<interview_id>/cancel', methods=['PUT'])
@token_required
def cancel_interview(current_user_id, interview_id):
    """Cancel an interview"""
    try:
        data = request.get_json()
        
        interviews_collection = db_utils.get_collection('interviews')
        interview = interviews_collection.find_one({'_id': interview_id})
        
        if not interview:
            return jsonify({
                'message': 'Interview not found!',
                'success': False
            }), 404
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        # Check if user has permission to cancel (recruiter or student)
        can_cancel = False
        if user['role'] == 'student' and interview['student_id'] == current_user_id:
            can_cancel = True
        elif user['role'] == 'recruiter' and interview['recruiter_id'] == current_user_id:
            can_cancel = True
        
        if not can_cancel:
            return jsonify({
                'message': 'Access denied. You can only cancel your own interviews!',
                'success': False
            }), 403
        
        # Update interview status to cancelled
        result = interviews_collection.update_one(
            {'_id': interview_id},
            {
                '$set': {
                    'status': 'cancelled',
                    'cancellation_reason': data.get('reason', ''),
                    'cancelled_by': current_user_id,
                    'cancelled_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Update application status back to under_review
            applications_collection = db_utils.get_collection('applications')
            applications_collection.update_one(
                {'_id': interview['application_id']},
                {
                    '$set': {
                        'status': 'under_review',
                        'updated_at': datetime.datetime.utcnow()
                    }
                }
            )
            
            # Create notification for the other party
            notifications_collection = db_utils.get_collection('notifications')
            jobs_collection = db_utils.get_collection('jobs')
            application = applications_collection.find_one({'_id': interview['application_id']})
            job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
            
            other_user_id = interview['student_id'] if user['role'] == 'recruiter' else interview['recruiter_id']
            notification_data = NotificationModel.create_notification_schema(
                user_id=other_user_id,
                title='Interview Cancelled',
                message=f"Interview for {job['title'] if job else 'Job'} has been cancelled",
                type='warning',
                related_id=interview_id,
                related_type='interview'
            )
            notifications_collection.insert_one(notification_data)
            
            return jsonify({
                'message': 'Interview cancelled successfully!',
                'success': True,
                'interview': {
                    'id': interview_id,
                    'status': 'cancelled'
                }
            }), 200
        else:
            return jsonify({
                'message': 'Failed to cancel interview!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to cancel interview: {str(e)}',
            'success': False
        }), 500