from flask import Blueprint, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import datetime
import sys
import os
import io
import gridfs
from bson import ObjectId

# Add the parent directory to the path so we can import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db_utils
from routes.auth_routes import token_required
from config import Config

file_bp = Blueprint('files', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in Config.ALLOWED_EXTENSIONS

@file_bp.route('/upload/resume', methods=['POST'])
@token_required
def upload_resume(current_user_id):
    """Upload resume file (students only)"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user or user['role'] != 'student':
            return jsonify({
                'message': 'Access denied. Only students can upload resumes!',
                'success': False
            }), 403
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({
                'message': 'No file provided!',
                'success': False
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'message': 'No file selected!',
                'success': False
            }), 400
        
        # Check file type
        if not allowed_file(file.filename):
            return jsonify({
                'message': 'Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed!',
                'success': False
            }), 400
        
        # Check file size (already handled by Flask's MAX_CONTENT_LENGTH)
        filename = secure_filename(file.filename)
        
        # Create unique filename
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user_id}_{timestamp}_{filename}"
        
        # Store file in GridFS
        fs = db_utils.fs
        
        try:
            # Store file with metadata
            file_id = fs.put(
                file.stream,
                filename=unique_filename,
                original_filename=filename,
                uploaded_by=current_user_id,
                upload_date=datetime.datetime.utcnow(),
                content_type=file.content_type,
                file_type='resume'
            )
            
            # Update user's resume file reference
            users_collection.update_one(
                {'_id': current_user_id},
                {
                    '$set': {
                        'resume_file_id': str(file_id),
                        'updated_at': datetime.datetime.utcnow()
                    }
                }
            )
            
            return jsonify({
                'message': 'Resume uploaded successfully!',
                'success': True,
                'file_id': str(file_id),
                'filename': filename,
                'file_size': file.content_length or 0
            }), 201
            
        except Exception as e:
            return jsonify({
                'message': f'Failed to store file: {str(e)}',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to upload resume: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/upload/document', methods=['POST'])
@token_required
def upload_document(current_user_id):
    """Upload general document (any user)"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({
                'message': 'No file provided!',
                'success': False
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'message': 'No file selected!',
                'success': False
            }), 400
        
        # Check file type
        if not allowed_file(file.filename):
            return jsonify({
                'message': 'Invalid file type. Only PDF, DOC, DOCX, and TXT files are allowed!',
                'success': False
            }), 400
        
        filename = secure_filename(file.filename)
        document_type = request.form.get('document_type', 'general')
        description = request.form.get('description', '')
        
        # Create unique filename
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user_id}_{timestamp}_{filename}"
        
        # Store file in GridFS
        fs = db_utils.fs
        
        try:
            # Store file with metadata
            file_id = fs.put(
                file.stream,
                filename=unique_filename,
                original_filename=filename,
                uploaded_by=current_user_id,
                upload_date=datetime.datetime.utcnow(),
                content_type=file.content_type,
                file_type='document',
                document_type=document_type,
                description=description
            )
            
            return jsonify({
                'message': 'Document uploaded successfully!',
                'success': True,
                'file_id': str(file_id),
                'filename': filename,
                'document_type': document_type,
                'file_size': file.content_length or 0
            }), 201
            
        except Exception as e:
            return jsonify({
                'message': f'Failed to store file: {str(e)}',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to upload document: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/download/<file_id>', methods=['GET'])
@token_required
def download_file(current_user_id, file_id):
    """Download a file by ID"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        fs = db_utils.fs
        
        try:
            # Get file from GridFS
            grid_out = fs.get(ObjectId(file_id))
            
            # Check permissions
            can_access = False
            
            # User can access their own files
            if grid_out.uploaded_by == current_user_id:
                can_access = True
            # Recruiters can access resumes of applicants
            elif user['role'] == 'recruiter':
                # A recruiter can access a resume if an application with that resume was submitted to one of their jobs.
                applications_collection = db_utils.get_collection('applications')
                jobs_collection = db_utils.get_collection('jobs')
                recruiter_job_ids = [job['_id'] for job in jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1})]
                # The resume_file_id in the application is stored as a string, so we must check against a string.
                if applications_collection.find_one({
                    'resume_file_id': file_id,
                    'job_id': {'$in': recruiter_job_ids}
                }):
                    can_access = True
            # College admins can access all files
            elif user['role'] == 'college':
                can_access = True
            
            if not can_access:
                return jsonify({
                    'message': 'Access denied!',
                    'success': False
                }), 403
            
            # Create response with file content
            response = Response(
                grid_out.read(),
                mimetype=grid_out.content_type or 'application/octet-stream',
                direct_passthrough=False
            )
            
            # Set headers for file download
            response.headers['Content-Disposition'] = f'attachment; filename="{grid_out.original_filename}"'
            response.headers['Content-Length'] = grid_out.length
            
            return response
            
        except gridfs.NoFile:
            return jsonify({
                'message': 'File not found!',
                'success': False
            }), 404
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to download file: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/view/<file_id>', methods=['GET'])
@token_required
def view_file(current_user_id, file_id):
    """View a file in browser (inline display)"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        fs = db_utils.fs
        
        try:
            # Get file from GridFS
            grid_out = fs.get(ObjectId(file_id))
            
            # Check permissions (same logic as download)
            can_access = False
            
            if grid_out.uploaded_by == current_user_id:
                can_access = True
            elif user['role'] == 'recruiter':
                # A recruiter can access a resume if an application with that resume was submitted to one of their jobs.
                applications_collection = db_utils.get_collection('applications')
                jobs_collection = db_utils.get_collection('jobs')
                recruiter_job_ids = [job['_id'] for job in jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1})]
                # The resume_file_id in the application is stored as a string, so we must check against a string.
                if applications_collection.find_one({
                    'resume_file_id': file_id,
                    'job_id': {'$in': recruiter_job_ids}
                }):
                    can_access = True
            elif user['role'] == 'college':
                can_access = True
            
            if not can_access:
                return jsonify({
                    'message': 'Access denied!',
                    'success': False
                }), 403
            
            # Create response for inline viewing
            response = Response(
                grid_out.read(),
                mimetype=grid_out.content_type or 'application/octet-stream',
                direct_passthrough=False
            )
            
            # Set headers for inline display
            response.headers['Content-Disposition'] = f'inline; filename="{grid_out.original_filename}"'
            response.headers['Content-Length'] = grid_out.length
            
            return response
            
        except gridfs.NoFile:
            return jsonify({
                'message': 'File not found!',
                'success': False
            }), 404
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to view file: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/my-files', methods=['GET'])
@token_required
def get_my_files(current_user_id):
    """Get list of files uploaded by current user"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        fs = db_utils.fs
        
        # Get all files uploaded by user
        files_cursor = fs.find({'uploaded_by': current_user_id}).sort('upload_date', -1)
        
        files_list = []
        for grid_file in files_cursor:
            file_info = {
                'file_id': str(grid_file._id),
                'filename': grid_file.original_filename,
                'file_type': grid_file.file_type,
                'document_type': getattr(grid_file, 'document_type', ''),
                'description': getattr(grid_file, 'description', ''),
                'upload_date': grid_file.upload_date.isoformat(),
                'file_size': grid_file.length,
                'content_type': grid_file.content_type
            }
            files_list.append(file_info)
        
        return jsonify({
            'message': 'Files retrieved successfully!',
            'success': True,
            'files': files_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'message': f'Failed to retrieve files: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/delete/<file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user_id, file_id):
    """Delete a file (only file owner can delete)"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        fs = db_utils.fs
        
        try:
            # Get file from GridFS
            grid_out = fs.get(ObjectId(file_id))
            
            # Check if user owns the file
            if grid_out.uploaded_by != current_user_id:
                return jsonify({
                    'message': 'Access denied. You can only delete your own files!',
                    'success': False
                }), 403
            
            # Delete file from GridFS
            fs.delete(ObjectId(file_id))
            
            # If this was a resume file, remove reference from user profile
            if grid_out.file_type == 'resume':
                users_collection.update_one(
                    {'_id': current_user_id, 'resume_file_id': file_id},
                    {
                        '$unset': {'resume_file_id': ''},
                        '$set': {'updated_at': datetime.datetime.utcnow()}
                    }
                )
            
            return jsonify({
                'message': 'File deleted successfully!',
                'success': True
            }), 200
            
        except gridfs.NoFile:
            return jsonify({
                'message': 'File not found!',
                'success': False
            }), 404
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to delete file: {str(e)}',
            'success': False
        }), 500

