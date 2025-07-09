from backend.app.extensions import get_mysql_connection

try:
    conn = get_mysql_connection()
    print("✅ Connected to Railway MySQL successfully!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
