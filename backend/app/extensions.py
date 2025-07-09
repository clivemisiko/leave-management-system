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
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT")),
        ssl={"ssl": {}},  # Required by TiDB
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
