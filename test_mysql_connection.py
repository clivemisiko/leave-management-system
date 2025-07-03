import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB'),
        port=int(os.getenv('MYSQL_PORT')),
        connect_timeout=10
    )
    print("✅ Success! Connected to MySQL.")
    conn.close()
except Exception as e:
    print(f"❌ Failed: {e}")