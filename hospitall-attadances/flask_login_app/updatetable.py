import sqlite3

with sqlite3.connect('db.sqlite3') as conn:
    c = conn.cursor()
    # Add new columns if they don't exist
    try:
        c.execute("ALTER TABLE attendance ADD COLUMN session TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE attendance ADD COLUMN status TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE attendance ADD COLUMN time TEXT")
    except:
        pass
    conn.commit()

print("✅ Columns added to attendance table.")
