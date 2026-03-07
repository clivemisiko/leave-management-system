from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os
from urllib.parse import urlparse

mail = Mail()
db = SQLAlchemy()

def get_postgres_connection():
    """
    Returns a PostgreSQL connection using the Render database connection string.
    """
    try:
        # Use the POSTGRES_URI from Render (set in render.yaml)
        database_url = os.getenv("POSTGRES_URI")
        
        if not database_url:
            raise ValueError("POSTGRES_URI environment variable not set")
        
        # Parse the POSTGRES_URI
        result = urlparse(database_url)
        
        # Connect with SSL (Render PostgreSQL requires this)
        conn = psycopg2.connect(
            dbname=result.path.lstrip("/"),
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port or 5432,
            sslmode='require'  # Render requires SSL
        )
        return conn

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"   POSTGRES_URI: {os.getenv('POSTGRES_URI', 'Not set')}")
        return None