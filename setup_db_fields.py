import pymysql
from dotenv import load_dotenv
import os

# Load .env environment variables
load_dotenv()

# Database connection config
db_config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB"),
    "cursorclass": pymysql.cursors.DictCursor
}

required_columns = {
    "leave_applications": {
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "leave_type": "VARCHAR(100)",
        "approved_at": "DATETIME NULL",
        "approved_by": "VARCHAR(100)",
        "rejected_at": "DATETIME NULL"
    },
    "staff": {
        "leave_balance": "INT DEFAULT 0"
    },
    "admins": {
        "username": "VARCHAR(100)",
        "password": "VARCHAR(255)"
    }
}

def add_missing_columns():
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            for table, columns in required_columns.items():
                cur.execute(f"SHOW COLUMNS FROM {table}")
                existing = [col["Field"] for col in cur.fetchall()]
                
                for column, definition in columns.items():
                    if column not in existing:
                        alter_query = f"ALTER TABLE {table} ADD COLUMN {column} {definition};"
                        print(f"➕ Adding missing column: {column} to {table}")
                        cur.execute(alter_query)
                    else:
                        print(f"✔️ Column {column} already exists in {table}")
            conn.commit()
            print("✅ Table update complete.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()
