from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os
from urllib.parse import urlparse

mail = Mail()
db = SQLAlchemy()

def get_postgres_connection():
    """
    Returns a PostgreSQL connection using the correct Railway connection string.
    """
    try:
        # Use the connection string from Railway dashboard
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:BPfofFISBoCNEKDBjoHcDWvmVLXuotem@nozomi.proxy.rlwy.net:45865/railway")
        
        # Parse the DATABASE_URL
        result = urlparse(database_url)
        
        # Connect with SSL required (Railway needs this)
        conn = psycopg2.connect(
            dbname=result.path.lstrip("/"),
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port or 5432,
            sslmode='require'  # Railway requires SSL
        )
        return conn

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"   Attempted connection to: {os.getenv('POSTGRES_HOST', 'nozomi.proxy.rlwy.net')}:{os.getenv('POSTGRES_PORT', 45865)}")
        return None