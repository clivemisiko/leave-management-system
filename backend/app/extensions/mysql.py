import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

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
