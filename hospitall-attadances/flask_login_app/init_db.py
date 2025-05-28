import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Create the attendance table if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id TEXT,
    name TEXT,
    date TEXT,
    session TEXT,
    status TEXT,
    time TEXT
)
''')

conn.commit()
conn.close()

print("✅ Table 'attendance' created.")
