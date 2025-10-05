from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import gridfs
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    _instance = None
    _client = None
    _db = None
    _fs = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self.connect()
    
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self._client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=5000)
            self._client.admin.command('ismaster')
            self._db = self._client[Config.DATABASE_NAME]
            self._fs = gridfs.GridFS(self._db)
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise e
    
    def get_database(self):
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    def get_gridfs(self):
        """Get GridFS instance for file storage"""
        if self._fs is None:
            self.connect()
        return self._fs
    
    def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._fs = None
            logger.info("Database connection closed")

# Database utility functions
class DatabaseUtils:
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self.db = self.db_connection.get_database()
        self.fs = self.db_connection.get_gridfs()
    
    def get_collection(self, collection_name):
        """Get a specific collection"""
        return self.db[collection_name]
    
    def create_indexes(self):
        """Create necessary database indexes for better performance"""
        try:
            # User indexes
            users = self.get_collection('users')
            users.create_index('email', unique=True)
            users.create_index('role')
            users.create_index('is_active')
            
            # Job indexes
            jobs = self.get_collection('jobs')
            jobs.create_index('recruiter_id')
            jobs.create_index('status')
            jobs.create_index('created_at')
            jobs.create_index([('title', 'text'), ('company', 'text'), ('location', 'text')])
            
            # Application indexes
            applications = self.get_collection('applications')
            applications.create_index('job_id')
            applications.create_index('student_id')
            applications.create_index('status')
            applications.create_index('applied_at')
            
            # Interview indexes
            interviews = self.get_collection('interviews')
            interviews.create_index('application_id')
            interviews.create_index('recruiter_id')
            interviews.create_index('student_id')
            interviews.create_index('scheduled_date')
            interviews.create_index('status')
            
            # Company indexes
            companies = self.get_collection('companies')
            companies.create_index('name', unique=True)
            companies.create_index('industry')
            
            # Notification indexes
            notifications = self.get_collection('notifications')
            notifications.create_index('user_id')
            notifications.create_index('is_read')
            notifications.create_index('created_at')
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def seed_sample_data(self):
        """Seed database with sample data for development"""
        try:
            # Sample companies
            companies_data = [
                {
                    '_id': 'company_1',
                    'name': 'Tech Innovators Inc.',
                    'website': 'https://techinnovators.com',
                    'industry': 'Technology',
                    'size': 'medium',
                    'description': 'Leading technology solutions provider',
                    'logo_url': 'https://images.unsplash.com/photo-1640716203594-6628aa4952af?q=80&w=1332&auto=format&fit=crop&ixlib=rb-4.1.0',
                    'headquarters': 'San Francisco, CA',
                    'founded_year': 2015,
                    'active_jobs_count': 5,
                    'total_hires': 120,
                },
                {
                    '_id': 'company_2',
                    'name': 'Data Insights Corp.',
                    'website': 'https://datainsights.com',
                    'industry': 'Analytics',
                    'size': 'large',
                    'description': 'Data analytics and business intelligence',
                    'logo_url': 'https://i.pinimg.com/736x/7e/24/b2/7e24b283da9067255cc1a1e76462d01e.jpg',
                    'headquarters': 'New York, NY',
                    'founded_year': 2012,
                    'active_jobs_count': 3,
                    'total_hires': 85,
                }
            ]
            
            companies = self.get_collection('companies')
            for company in companies_data:
                companies.update_one(
                    {'_id': company['_id']},
                    {'$set': company},
                    upsert=True
                )
            
            logger.info("Sample data seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding sample data: {e}")

# Global database instance
db_utils = DatabaseUtils()