from flask import Blueprint, request, jsonify
import datetime
from collections import defaultdict
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db_utils
from routes.auth_routes import token_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/college-stats', methods=['GET'])
@token_required
def get_college_dashboard_stats(current_user_id):
    """Get statistics for college dashboard"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can view college statistics!',
                'success': False
            }), 403
        
        jobs_collection = db_utils.get_collection('jobs')
        applications_collection = db_utils.get_collection('applications')
        interviews_collection = db_utils.get_collection('interviews')
        
        # Basic statistics
        total_students = users_collection.count_documents({'role': 'student', 'is_active': True})
        total_recruiters = users_collection.count_documents({'role': 'recruiter', 'is_active': True})
        total_jobs = jobs_collection.count_documents({'status': 'active'})
        total_applications = applications_collection.count_documents({})
        
        # Placement statistics
        placed_students = applications_collection.count_documents({'status': 'accepted'})
        ongoing_interviews = interviews_collection.count_documents({'status': {'$in': ['scheduled', 'rescheduled']}})
        
        # Companies that have posted jobs
        active_companies = jobs_collection.distinct('company', {'status': 'active'})
        total_companies = len(active_companies)
        
        stats = {
            'total_students': total_students,
            'placed_students': placed_students,
            'total_companies': total_companies,
            'ongoing_drives': total_jobs,  # Assuming active jobs are ongoing drives
            'total_recruiters': total_recruiters,
            'total_applications': total_applications,
            'ongoing_interviews': ongoing_interviews,
            'placement_percentage': round((placed_students / total_students * 100) if total_students > 0 else 0, 1)
        }
        
        return jsonify({
            'message': 'College statistics retrieved successfully!',
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve college statistics: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/placements-by-department', methods=['GET'])
@token_required
def get_placements_by_department(current_user_id):
    """Get placement statistics by department"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can view placement statistics!',
                'success': False
            }), 403
        
        # Get all students with their departments
        students = list(users_collection.find(
            {'role': 'student', 'is_active': True},
            {'_id': 1, 'profile.department': 1}
        ))
        
        # Get all accepted applications
        applications_collection = db_utils.get_collection('applications')
        accepted_applications = list(applications_collection.find(
            {'status': 'accepted'},
            {'student_id': 1}
        ))
        
        placed_student_ids = {app['student_id'] for app in accepted_applications}
        
        # Group by department
        dept_stats = defaultdict(lambda: {'total': 0, 'placed': 0})
        
        for student in students:
            department = student['profile'].get('department', 'Unknown')
            dept_stats[department]['total'] += 1
            if student['_id'] in placed_student_ids:
                dept_stats[department]['placed'] += 1
        
        # Format response
        chart_data = []
        for dept, stats in dept_stats.items():
            placement_rate = round((stats['placed'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1)
            chart_data.append({
                'department': dept,
                'total_students': stats['total'],
                'placed_students': stats['placed'],
                'placement_rate': placement_rate
            })
        
        # Sort by placement rate descending
        chart_data.sort(key=lambda x: x['placement_rate'], reverse=True)
        
        return jsonify({
            'message': 'Placements by department retrieved successfully!',
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve placements by department: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/placements-by-company', methods=['GET'])
@token_required
def get_placements_by_company(current_user_id):
    """Get placement statistics by company"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can view placement statistics!',
                'success': False
            }), 403
        
        # Get all accepted applications with job details
        applications_collection = db_utils.get_collection('applications')
        jobs_collection = db_utils.get_collection('jobs')
        
        pipeline = [
            {'$match': {'status': 'accepted'}},
            {'$lookup': {
                'from': 'jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_details'
            }},
            {'$unwind': '$job_details'},
            {'$group': {
                '_id': '$job_details.company',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10}  # Top 10 companies
        ]
        
        result = list(applications_collection.aggregate(pipeline))
        
        chart_data = []
        for item in result:
            chart_data.append({
                'company': item['_id'],
                'placements': item['count']
            })
        
        return jsonify({
            'message': 'Placements by company retrieved successfully!',
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve placements by company: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/student-gpa-distribution', methods=['GET'])
@token_required
def get_student_gpa_distribution(current_user_id):
    """Get student GPA distribution for performance analysis"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can view student performance data!',
                'success': False
            }), 403
        
        # Get all students with GPA
        students = list(users_collection.find(
            {'role': 'student', 'is_active': True},
            {'_id': 1, 'profile.gpa': 1}
        ))
        
        # Get placement status for students
        applications_collection = db_utils.get_collection('applications')
        placed_student_ids = set(app['student_id'] for app in applications_collection.find(
            {'status': 'accepted'},
            {'student_id': 1}
        ))
        
        # Categorize by GPA ranges
        gpa_ranges = {
            '3.5-4.0': {'total': 0, 'placed': 0, 'range': [3.5, 4.0]},
            '3.0-3.5': {'total': 0, 'placed': 0, 'range': [3.0, 3.5]},
            '2.5-3.0': {'total': 0, 'placed': 0, 'range': [2.5, 3.0]},
            '2.0-2.5': {'total': 0, 'placed': 0, 'range': [2.0, 2.5]},
            'Below 2.0': {'total': 0, 'placed': 0, 'range': [0, 2.0]}
        }
        
        for student in students:
            gpa = student['profile'].get('gpa', 0)
            is_placed = student['_id'] in placed_student_ids
            
            # Determine GPA range
            range_key = 'Below 2.0'
            for key, data in gpa_ranges.items():
                if key != 'Below 2.0' and data['range'][0] <= gpa < data['range'][1]:
                    range_key = key
                    break
                elif key == '3.5-4.0' and gpa >= 3.5:
                    range_key = key
                    break
            
            gpa_ranges[range_key]['total'] += 1
            if is_placed:
                gpa_ranges[range_key]['placed'] += 1
        
        # Format response
        chart_data = []
        for range_name, data in gpa_ranges.items():
            placement_rate = round((data['placed'] / data['total'] * 100) if data['total'] > 0 else 0, 1)
            chart_data.append({
                'gpa_range': range_name,
                'total_students': data['total'],
                'placed_students': data['placed'],
                'placement_rate': placement_rate
            })
        
        return jsonify({
            'message': 'Student GPA distribution retrieved successfully!',
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve student GPA distribution: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/recruiters-by-industry', methods=['GET'])
@token_required
def get_recruiters_by_industry(current_user_id):
    """Get recruiter distribution by industry"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can view recruiter statistics!',
                'success': False
            }), 403
        
        # Get industry distribution
        pipeline = [
            {'$match': {'role': 'recruiter', 'is_active': True}},
            {'$group': {
                '_id': '$profile.industry',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        
        result = list(users_collection.aggregate(pipeline))
        
        chart_data = []
        for item in result:
            industry = item['_id'] if item['_id'] else 'Unknown'
            chart_data.append({
                'industry': industry,
                'recruiter_count': item['count']
            })
        
        return jsonify({
            'message': 'Recruiters by industry retrieved successfully!',
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve recruiters by industry: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/recruiter-stats', methods=['GET'])
@token_required
def get_recruiter_dashboard_stats(current_user_id):
    """Get statistics for recruiter dashboard"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'recruiter':
            return jsonify({
                'message': 'Access denied. Only recruiters can view recruiter statistics!',
                'success': False
            }), 403
        
        jobs_collection = db_utils.get_collection('jobs')
        applications_collection = db_utils.get_collection('applications')
        interviews_collection = db_utils.get_collection('interviews')
        
        # Get jobs posted by this recruiter
        recruiter_jobs = list(jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1}))
        job_ids = [job['_id'] for job in recruiter_jobs]
        
        # Basic statistics
        total_jobs = len(recruiter_jobs)
        active_jobs = jobs_collection.count_documents({'recruiter_id': current_user_id, 'status': 'active'})
        closed_jobs = jobs_collection.count_documents({'recruiter_id': current_user_id, 'status': 'closed'})
        
        # Application statistics
        total_applications = applications_collection.count_documents({'job_id': {'$in': job_ids}})
        new_applications = applications_collection.count_documents({
            'job_id': {'$in': job_ids},
            'status': 'submitted'
        })
        
        # Interview statistics
        interviews_scheduled = interviews_collection.count_documents({
            'recruiter_id': current_user_id,
            'status': {'$in': ['scheduled', 'rescheduled']}
        })
        interviews_completed = interviews_collection.count_documents({
            'recruiter_id': current_user_id,
            'status': 'completed'
        })
        
        # Candidates in different stages
        under_review = applications_collection.count_documents({
            'job_id': {'$in': job_ids},
            'status': 'under_review'
        })
        interview_scheduled = applications_collection.count_documents({
            'job_id': {'$in': job_ids},
            'status': 'interview_scheduled'
        })
        candidates_hired = applications_collection.count_documents({
            'job_id': {'$in': job_ids},
            'status': 'accepted'
        })
        
        stats = {
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'closed_jobs': closed_jobs,
            'total_applications': total_applications,
            'new_applications': new_applications,
            'interviews_scheduled': interviews_scheduled,
            'interviews_completed': interviews_completed,
            'candidates_under_review': under_review,
            'candidates_in_interview': interview_scheduled,
            'candidates_hired': candidates_hired
        }
        
        return jsonify({
            'message': 'Recruiter statistics retrieved successfully!',
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve recruiter statistics: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/application-trends', methods=['GET'])
@token_required
def get_application_trends(current_user_id):
    """Get application trends over time"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] not in ['college', 'recruiter']:
            return jsonify({
                'message': 'Access denied!',
                'success': False
            }), 403
        
        applications_collection = db_utils.get_collection('applications')
        
        # Build query based on user role
        query = {}
        if user['role'] == 'recruiter':
            # Get jobs posted by this recruiter
            jobs_collection = db_utils.get_collection('jobs')
            recruiter_jobs = list(jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1}))
            job_ids = [job['_id'] for job in recruiter_jobs]
            query['job_id'] = {'$in': job_ids}
        
        # Get applications from last 6 months
        six_months_ago = datetime.datetime.utcnow() - datetime.timedelta(days=180)
        query['applied_at'] = {'$gte': six_months_ago}
        
        # Aggregate applications by month
        pipeline = [
            {'$match': query},
            {'$group': {
                '_id': {
                    'year': {'$year': '$applied_at'},
                    'month': {'$month': '$applied_at'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        result = list(applications_collection.aggregate(pipeline))
        
        # Format response
        chart_data = []
        for item in result:
            month_name = datetime.date(item['_id']['year'], item['_id']['month'], 1).strftime('%B %Y')
            chart_data.append({
                'month': month_name,
                'applications': item['count']
            })
        
        return jsonify({
            'message': 'Application trends retrieved successfully!',
            'success': True,
            'data': chart_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve application trends: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/student-stats', methods=['GET'])
@token_required
def get_student_dashboard_stats(current_user_id):
    """Get statistics for student dashboard"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'student':
            return jsonify({
                'message': 'Access denied. Only students can view student statistics!',
                'success': False
            }), 403
        
        applications_collection = db_utils.get_collection('applications')
        interviews_collection = db_utils.get_collection('interviews')
        
        # Application statistics
        total_applications = applications_collection.count_documents({'student_id': current_user_id})
        pending_applications = applications_collection.count_documents({
            'student_id': current_user_id,
            'status': {'$in': ['submitted', 'under_review']}
        })
        interview_scheduled = applications_collection.count_documents({
            'student_id': current_user_id,
            'status': 'interview_scheduled'
        })
        accepted_applications = applications_collection.count_documents({
            'student_id': current_user_id,
            'status': 'accepted'
        })
        rejected_applications = applications_collection.count_documents({
            'student_id': current_user_id,
            'status': 'rejected'
        })
        
        # Interview statistics
        upcoming_interviews = interviews_collection.count_documents({
            'student_id': current_user_id,
            'status': {'$in': ['scheduled', 'rescheduled']},
            'scheduled_date': {'$gte': datetime.datetime.utcnow()}
        })
        completed_interviews = interviews_collection.count_documents({
            'student_id': current_user_id,
            'status': 'completed'
        })
        
        stats = {
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'interviews_scheduled': interview_scheduled,
            'accepted_applications': accepted_applications,
            'rejected_applications': rejected_applications,
            'upcoming_interviews': upcoming_interviews,
            'completed_interviews': completed_interviews,
            'success_rate': round((accepted_applications / total_applications * 100) if total_applications > 0 else 0, 1)
        }
        
        return jsonify({
            'message': 'Student statistics retrieved successfully!',
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve student statistics: {str(e)}',
            'success': False
        }), 500

@dashboard_bp.route('/recent-activities', methods=['GET'])
@token_required
def get_recent_activities(current_user_id):
    """Get recent activities for the dashboard"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        activities = []
        limit = int(request.args.get('limit', 10))
        
        if user['role'] == 'student':
            # Recent applications and interviews for students
            applications_collection = db_utils.get_collection('applications')
            interviews_collection = db_utils.get_collection('interviews')
            jobs_collection = db_utils.get_collection('jobs')
            
            # Recent applications
            recent_apps = list(applications_collection.find(
                {'student_id': current_user_id},
                sort=[('applied_at', -1)],
                limit=limit//2
            ))
            
            for app in recent_apps:
                job = jobs_collection.find_one({'_id': app['job_id']})
                activities.append({
                    'type': 'application',
                    'message': f"Applied for {job['title'] if job else 'Unknown Job'} at {job['company'] if job else 'Unknown Company'}",
                    'timestamp': app['applied_at'].isoformat(),
                    'status': app['status']
                })
            
            # Recent interviews
            recent_interviews = list(interviews_collection.find(
                {'student_id': current_user_id},
                sort=[('created_at', -1)],
                limit=limit//2
            ))
            
            for interview in recent_interviews:
                application = applications_collection.find_one({'_id': interview['application_id']})
                job = jobs_collection.find_one({'_id': application['job_id']}) if application else None
                activities.append({
                    'type': 'interview',
                    'message': f"Interview {interview['status']} for {job['title'] if job else 'Unknown Job'}",
                    'timestamp': interview['created_at'].isoformat(),
                    'status': interview['status']
                })
        
        elif user['role'] == 'recruiter':
            # Recent applications and jobs for recruiters
            jobs_collection = db_utils.get_collection('jobs')
            applications_collection = db_utils.get_collection('applications')
            
            # Recent jobs posted
            recent_jobs = list(jobs_collection.find(
                {'recruiter_id': current_user_id},
                sort=[('created_at', -1)],
                limit=limit//2
            ))
            
            for job in recent_jobs:
                activities.append({
                    'type': 'job',
                    'message': f"Posted job: {job['title']} at {job['company']}",
                    'timestamp': job['created_at'].isoformat(),
                    'status': job['status']
                })
            
            # Recent applications received
            job_ids = [job['_id'] for job in jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1})]
            recent_apps = list(applications_collection.find(
                {'job_id': {'$in': job_ids}},
                sort=[('applied_at', -1)],
                limit=limit//2
            ))
            
            for app in recent_apps:
                job = jobs_collection.find_one({'_id': app['job_id']})
                activities.append({
                    'type': 'application',
                    'message': f"New application received for {job['title'] if job else 'Unknown Job'}",
                    'timestamp': app['applied_at'].isoformat(),
                    'status': app['status']
                })
        
        elif user['role'] == 'college':
            # Recent system-wide activities for college admins
            jobs_collection = db_utils.get_collection('jobs')
            applications_collection = db_utils.get_collection('applications')
            
            # Recent jobs posted
            recent_jobs = list(jobs_collection.find(
                {},
                sort=[('created_at', -1)],
                limit=limit//2
            ))
            
            for job in recent_jobs:
                activities.append({
                    'type': 'job',
                    'message': f"New job posted: {job['title']} at {job['company']}",
                    'timestamp': job['created_at'].isoformat(),
                    'status': job['status']
                })
            
            # Recent applications
            recent_apps = list(applications_collection.find(
                {},
                sort=[('applied_at', -1)],
                limit=limit//2
            ))
            
            for app in recent_apps:
                job = jobs_collection.find_one({'_id': app['job_id']})
                activities.append({
                    'type': 'application',
                    'message': f"New application for {job['title'] if job else 'Unknown Job'}",
                    'timestamp': app['applied_at'].isoformat(),
                    'status': app['status']
                })
        
        # Sort activities by timestamp (most recent first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        activities = activities[:limit]
        
        return jsonify({
            'message': 'Recent activities retrieved successfully!',
            'success': True,
            'activities': activities
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve recent activities: {str(e)}',
            'success': False
        }), 500