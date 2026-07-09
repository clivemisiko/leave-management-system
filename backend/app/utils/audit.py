from backend.app.extensions import get_postgres_connection
from datetime import datetime
from psycopg2.extras import RealDictCursor

def log_action(action, staff_id=None, admin_username=None):
    try:
        conn = get_postgres_connection()
        if not conn:
            print("[Audit Log Error] Database connection unavailable")
            return

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO activity_logs (staff_id, admin_username, action, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (
                staff_id,
                admin_username,
                action,
                datetime.now()
            ))
            conn.commit()
    except Exception as e:
        print(f"[Audit Log Error] {str(e)}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
