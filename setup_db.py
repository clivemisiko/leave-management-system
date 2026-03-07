# setup_db.py

from backend.app import create_app
from backend.app.extensions import get_postgres_connection
from werkzeug.security import generate_password_hash

app = create_app()


def add_column_if_missing(cur, table, column, definition):
    """Add a column to a table only if it does not already exist (PostgreSQL safe)."""
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
    """, (table, column))
    exists = cur.fetchone()[0]
    if not exists:
        print(f"  ➕ Adding column '{column}' to '{table}'...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    else:
        print(f"  ✅ Column '{column}' already exists in '{table}'.")


def create_tables():
    with app.app_context():
        conn = None
        cur = None
        try:
            conn = get_postgres_connection()
            if not conn:
                print("❌ Failed to get database connection")
                return

            cur = conn.cursor()

            # ── Create admin table ────────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            # ── Create staff table (base columns only in CREATE) ──────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id SERIAL PRIMARY KEY,
                    pno VARCHAR(20) NOT NULL UNIQUE,
                    username VARCHAR(50) NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            """)

            # ── Ensure all required staff columns exist ───────────────────────
            print("Checking staff table columns...")
            staff_columns = {
                "email":               "VARCHAR(100) UNIQUE",
                "designation":         "VARCHAR(100)",
                "department":          "VARCHAR(100)",
                "phone_number":        "VARCHAR(20)",
                "is_verified":         "BOOLEAN DEFAULT FALSE",
                "verification_token":  "VARCHAR(255)",
                "reset_token":         "VARCHAR(255)",
                "reset_token_expires": "TIMESTAMP",
                "leave_balance":       "INT DEFAULT 30",
                "profile_pic":         "VARCHAR(255)",
                "is_active":           "BOOLEAN DEFAULT TRUE",
                "created_at":          "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at":          "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            }
            for col, defn in staff_columns.items():
                add_column_if_missing(cur, "staff", col, defn)

            # ── Create leave_applications table (base columns only) ───────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leave_applications (
                    id SERIAL PRIMARY KEY,
                    staff_id INT,
                    name VARCHAR(100),
                    pno VARCHAR(20),
                    designation VARCHAR(100),
                    leave_days INT,
                    start_date DATE,
                    end_date DATE,
                    status VARCHAR(20) DEFAULT 'Pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── Ensure all required leave_applications columns exist ──────────
            print("Checking leave_applications table columns...")
            leave_columns = {
                "department":       "VARCHAR(100)",
                "leave_balance":    "INT DEFAULT 30",
                "last_leave_start": "DATE",
                "last_leave_end":   "DATE",
                "contact_address":  "TEXT",
                "contact_tel":      "VARCHAR(20)",
                "salary_option":    "VARCHAR(100)",
                "salary_continue":  "BOOLEAN DEFAULT TRUE",
                "salary_address":   "TEXT",
                "delegate":         "VARCHAR(100)",
                "user_type":        "VARCHAR(10)",
                "leave_type":       "VARCHAR(50)",
                "reason":           "TEXT",
                "rejected_by":      "VARCHAR(100)",
                "rejected_at":      "TIMESTAMP",
                "approved_by":      "VARCHAR(100)",
                "approved_at":      "TIMESTAMP",
                "supporting_doc":   "VARCHAR(255)",
            }
            for col, defn in leave_columns.items():
                add_column_if_missing(cur, "leave_applications", col, defn)

            # ── add FK constraint only if it doesn't already exist ────────────
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                  AND table_name = 'leave_applications'
                  AND constraint_name = 'leave_applications_staff_id_fkey'
            """)
            if cur.fetchone()[0] == 0:
                try:
                    cur.execute("""
                        ALTER TABLE leave_applications
                        ADD CONSTRAINT leave_applications_staff_id_fkey
                        FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
                    """)
                    print("  ➕ Added FK constraint on leave_applications.staff_id.")
                except Exception as fk_err:
                    print(f"  ⚠️  Could not add FK (may be ok): {fk_err}")
                    conn.rollback()
                    # Re-open the transaction
                    conn = get_postgres_connection()
                    cur = conn.cursor()

            # ── Create audit_log table ────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(50) NOT NULL,
                    record_id INT NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    changed_by VARCHAR(100),
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    old_values JSONB,
                    new_values JSONB
                )
            """)

            # ── Create email_templates table ──────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_templates (
                    id SERIAL PRIMARY KEY,
                    template_name VARCHAR(100) NOT NULL UNIQUE,
                    subject VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── Seed default admin ────────────────────────────────────────────
            cur.execute("SELECT id FROM admin WHERE username = %s", ('admin',))
            if not cur.fetchone():
                hashed_pw = generate_password_hash('admin123')
                cur.execute(
                    "INSERT INTO admin (username, password) VALUES (%s, %s)",
                    ('admin', hashed_pw)
                )
                print("✅ Default admin user created.")

            # ── Seed sample staff user ────────────────────────────────────────
            cur.execute("SELECT id FROM staff WHERE pno = %s", ('EMP001',))
            if not cur.fetchone():
                hashed_pw = generate_password_hash('staff123')
                cur.execute(
                    """INSERT INTO staff
                       (pno, username, password, email, designation, department, leave_balance, is_verified)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    ('EMP001', 'john_doe', hashed_pw, 'john@example.com',
                     'Developer', 'IT Department', 30, True)
                )
                print("✅ Sample staff user created.")

            # ── Seed default email templates ──────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM email_templates")
            if cur.fetchone()[0] == 0:
                templates = [
                    ('registration', 'Welcome to Leave Management System',
                     'Dear {username},\n\nWelcome to our Leave Management System. '
                     'Your account has been created successfully.\n\nYour PNO: {pno}\n\n'
                     'Please verify your email to activate your account.'),

                    ('verification', 'Verify Your Email Address',
                     'Dear {username},\n\nPlease click the link below to verify your email address:'
                     '\n\n{verification_link}\n\nThis link will expire in 24 hours.'),

                    ('leave_approval', 'Leave Application Approved',
                     'Dear {username},\n\nYour leave application from {start_date} to {end_date} '
                     'has been approved.\n\nStatus: Approved\nApproved by: {approved_by}'),

                    ('leave_rejection', 'Leave Application Rejected',
                     'Dear {username},\n\nYour leave application from {start_date} to {end_date} '
                     'has been rejected.\n\nReason: {reason}\nRejected by: {rejected_by}'),

                    ('password_reset', 'Password Reset Request',
                     'Dear {username},\n\nYou requested a password reset. Click the link below to '
                     'reset your password:\n\n{reset_link}\n\nThis link will expire in 1 hour.'),
                ]
                for template_name, subject, body in templates:
                    cur.execute(
                        "INSERT INTO email_templates (template_name, subject, body) VALUES (%s, %s, %s)",
                        (template_name, subject, body)
                    )
                print("✅ Default email templates created.")

            conn.commit()
            print("✅ All tables and columns verified/created successfully.")
            print("✅ Default admin credentials: admin / admin123")
            print("✅ Sample staff credentials: EMP001 / staff123")
            print("✅ Database setup completed successfully! 🎉")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


if __name__ == '__main__':
    try:
        create_tables()
    except Exception as e:
        print(f"⚠️  setup_db.py encountered an error (app will still start): {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(0)  # Exit 0 so gunicorn still launches
