import mysql.connector

passwords = ['', 'root', 'admin', 'password', '123456']
for pwd in passwords:
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=pwd
        )
        print(f"SUCCESS: {pwd}")
        connection.close()
        break
    except Exception as e:
        print(f"FAILED: {pwd} {e}")
