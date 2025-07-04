from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent / "backend"))

from flask import redirect, url_for, session, render_template
from backend.app import create_app
from backend.app.extensions import get_mysql_connection  # ✅ Import this BEFORE you use it

app = create_app()

@app.route('/')
def index():
    session.clear()
    return render_template('landing.html')

@app.route('/db-check')
def db_check():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        cur.close()
        return f"✅ Connected to MySQL! Tables: {tables}"
    except Exception as e:
        return f"❌ DB Error: {e}"

if __name__ == '__main__':
    app.run(debug=True, port=5050)

    for rule in app.url_map.iter_rules():
        print(f"{rule} --> {rule.endpoint}")
