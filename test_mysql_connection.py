import pymysql
from dotenv import load_dotenv
import os

# ✅ Load the .env file
load_dotenv()

# ✅ Fetch values from .env
host = os.getenv("MYSQL_HOST")
port = int(os.getenv("MYSQL_PORT", 3306))
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DB")

# ✅ Try connecting
try:
    connection = pymysql.connect(
    host=host,
    user=user,
    password=password,
    db=database,
    port=port,
    connect_timeout=10,
    autocommit=True
)

    print("✅ MySQL connection successful!")
    connection.close()

except pymysql.MySQLError as e:
    print(f"❌ MySQL connection failed: {e}")
