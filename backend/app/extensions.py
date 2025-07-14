# backend/app/extensions.py
import pymysql
import os
from dotenv import load_dotenv
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy


# ✅ Load environment variables
load_dotenv()

db = SQLAlchemy()

# ✅ Flask-Mail instance
mail = Mail()

# ✅ Function to get a MySQL connection (works with TiDB)
def get_mysql_connection():
    # ✅ Debug: show which host and port we’re trying to use
    print("Connecting to:", os.getenv("MYSQL_HOST"), os.getenv("MYSQL_PORT"))

    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT")),
        ssl={"fake_flag_to_enable_tls": True},  # ✅ Required by Railway
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
