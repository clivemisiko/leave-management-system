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
        # Try POSTGRES_URI first (set in render.yaml), fall back to DATABASE_URL
        database_url = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("Neither POSTGRES_URI nor DATABASE_URL environment variable is set")
        
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