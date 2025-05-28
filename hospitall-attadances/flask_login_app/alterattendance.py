import sqlite3

with sqlite3.connect('db.sqlite3') as conn:
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN morning TEXT;")
        print("✅ Column 'morning' added.")
    except sqlite3.OperationalError:
        print("⚠️ Column 'morning' already exists.")
    
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN evening TEXT;")
        print("✅ Column 'evening' added.")
    except sqlite3.OperationalError:
        print("⚠️ Column 'evening' already exists.")

