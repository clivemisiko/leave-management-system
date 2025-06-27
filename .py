# setup_db.py
from backend.app import create_app
from backend.app.extensions import mysql

app = create_app()

def create_tables():
    with app.app_context():
        try:
            conn = mysql.connection
            cursor = conn.cursor()

            # Create `admin` table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL
                )
            ''')

            # Create `staff` table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staff (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pno VARCHAR(20) NOT NULL UNIQUE,
                    username VARCHAR(50) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(100)
                )
            ''')

            
            # Create `leave_applications` table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leave_applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    staff_id INT,
                    name VARCHAR(100),
                    pno VARCHAR(20),
                    designation VARCHAR(100),
                    leave_days INT,
                    start_date DATE,
                    end_date DATE,
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
                    FOREIGN KEY (staff_id) REFERENCES staff(id)
                )
            ''')

            # Insert default admin
            cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)",
                               ('admin', 'admin123'))  # 🔐 You can hash this later

            conn.commit()
            print("✅ Tables created and default admin inserted")

        except Exception as e:
            print(f"❌ Setup failed: {e}")

if __name__ == '__main__':
    create_tables()
