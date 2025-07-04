import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'gateway01.us-west-2.prod.aws.tidbcloud.com')
    MYSQL_USER = os.getenv('MYSQL_USER', '2T4hhMqwZwwhwJM.root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'na5fF8Gcvr8t5iL0')
    MYSQL_DB = os.getenv('MYSQL_DB', 'test')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 4000))
    MYSQL_SSL_DISABLED = False

# Add this DevelopmentConfig class
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True