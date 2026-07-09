from dotenv import load_dotenv
load_dotenv()

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent / "backend"))

from backend.app import create_app
from backend.app.extensions import get_postgres_connection

app = create_app()

@app.route('/db-check')
def db_check():
    conn = None
    cur = None
    try:
        conn = get_postgres_connection()
        if not conn:
            return "DB Error: could not connect to PostgreSQL. Check POSTGRES_URI or DATABASE_URL.", 503

        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cur.fetchall()

        return f"Connected to PostgreSQL. Tables: {tables}"
    except Exception as e:
        return f"DB Error: {e}", 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    # Print available routes before starting the server
    for rule in app.url_map.iter_rules():
        print(f"{rule} --> {rule.endpoint}")

    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
