# setup_db.py

from backend.app import create_app
from backend.app.extensions import get_mysql_connection
from werkzeug.security import generate_password_hash

app = create_app()

def create_tables():
    with app.app_context():
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            # ✅ Create `admin` table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL
                )
            """)

            # ✅ Create `staff` table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pno VARCHAR(20) NOT NULL UNIQUE,
                    username VARCHAR(50) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    leave_balance INT DEFAULT 30
                )
            """)

            # ✅ Create `leave_applications` table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leave_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    staff_id INT,
                    name VARCHAR(100),
                    pno VARCHAR(20),
                    designation VARCHAR(100),
                    leave_days INT,
                    start_date DATE,
                    end_date DATE,
                    leave_balance INT DEFAULT 30,
                    last_leave_start DATE,
                    last_leave_end DATE,
                    contact_address TEXT,
                    contact_tel VARCHAR(20),
                    salary_option VARCHAR(100),
                    salary_address TEXT,
                    delegate VARCHAR(100),
                    user_type VARCHAR(10),
                    status VARCHAR(20) DEFAULT 'Pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
                )
            """)

            # ✅ Insert default admin if not exists
            cur.execute("SELECT * FROM admin WHERE username = %s", ('admin',))
            if not cur.fetchone():
                hashed_pw = generate_password_hash('admin123')
                cur.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", ('admin', hashed_pw))

            conn.commit()
            print("✅ Tables created and default admin inserted successfully.")

        except Exception as e:
            conn.rollback()
            print(f"❌ Setup failed: {e}")

        finally:
            if 'cur' in locals():
                cur.close()

if __name__ == '__main__':
    create_tables()