@file_bp.route('/info/<file_id>', methods=['GET'])
@token_required
def get_file_info(current_user_id, file_id):
    """Get file information without downloading"""
    try:
        users_collection = db_utils.get_collection('users')
        user = users_collection.find_one({'_id': current_user_id, 'is_active': True})
        
        if not user:
            return jsonify({
                'message': 'User not found!',
                'success': False
            }), 404
        
        fs = db_utils.fs
        
        try:
            # Get file from GridFS
            grid_out = fs.get(ObjectId(file_id))
            
            # Check permissions (basic check - user owns file or is college admin)
            can_access = False
            if grid_out.uploaded_by == current_user_id or user['role'] == 'college':
                can_access = True
            elif user['role'] == 'recruiter':
                # A recruiter can access a resume if an application with that resume was submitted to one of their jobs.
                applications_collection = db_utils.get_collection('applications')
                jobs_collection = db_utils.get_collection('jobs')
                recruiter_job_ids = [job['_id'] for job in jobs_collection.find({'recruiter_id': current_user_id}, {'_id': 1})]
                # The resume_file_id in the application is stored as a string, so we must check against a string.
                if applications_collection.find_one({
                    'resume_file_id': file_id,
                    'job_id': {'$in': recruiter_job_ids}
                }):
                    can_access = True
            
            if not can_access:
                return jsonify({
                    'message': 'Access denied!',
                    'success': False
                }), 403
            
            # Get uploader information
            uploader = users_collection.find_one(
                {'_id': grid_out.uploaded_by},
                {'profile.full_name': 1, 'email': 1}
            )
            
            file_info = {
                'file_id': str(grid_out._id),
                'filename': grid_out.original_filename,
                'file_type': grid_out.file_type,
                'document_type': getattr(grid_out, 'document_type', ''),
                'description': getattr(grid_out, 'description', ''),
                'upload_date': grid_out.upload_date.isoformat(),
                'file_size': grid_out.length,
                'content_type': grid_out.content_type,
                'uploader': {
                    'name': uploader['profile']['full_name'] if uploader else 'Unknown',
                    'email': uploader['email'] if uploader else 'Unknown'
                } if uploader else None
            }
            
            return jsonify({
                'message': 'File information retrieved successfully!',
                'success': True,
                'file_info': file_info
            }), 200
            
        except gridfs.NoFile:
            return jsonify({
                'message': 'File not found!',
                'success': False
            }), 404
            
    except Exception as e:
        return jsonify({
            'message': f'Failed to get file information: {str(e)}',
            'success': False
        }), 500