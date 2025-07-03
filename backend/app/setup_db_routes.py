from flask import Blueprint
from backend.app.extensions import get_mysql_connection  # ✅ Correct import

setup_db_bp = Blueprint('setup_db', __name__)

@setup_db_bp.route('/setup-db')
def setup_database():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pno VARCHAR(20) NOT NULL,
                username VARCHAR(100) NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                staff_id INT,
                leave_days INT,
                start_date DATE,
                end_date DATE,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'Pending',
                FOREIGN KEY (staff_id) REFERENCES staff(id)
            )
        """)

        conn.commit()
        return "✅ Tables created successfully!"

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return f"❌ Error: {e}"

    finally:
        if 'cur' in locals():
            cur.close()
