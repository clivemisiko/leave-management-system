from flask import Blueprint
from backend.app.extensions import get_postgres_connection # ✅ Correct import

setup_db_bp = Blueprint('setup_db', __name__)

@setup_db_bp.route('/setup-db')
def setup_database():
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id SERIAL PRIMARY KEY,
                pno VARCHAR(20) NOT NULL UNIQUE,
                username VARCHAR(50) NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE,
                designation VARCHAR(100),
                department VARCHAR(100),
                phone_number VARCHAR(20),
                is_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(255),
                reset_token VARCHAR(255),
                leave_balance INT DEFAULT 30,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS leave_applications (
                id SERIAL PRIMARY KEY,
                staff_id INT,
                name VARCHAR(100) NOT NULL,
                pno VARCHAR(20) NOT NULL,
                designation VARCHAR(100),
                leave_days INT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                contact_address TEXT,
                contact_tel VARCHAR(20),
                salary_continue BOOLEAN DEFAULT TRUE,
                salary_address TEXT,
                delegate VARCHAR(100),
                outside_country BOOLEAN DEFAULT FALSE,
                leave_balance INT,
                last_leave_start DATE,
                last_leave_end DATE,
                leave_type VARCHAR(50) DEFAULT 'annual',
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
