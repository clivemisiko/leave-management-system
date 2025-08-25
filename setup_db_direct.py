# add_missing_columns.py
from backend.app import create_app
from backend.app.extensions import get_postgres_connection

app = create_app()

def add_missing_columns():
    with app.app_context():
        conn = None
        cur = None
        try:
            conn = get_postgres_connection()
            if not conn:
                print("❌ Failed to get database connection")
                return
                
            cur = conn.cursor()

            # Check and add designation column to staff table
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'staff'
                AND column_name = 'designation'
            """)
            
            exists = cur.fetchone()[0]
            
            if not exists:
                print("⚠️ Adding missing 'designation' column to staff table...")
                cur.execute("ALTER TABLE staff ADD COLUMN designation VARCHAR(100)")
                print("✅ 'designation' column added successfully.")
            else:
                print("✅ 'designation' column already exists.")

            conn.commit()
            print("🎉 Missing columns have been added!")

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

if __name__ == '__main__':
    add_missing_columns()