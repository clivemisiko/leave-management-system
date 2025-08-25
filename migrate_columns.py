# migrate_columns.py
from backend.app.extensions import get_postgres_connection()

def column_exists(cursor, table, column):
    cursor.execute(f"""
        SELECT COUNT(*) AS count FROM information_schema.COLUMNS 
        WHERE TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (table, column))
    return cursor.fetchone()['count'] > 0

def add_column_if_missing(cursor, table, column, definition):
    if not column_exists(cursor, table, column):
        print(f"➕ Adding missing column `{column}` to `{table}`...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    else:
        print(f"✅ Column `{column}` already exists in `{table}`.")

def run_column_migrations():
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

        # Columns to ensure in leave_applications
        leave_columns = {
    "approved_by": "VARCHAR(100)",
    "approved_at": "DATETIME",
    "rejected_by": "VARCHAR(100)",
    "rejected_at": "DATETIME",
    "leave_type": "VARCHAR(50)",
    "salary_continue": "BOOLEAN DEFAULT TRUE",
    "salary_option": "VARCHAR(50)",
    "salary_address": "TEXT"
}



        for col, definition in leave_columns.items():
            add_column_if_missing(cur, "leave_applications", col, definition)

        conn.commit()
        print("✅ All missing columns handled.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        if 'cur' in locals():
            cur.close()

if __name__ == "__main__":
    run_column_migrations()
