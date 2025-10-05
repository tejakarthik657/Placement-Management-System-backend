import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    MONGODB_URL = os.environ.get('MONGODB_URL') or "mongodb+srv://tejakarthik5505_db_user:Ci4kgoFiAGVewYwT@cluster0.ajuxzww.mongodb.net/"
    DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'placement_db'
    JWT_EXPIRATION_DELTA = 24  # hours
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}