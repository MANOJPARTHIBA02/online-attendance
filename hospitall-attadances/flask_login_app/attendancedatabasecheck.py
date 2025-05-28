import sqlite3

def inspect_table():
    conn = sqlite3.connect('db.sqlite3')  # use actual path
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(attendance);")  # or your table name
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()

inspect_table()
