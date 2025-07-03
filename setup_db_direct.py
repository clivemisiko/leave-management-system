import pymysql

try:
    connection = pymysql.connect(
        host='interchange.proxy.rlwy.net',
        user='root',
        password='mevtivlyusqfhxst',
        database='railway',
        port=24117,
        connect_timeout=10,
    )
    print("✅ Connected to MySQL")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("📋 Tables:", tables)

except Exception as e:
    print("❌ Error:", e)
