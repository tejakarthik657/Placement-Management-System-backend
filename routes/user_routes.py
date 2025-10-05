from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import UserModel, ValidationUtils
from utils.database import db_utils
from routes.auth_routes import token_required

user_bp = Blueprint('users', __name__)

@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user_id):
    """Get current user's profile information"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Remove sensitive information
        profile_data = {
            'id': user['_id'],
            'email': user['email'],
            'role': user['role'],
            'profile': user['profile'],
            'settings': user['settings'],
            'resume_file_id': user.get('resume_file_id'),
            'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
            'updated_at': user['updated_at'].isoformat() if user.get('updated_at') else None
        }
        
        return jsonify({
            'message': 'Profile retrieved successfully!',
            'success': True,
            'user': profile_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve profile: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user_id):
    """Update current user's profile information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'message': 'No data provided!',
                'success': False
            }), 400
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Prepare update data
        update_data = {}
        profile_updates = {}
        
        # Basic profile fields that all users can update
        basic_fields = ['full_name', 'phone', 'linkedin', 'github', 'location']
        for field in basic_fields:
            if field in data:
                profile_updates[f'profile.{field}'] = data[field]
        
        # Role-specific fields
        if user['role'] == 'student':
            student_fields = ['department', 'graduation_year', 'gpa']
            for field in student_fields:
                if field in data:
                    profile_updates[f'profile.{field}'] = data[field]
        
        elif user['role'] == 'recruiter':
            recruiter_fields = ['company_name', 'company_website', 'industry']
            for field in recruiter_fields:
                if field in data:
                    profile_updates[f'profile.{field}'] = data[field]
        
        elif user['role'] == 'college':
            college_fields = ['college_name']
            for field in college_fields:
                if field in data:
                    profile_updates[f'profile.{field}'] = data[field]
        
        # Add timestamp
        if profile_updates:
            profile_updates['updated_at'] = datetime.datetime.utcnow()
            
            # Update user in database
            result = users_collection.update_one(
                {'_id': current_user_id},
                {'$set': profile_updates}
            )
            
            if result.modified_count > 0:
                # Get updated user data
                updated_user = users_collection.find_one({'_id': current_user_id})
                profile_data = {
                    'id': updated_user['_id'],
                    'email': updated_user['email'],
                    'role': updated_user['role'],
                    'profile': updated_user['profile'],
                    'updated_at': updated_user['updated_at'].isoformat()
                }
                
                return jsonify({
                    'message': 'Profile updated successfully!',
                    'success': True,
                    'user': profile_data
                }), 200
            else:
                return jsonify({
                    'message': 'No changes were made to the profile!',
                    'success': True
                }), 200
        else:
            return jsonify({
                'message': 'No valid fields provided for update!',
                'success': False
            }), 400
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to update profile: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/settings', methods=['GET'])
@token_required
def get_settings(current_user_id):
    """Get current user's settings"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        return jsonify({
            'message': 'Settings retrieved successfully!',
            'success': True,
            'settings': user.get('settings', {})
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve settings: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/settings', methods=['PUT'])
@token_required
def update_settings(current_user_id):
    """Update current user's settings"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'message': 'No settings data provided!',
                'success': False
            }), 400
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Prepare settings update
        settings_updates = {}
        valid_settings = ['email_notifications', 'sms_notifications', 'profile_visibility']
        
        for setting in valid_settings:
            if setting in data:
                settings_updates[f'settings.{setting}'] = data[setting]
        
        if settings_updates:
            settings_updates['updated_at'] = datetime.datetime.utcnow()
            
            result = users_collection.update_one(
                {'_id': current_user_id},
                {'$set': settings_updates}
            )
            
            if result.modified_count > 0:
                # Get updated settings
                updated_user = users_collection.find_one({'_id': current_user_id})
                
                return jsonify({
                    'message': 'Settings updated successfully!',
                    'success': True,
                    'settings': updated_user.get('settings', {})
                }), 200
            else:
                return jsonify({
                    'message': 'No changes were made to settings!',
                    'success': True
                }), 200
        else:
            return jsonify({
                'message': 'No valid settings provided for update!',
                'success': False
            }), 400
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to update settings: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/change-password', methods=['PUT'])
@token_required
def change_password(current_user_id):
    """Change user's password"""
    try:
        data = request.get_json()
        
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({
                'message': 'Current password and new password are required!',
                'success': False
            }), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate new password strength
        if len(new_password) < 6:
            return jsonify({
                'message': 'New password must be at least 6 characters long!',
                'success': False
            }), 400
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Verify current password
        if not check_password_hash(user['password_hash'], current_password):
            return jsonify({
                'message': 'Current password is incorrect!',
                'success': False
            }), 401
        
        # Hash new password
        new_password_hash = generate_password_hash(new_password)
        
        # Update password in database
        result = users_collection.update_one(
            {'_id': current_user_id},
            {
                '$set': {
                    'password_hash': new_password_hash,
                    'updated_at': datetime.datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                'message': 'Password changed successfully!',
                'success': True
            }), 200
        else:
            return jsonify({
                'message': 'Failed to change password!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to change password: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/deactivate', methods=['PUT'])
@token_required
def deactivate_account(current_user_id):
    """Deactivate current user's account"""
    try:
        data = request.get_json()
        
        if not data or not data.get('password'):
            return jsonify({
                'message': 'Password confirmation is required!',
                'success': False
            }), 400
        
        password = data['password']
        
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Verify password
        if not check_password_hash(user['password_hash'], password):
            return jsonify({
                'message': 'Password is incorrect!',
                'success': False
            }), 401
        
        # Deactivate account
        result = users_collection.update_one(
            {'_id': current_user_id},
            {
                '$set': {
                    'is_active': False,
                    'deactivated_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                'message': 'Account deactivated successfully!',
                'success': True
            }), 200
        else:
            return jsonify({
                'message': 'Failed to deactivate account!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to deactivate account: {str(e)}',
            'success': False
        }), 500

@user_bp.route('/search', methods=['GET'])
@token_required  
def search_users(current_user_id):
    """Search for users (mainly for admin purposes)"""
    try:
        users_collection = db_utils.get_collection('users')
        current_user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        # Only allow college admins to search users
        if not current_user or current_user['role'] != 'college':
            return jsonify({
                'message': 'Access denied. Only college admins can search users!',
                'success': False
            }), 403
        
        # Get query parameters
        role = request.args.get('role')
        department = request.args.get('department')
        graduation_year = request.args.get('graduation_year')
        search_text = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = {'is_active': True}
        
        if role and ValidationUtils.validate_role(role):
            query['role'] = role
        
        if department:
            query['profile.department'] = {'$regex': department, '$options': 'i'}
            
        if graduation_year:
            try:
                query['profile.graduation_year'] = int(graduation_year)
            except ValueError:
                pass
        
        if search_text:
            query['$or'] = [
                {'profile.full_name': {'$regex': search_text, '$options': 'i'}},
                {'email': {'$regex': search_text, '$options': 'i'}}
            ]
        
        # Execute query with pagination
        skip = (page - 1) * limit
        cursor = users_collection.find(query, {
            'password_hash': 0  # Exclude password hash
        }).skip(skip).limit(limit)
        
        users = list(cursor)
        total_count = users_collection.count_documents(query)
        
        # Format response
        user_list = []
        for user in users:
            user_data = {
                'id': user['_id'],
                'email': user['email'],
                'role': user['role'],
                'profile': user['profile'],
                'created_at': user['created_at'].isoformat() if user.get('created_at') else None
            }
            user_list.append(user_data)
        
        return jsonify({
            'message': 'Users retrieved successfully!',
            'success': True,
            'users': user_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to search users: {str(e)}',
            'success': False
        }), 500