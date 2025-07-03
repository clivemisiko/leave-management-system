# app/init_db.py

from flask import Flask
from backend.app.extensions import get_mysql_connection  # ✅ Correct import
import os

app = Flask(__name__)
app.config['ENV'] = 'development'

def initialize_database():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()

        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            sql_statements = f.read()

        for statement in sql_statements.split(';'):
            stmt = statement.strip()
            if stmt:
                cur.execute(stmt)

        conn.commit()
        print("✅ Database initialized successfully.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error initializing DB: {e}")

    finally:
        if 'cur' in locals():
            cur.close()

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
