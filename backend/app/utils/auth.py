from werkzeug.security import generate_password_hash
from backend.app.extensions import get_postgres_connection # ✅ You need this
# Do NOT use `MySQLdb` if you're using PyMySQL + TiDB

def update_password(pno, new_password):
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        hashed_pw = generate_password_hash(new_password)

        cur.execute(
            "UPDATE staff SET password = %s WHERE pno = %s",
            (hashed_pw, pno)
        )
        conn.commit()
        return True

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        raise e

    finally:
        if 'cur' in locals():
            cur.close()
