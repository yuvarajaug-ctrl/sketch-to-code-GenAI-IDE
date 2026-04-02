import mysql.connector
from config import Config

try:
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password=''
    )
    cursor = connection.cursor()
    cursor.execute("SHOW DATABASES LIKE 'sketch2code_db'")
    result = cursor.fetchone()
    if result:
        print("DATABASE_EXISTS")
    else:
        print("DATABASE_NOT_FOUND")
    connection.close()
except Exception as e:
    print(f"CONNECTION_FAILED: {e}")
