from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent / "backend"))

from flask import redirect, url_for, session, render_template
from backend.app import create_app
from backend.app.extensions import get_postgres_connection

app = create_app()

@app.route('/')
def index():
    session.clear()
    return render_template('landing.html')

@app.route('/db-check')
def db_check():
    conn = None
    cur = None
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cur.fetchall()
        cur.close()

        return f"✅ Connected to MySQL! Tables: {tables}"
    except Exception as e:
        return f"❌ DB Error: {e}"
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    # Print available routes before starting the server
    for rule in app.url_map.iter_rules():
        print(f"{rule} --> {rule.endpoint}")

    app.run(debug=True, port=5000)
