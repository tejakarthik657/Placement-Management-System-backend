from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Import configurations
from config import Config

# Initialize Flask app
app = Flask(__name__)

# Load configurations from Config class
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

# Enable CORS with explicit settings to allow the frontend origin and Authorization header
# Restrict CORS to /api/*, allow common HTTP methods and the Authorization header used for JWT
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
}, supports_credentials=True, expose_headers=["Authorization"])


# Ensure CORS headers are present on every response (helps if any OPTIONS/other responses miss headers)
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    if origin and origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
    return response

# Import database utilities
from utils.database import db_utils

# Initialize database and create indexes
try:
    db_utils.create_indexes()
    db_utils.seed_sample_data()
    print("Database indexes and sample data initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Use the token_required decorator from auth_routes
from routes.auth_routes import token_required


# Import routes
from routes.auth_routes import auth_bp
from routes.job_routes import job_bp
from routes.application_routes import application_bp
from routes.user_routes import user_bp
from routes.dashboard_routes import dashboard_bp
from routes.interview_routes import interview_bp
from routes.file_routes import file_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(job_bp, url_prefix='/api/jobs')
app.register_blueprint(application_bp, url_prefix='/api/applications')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(interview_bp, url_prefix='/api/interviews')
app.register_blueprint(file_bp, url_prefix='/api/files')

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'message': 'Placement Management System API is running!',
        'status': 'active',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)