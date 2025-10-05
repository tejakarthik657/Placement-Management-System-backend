from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import sys
import os

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import UserModel, ValidationUtils
from utils.database import db_utils
from config import Config

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    """Decorator to require JWT token for protected routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!', 'success': False}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
            
            # Get user from database to ensure they still exist
            users_collection = db_utils.get_collection('users')
            user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
            if not user:
                return jsonify({'message': 'User not found or inactive!', 'success': False}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!', 'success': False}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!', 'success': False}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (student, recruiter, or college admin)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password') or not data.get('role'):
            return jsonify({
                'message': 'Email, password, and role are required!',
                'success': False
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        role = data['role'].lower()
        
        # Validate email format
        if not ValidationUtils.validate_email(email):
            return jsonify({
                'message': 'Invalid email format!',
                'success': False
            }), 400
        
        # Validate role
        if not ValidationUtils.validate_role(role):
            return jsonify({
                'message': 'Invalid role! Must be student, recruiter, or college.',
                'success': False
            }), 400
        
        # Validate password strength
        if len(password) < 6:
            return jsonify({
                'message': 'Password must be at least 6 characters long!',
                'success': False
            }), 400
        
        # Check if user already exists
        users_collection = db_utils.get_collection('users')
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return jsonify({
                'message': 'User with this email already exists!',
                'success': False
            }), 409
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Create user document
        user_data = UserModel.create_user_schema(
            email=email,
            password_hash=password_hash,
            role=role,
            full_name=data.get('full_name', ''),
            phone=data.get('phone', ''),
            linkedin=data.get('linkedin', ''),
            github=data.get('github', ''),
            location=data.get('location', ''),
            department=data.get('department', '') if role == 'student' else '',
            graduation_year=data.get('graduation_year', 0) if role == 'student' else 0,
            gpa=data.get('gpa', 0.0) if role == 'student' else 0.0,
            company_name=data.get('company_name', '') if role == 'recruiter' else '',
            company_website=data.get('company_website', '') if role == 'recruiter' else '',
            industry=data.get('industry', '') if role == 'recruiter' else '',
            college_name=data.get('college_name', '') if role == 'college' else ''
        )
        
        # Insert user into database
        result = users_collection.insert_one(user_data)
        
        if result.inserted_id:
            return jsonify({
                'message': 'User registered successfully!',
                'success': True,
                'user_id': user_data['_id']
            }), 201
        else:
            return jsonify({
                'message': 'Failed to register user!',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Registration failed: {str(e)}',
            'success': False
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({
                'message': 'Email and password are required!',
                'success': False
            }), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user in database
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({
            'email': email,
            'is_active': True
        })
        
        if not user:
            return jsonify({
                'message': 'Invalid email or password!',
                'success': False
            }), 401
        
        # Check password
        if not check_password_hash(user['password_hash'], password):
            return jsonify({
                'message': 'Invalid email or password!',
                'success': False
            }), 401
        
        # Generate JWT token
        token_payload = {
            'user_id': user['_id'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_DELTA)
        }
        
        token = jwt.encode(token_payload, Config.SECRET_KEY, algorithm='HS256')
        
        # Update last login time
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.datetime.utcnow()}}
        )
        
        # Return success response
        return jsonify({
            'message': 'Login successful!',
            'success': True,
            'token': token,
            'user': {
                'id': user['_id'],
                'email': user['email'],
                'role': user['role'],
                'profile': user['profile']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Login failed: {str(e)}',
            'success': False
        }), 500

@auth_bp.route('/verify-token', methods=['GET'])
@token_required
def verify_token(current_user_id):
    """Verify if the current token is valid and return user info"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({
            '_id': current_user_id,
            'is_active': True
        })
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        return jsonify({
            'message': 'Token is valid!',
            'success': True,
            'user': {
                'id': user['_id'],
                'email': user['email'],
                'role': user['role'],
                'profile': user['profile']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Token verification failed: {str(e)}',
            'success': False
        }), 500

@auth_bp.route('/refresh-token', methods=['POST'])
@token_required
def refresh_token(current_user_id):
    """Refresh JWT token"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({
            '_id': current_user_id,
            'is_active': True
        })
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Generate new token
        token_payload = {
            'user_id': user['_id'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRATION_DELTA)
        }
        
        new_token = jwt.encode(token_payload, Config.SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'message': 'Token refreshed successfully!',
            'success': True,
            'token': new_token
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Token refresh failed: {str(e)}',
            'success': False
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user_id):
    """Logout user (mainly for logging purposes since JWT is stateless)"""
    try:
        users_collection = db_utils.get_collection('users')
        users_collection.update_one(
            {'_id': current_user_id},
            {'$set': {'last_logout': datetime.datetime.utcnow()}}
        )
        
        return jsonify({
            'message': 'Logged out successfully!',
            'success': True
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Logout failed: {str(e)}',
            'success': False
        }), 500