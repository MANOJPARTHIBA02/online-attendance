import sqlite3

with sqlite3.connect('users.db') as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    for user in users:
        print(user)
