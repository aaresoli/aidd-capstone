import os
from datetime import timedelta

from dotenv import load_dotenv

# Automatically ingest local environment settings (e.g., Google OAuth secrets)
# so developers can keep credentials in a .env file ignored by git.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, '..', '.env')
load_dotenv(ENV_PATH)


class Config:
    """Application configuration"""
    
    # Secret key for session management and CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    BASE_DIR = BASE_DIR
    DATABASE_PATH = os.path.join(BASE_DIR, '..', 'campus_hub.db')

    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # WTForms CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    
    # Application settings
    RESOURCES_PER_PAGE = 12
    MESSAGES_PER_PAGE = 20

    # Registration restrictions
    ALLOWED_EMAIL_DOMAINS = {'iu.edu'}

    # Calendar integrations
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_OAUTH_REDIRECT_PATH = os.environ.get('GOOGLE_OAUTH_REDIRECT_PATH', '/calendar/google/callback')
    EXTERNAL_BASE_URL = os.environ.get('EXTERNAL_BASE_URL')
    GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    CALENDAR_DEFAULT_TIMEZONE = os.environ.get('CALENDAR_DEFAULT_TIMEZONE', 'America/New_York')
