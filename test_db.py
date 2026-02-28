import pymysql

try:
    print("try to conncet to MySQL...")
    conn = pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='root',  
        database='ai_tutor_db',
        charset='utf8mb4'
    )
    print("successfully connected to MySQL!")
    conn.close()
except Exception as e:
    print(f"❌ failed to connect to MySQL, error message:\n{e}")
