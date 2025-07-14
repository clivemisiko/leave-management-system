import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

def get_mysql_connection():
    try:
        print("Connecting to:", os.getenv("MYSQL_HOST"), os.getenv("MYSQL_PORT"))  # ✅ debug
        return pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DB"),
            port=int(os.getenv("MYSQL_PORT")),
            ssl={"fake_flag_to_enable_tls": True},  # ✅ Required for Railway
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

    except Exception as e:
        print("❌ Database connection failed:", e)
        raise

