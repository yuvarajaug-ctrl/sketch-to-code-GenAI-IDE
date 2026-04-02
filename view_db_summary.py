import sqlite3
import os

DB_PATH = 'site.db'

def show_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("SKETCH2CODE DATABASE OVERVIEW")
    print("="*50)

    # Show Users
    print("\n[TABLE: users]")
    try:
        cursor.execute("SELECT id, email, role, created_at FROM users")
        rows = cursor.fetchall()
        print(f"{'ID':<5} | {'Email':<25} | {'Role':<10} | {'Created At'}")
        print("-" * 70)
        for row in rows:
            print(f"{row['id']:<5} | {row['email']:<25} | {row['role']:<10} | {row['created_at']}")
    except Exception as e:
        print(f"Error reading users: {e}")

    # Show Projects
    print("\n[TABLE: projects]")
    try:
        cursor.execute("SELECT id, user_id, title, sketch_image_path, created_at FROM projects")
        rows = cursor.fetchall()
        print(f"{'ID':<5} | {'UID':<5} | {'Title':<20} | {'Sketch'}")
        print("-" * 70)
        for row in rows:
            print(f"{row['id']:<5} | {row['user_id']:<5} | {row['title']:<20} | {row['sketch_image_path']}")
    except Exception as e:
        print(f"Error reading projects: {e}")

    print("\n" + "="*50)
    conn.close()

if __name__ == "__main__":
    show_db()
