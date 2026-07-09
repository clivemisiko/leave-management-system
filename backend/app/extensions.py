from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os
from urllib.parse import urlparse

mail = Mail()
db = SQLAlchemy()

def _mask_database_url(database_url):
    if not database_url:
        return "Not set"
    result = urlparse(database_url)
    if not result.hostname:
        return "Invalid URL"
    return f"{result.scheme}://{result.username or '<user>'}:***@{result.hostname}:{result.port or 5432}{result.path}"

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
            sslmode='require',
            connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "3")),
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3,
        )
        return conn

    except Exception as e:
        database_url = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")
        print(f"Database connection failed: {e}")
        print(f"Database URL: {_mask_database_url(database_url)}")
        return None
