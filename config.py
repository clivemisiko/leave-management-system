# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
    
    # ⬇️ PostgreSQL settings for Neon
    POSTGRES_URI = os.getenv('POSTGRES_URI', 'postgresql://neondb_owner:...your_neon_url_here...')
    SQLALCHEMY_DATABASE_URI = os.getenv('POSTGRES_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True
