from werkzeug.security import generate_password_hash
from flask import current_app
import MySQLdb.cursors

def update_password(pno, new_password):
    hashed_pw = generate_password_hash(new_password)
    cur = current_app.mysql.connection.cursor()
    try:
        cur.execute(
            "UPDATE staff SET password = %s WHERE pno = %s",
            (hashed_pw, pno)
        )
        current_app.mysql.connection.commit()
    except Exception as e:
        current_app.mysql.connection.rollback()
        raise e
    finally:
        cur.close()