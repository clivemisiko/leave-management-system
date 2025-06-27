import pymysql

try:
    connection = pymysql.connect(
        host='interchange.proxy.rlwy.net',
        user='root',
        password='SCCOJeyUAanzmZTHprXobCKidCuPSflS',
        database='railway',
        port=24117,
        connect_timeout=10,
        ssl={'fake_flag_to_enable_ssl': True}  # Enables SSL, even if dummy
    )
    print("✅ Connected to MySQL")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("📋 Tables:", tables)

except Exception as e:
    print("❌ Error:", e)
