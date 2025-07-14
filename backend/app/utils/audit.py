from backend.app.extensions import get_mysql_connection
from datetime import datetime
import pymysql

def log_action(action, staff_id=None, admin_username=None):
    try:
        conn = get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
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
