from dotenv import load_dotenv
load_dotenv()

from flask import redirect, url_for, session
from backend.app import create_app
from backend.app.extensions import mysql  # ✅ Add this line

app = create_app()

@app.route('/')
def index():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_dashboard'))
    elif session.get('staff_logged_in'):
        return redirect(url_for('staff.staff_dashboard'))
    else:
        return redirect(url_for('staff.staff_login'))

@app.route('/db-check')
def db_check():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        return f"✅ Connected to MySQL! Tables: {tables}"
    except Exception as e:
        return f"❌ DB Error: {e}"

if __name__ == '__main__':
    app.run(debug=True, port=5050)

    for rule in app.url_map.iter_rules():
        print(f"{rule} --> {rule.endpoint}")
