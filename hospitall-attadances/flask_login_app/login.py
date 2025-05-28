from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, cv2, os
from datetime import datetime
import face_recognition, numpy as np
from calendar import monthrange

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Ensure directories exist
os.makedirs('static/dataset', exist_ok=True)
os.makedirs('static/captures', exist_ok=True)

# Database initialization
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT, email TEXT,
                            userid TEXT UNIQUE, password TEXT)''')

    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS employees (
                        id TEXT PRIMARY KEY, name TEXT,
                        phone TEXT, face_image TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                        id TEXT, name TEXT, date TEXT,
                        session TEXT, status TEXT, time TEXT)''')
        conn.commit()

init_db()

# Routes for auth
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']

        with sqlite3.connect('users.db') as conn:
            user = conn.execute("SELECT * FROM users WHERE userid=?", (userid,)).fetchone()
            if user and check_password_hash(user[4], password):
                session['name'] = user[1]
                return redirect('/welcome')
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            with sqlite3.connect('users.db') as conn:
                conn.execute("""INSERT INTO users (name, email, userid, password)
                               VALUES (?, ?, ?, ?)""",
                             (request.form['name'], request.form['email'],
                              request.form['userid'], generate_password_hash(request.form['password'])))
                conn.commit()
                return redirect('/')
        except sqlite3.IntegrityError:
            return "User ID already exists!"
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
#back
@app.route('/back')
def back():
    return render_template('welcome.html')
    
# Welcome dashboard
@app.route('/welcome')
def welcome():
    if 'name' in session:
        return render_template('welcome.html', name=session['name'])
    return redirect('/')



# Employee Registration
@app.route('/newreg', methods=['GET', 'POST'])
def newreg():
    if request.method == 'POST':
        session['name'] = request.form['name']
        session['emp_id'] = request.form['emp_id']
        session['phone'] = request.form['phone']
        return redirect('/capture_face')
    return render_template('newreg.html')

@app.route('/capture_face')
def capture_face():
    emp_id = session['emp_id']
    name = session['name']

    cam = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    while True:
        ret, frame = cam.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = frame[y:y+h, x:x+w]
            path = f'static/dataset/{emp_id}.jpg'
            cv2.imwrite(path, face)
            session['face_image'] = path
            cam.release()
            cv2.destroyAllWindows()
            return redirect('/confirm')

        cv2.imshow('Capturing Face - Press Q to Cancel', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    return redirect('/newreg')

@app.route('/confirm', methods=['GET', 'POST'])
def confirm():
    if request.method == 'POST':
        with sqlite3.connect('db.sqlite3') as conn:
            conn.execute("INSERT INTO employees (id, name, phone, face_image) VALUES (?, ?, ?, ?)",
                         (session['emp_id'], session['name'], session['phone'], session['face_image']))
            conn.commit()
        return redirect('/welcome')
    return render_template('confirm.html', name=session['name'], emp_id=session['emp_id'],
                           phone=session['phone'], face_image=session['face_image'])

# Employee List & Delete
@app.route('/employee_list')
def employee_list():
    with sqlite3.connect('db.sqlite3') as conn:
        employees = conn.execute("SELECT * FROM employees").fetchall()
    return render_template('employee_list.html', employees=employees)

@app.route('/delete_employee/<emp_id>', methods=['POST'])
def delete_employee(emp_id):
    with sqlite3.connect('db.sqlite3') as conn:
        conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        conn.execute("DELETE FROM attendance WHERE id = ?", (emp_id,))
        conn.commit()

    try:
        os.remove(f'static/dataset/{emp_id}.jpg')
    except FileNotFoundError:
        pass

    return redirect('/employee_list')

# Attendance
@app.route('/attendance_mark')
def attendance_mark():

    today = datetime.now().strftime("%Y-%m-%d")
    today = datetime.now()
    current_date = today.day
    current_month = today.month
    current_year = today.year
    date = today.strftime("%d %B %Y")  # e.g., '27 May 2025'
    current_time = today.strftime("%I:%M %p") 

    with sqlite3.connect('db.sqlite3') as conn:
        records = conn.execute("SELECT * FROM attendance WHERE date = ?", (today,)).fetchall()
    return render_template('attendance_mark.html', records=records,current_date=current_date,
                           current_month=current_month,
                           current_year=current_year,date=date,current_time=current_time
                           )

@app.route('/mark_by_id', methods=['GET', 'POST'])
def mark_by_id():
    if request.method == 'POST':
        emp_id = request.form['emp_id']
        with sqlite3.connect('db.sqlite3') as conn:
            row = conn.execute("SELECT name FROM employees WHERE id = ?", (emp_id,)).fetchone()
            if row:
                name = row[0]
                now = datetime.now()
                date = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")

                # Determine session
                h, m = now.hour, now.minute
                session = None
                if (h == 8 and m >= 30) or (9 <= h < 12) or (h == 12 and m <= 1):
                    session = 'morning'
                elif (h == 16 and m >= 30) or (17 <= h < 20) or (h == 20 and m <= 30):
                    session = 'evening'

                if session:
                    # Prevent duplicate attendance
                    exists = conn.execute("SELECT 1 FROM attendance WHERE id = ? AND date = ? AND session = ?", (emp_id, date, session)).fetchone()
                    if not exists:
                        conn.execute("INSERT INTO attendance (id, name, date, session, status, time) VALUES (?, ?, ?, ?, 'P', ?)",
                                     (emp_id, name, date, session, time_str))
                        conn.commit()
        return redirect('/report')
    return render_template('mark_by_id.html')

@app.route('/mark_by_face', methods=['POST'])
def mark_by_face():
    import time
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)


    if not cam.isOpened():
        return "❌ Camera not accessible", 500

    time.sleep(1)  # Warm-up time

    frame = None
    for _ in range(10):  # Try to grab multiple frames
        ret, temp_frame = cam.read()
        if ret and temp_frame is not None:
            frame = temp_frame

    cam.release()

    if frame is None:
        return "❌ Failed to capture image (even after multiple tries)", 500

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    try:
        encodings = face_recognition.face_encodings(rgb_frame)
    except Exception as e:
        return f"⚠️ Face recognition failed: {str(e)}", 500

    if not encodings:
        return "⚠️ No face detected", 400

    input_encoding = encodings[0]
    known_encodings, known_ids, known_names = [], [], []

    with sqlite3.connect('db.sqlite3') as conn:
        for emp_id, name, path in conn.execute("SELECT id, name, face_image FROM employees"):
            if path and os.path.exists(path):
                img = face_recognition.load_image_file(path)
                encoding = face_recognition.face_encodings(img)
                if encoding:
                    known_encodings.append(encoding[0])
                    known_ids.append(emp_id)
                    known_names.append(name)

    matches = face_recognition.compare_faces(known_encodings, input_encoding, tolerance=0.5)
    if any(matches):
        index = matches.index(True)
        emp_id = known_ids[index]
        name = known_names[index]
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Determine session
        h, m = now.hour, now.minute
        session = None
        if (h == 8 and m >= 30) or (9 <= h < 12) or (h == 12 and m <= 1):
            session = 'morning'
        elif (h == 16 and m >= 30) or (17 <= h < 20) or (h == 20 and m <= 30):
            session = 'evening'

        if session:
            with sqlite3.connect('db.sqlite3') as conn:
                exists = conn.execute("SELECT 1 FROM attendance WHERE id = ? AND date = ? AND session = ?", (emp_id, date, session)).fetchone()
                if not exists:
                    conn.execute("INSERT INTO attendance (id, name, date, session, status, time) VALUES (?, ?, ?, ?, 'P', ?)",
                                 (emp_id, name, date, session, time_str))
                    conn.commit()
            return redirect('/report')

        return "⚠️ Attendance not recorded (invalid session time)", 400

    return "⚠️ Face not matched", 404

# Attendance Report
@app.route('/report')
def report():

    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    today = datetime.strptime(selected_date, '%Y-%m-%d')

    today = datetime.now()
    current_date = today.day
    current_month = today.month
    current_year = today.year
    date = today.strftime("%d %B %Y")  # e.g., '27 May 2025'
    current_time = today.strftime("%I:%M %p")  # Current time in 12-hour format

    today_str = today.strftime('%Y-%m-%d')
    now = datetime.now()
    
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        employees = c.execute("SELECT id, name FROM employees").fetchall()
        existing = c.execute("SELECT id, session FROM attendance WHERE date = ?", (selected_date,)).fetchall()
        existing = {(id_, sess) for id_, sess in existing}
        
        if selected_date == datetime.now().strftime('%Y-%m-%d'):
            for emp_id, name in employees:
                if now.hour > 11 or (now.hour == 11 and now.minute > 30):
                    if (emp_id, 'morning') not in existing:
                        c.execute("INSERT INTO attendance (id, name, date, session, status, time) VALUES (?, ?, ?, 'morning', 'A', ?)",
                              (emp_id, name, today_str, '11:31:00'))
            if now.hour >= 20 and (emp_id, 'evening') not in existing:
                c.execute("INSERT INTO attendance (id, name, date, session, status, time) VALUES (?, ?, ?, 'evening', 'A', ?)",
                          (emp_id, name, today_str, '20:01:00'))

        conn.commit()

        people = c.execute("SELECT id, name FROM attendance WHERE date = ? GROUP BY id, name", (today_str,)).fetchall()
        report_data = []
        for emp_id, name in people:
            row = {'name': name, 'id': emp_id, 'morning': '', 'morning_time': '', 'evening': '', 'evening_time': ''}
            for sess, status, time in c.execute("SELECT session, status, time FROM attendance WHERE id = ? AND date = ?", (emp_id, selected_date)):
                try:
                    time_obj = datetime.strptime(time, "%H:%M:%S")
                    time_12hr = time_obj.strftime("%I:%M %p")
                except:
                    time_12hr = time  # fallback if time is empty or malformed

                if sess == 'morning':
                    row['morning'] = status
                    row['morning_time'] = time_12hr
                elif sess == 'evening':
                    row['evening'] = status
                    row['evening_time'] = time_12hr
            report_data.append(row)

    return render_template('report.html', rows=report_data,
                           current_date=current_date,
                           current_month=current_month,
                           current_year=current_year,
                           date=date,
                           current_time=current_time,selected_date=selected_date)

@app.route('/daily_data')
def daily_data():
    date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        records = c.execute("SELECT * FROM attendance WHERE date = ?", (date,)).fetchall()
        morning = [r for r in records if 9 <= int(r[3][:2]) < 14]
        evening = [r for r in records if 17 <= int(r[3][:2]) <= 23]
    return render_template('daily_data.html', date=date, morning=morning, evening=evening,)

@app.route('/monthly_data')
def monthly_data():
    import calendar
    from collections import defaultdict
    from calendar import monthrange
    from datetime import datetime
    import sqlite3
    from flask import request, render_template

    today = datetime.now()
    current_date = today.day
    current_month = today.month
    current_year = today.year
    date = today.strftime("%d %B %Y")
    current_time = today.strftime("%I:%M %p")

    # Get requested or current month/year
    year = int(request.args.get('year', current_year))
    month = int(request.args.get('month', current_month))
    days_in_month = monthrange(year, month)[1]
    date_prefix = f"{year}-{month:02d}"

    now = datetime.now()

    # Define system start date
    system_start_date = datetime(2025, 5, 27)

    # Fetch employee and attendance data
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        employees = c.execute("SELECT id, name FROM employees").fetchall()
        rows = c.execute(
            "SELECT id, session, status, date FROM attendance WHERE date LIKE ?",
            (f"{date_prefix}%",)
        ).fetchall()

    # Step 1: Build initial attendance data
    attendance_data = defaultdict(lambda: defaultdict(lambda: {'morning': '', 'evening': ''}))
    for emp_id, session, status, date_str in rows:
        try:
            day = int(date_str.split('-')[2])
            if session in ['morning', 'evening']:
                attendance_data[emp_id][day][session] = status
        except:
            continue

    # Step 2: Fill 'A' only if date has passed or today's session time has passed
    for emp_id, _ in employees:
        for day in range(1, days_in_month + 1):
            entry_date = datetime(year, month, day)

            if entry_date < system_start_date or entry_date > today:
                continue  # Skip dates before system or in the future

            is_today = (entry_date.date() == today.date())

            for session in ['morning', 'evening']:
                if attendance_data[emp_id][day][session] == '':
                    if session == 'morning' and (not is_today or (now.hour > 11 or (now.hour == 11 and now.minute > 30))):
                        attendance_data[emp_id][day]['morning'] = 'A'
                    elif session == 'evening' and (not is_today or now.hour >= 20):
                        attendance_data[emp_id][day]['evening'] = 'A'

    # Step 3: Format total present/absent counts
    def format_day_half(value):
        days = value // 2
        half = value % 2
        if days == 0 and half == 1:
            return "1/2"
        elif half == 1:
            return f"{days} 1/2"
        else:
            return f"{days}"

    # Step 4: Prepare employee attendance summary
    employees_attendance = []
    # Count present and absent for each employee (case-insensitive)
    for emp_id, name in employees:
        present_count = 0
        absent_count = 0
        attendance_per_day = {}
        
        for day in range(1, days_in_month + 1):
            att = attendance_data[emp_id][day]
            morning = att['morning'].strip().upper()
            evening = att['evening'].strip().upper()
            
            attendance_per_day[str(day)] = {
                'morning': morning,
                'evening': evening
           }
            
            if morning == 'P':
                present_count += 1
            elif morning == 'A':
                absent_count += 1
    
            if evening == 'P':
                present_count += 1
            elif evening == 'A':
                absent_count += 1

        total_present = format_day_half(present_count)
        total_absent = format_day_half(absent_count)

        employees_attendance.append({
            'id': emp_id,
            'name': name,
            'attendance': attendance_per_day,
            'total_present': total_present,
            'total_absent': total_absent
        })
        print(f"EMPLOYEE: {emp_id} - {name}")
        print(f"Present: {present_count}, Absent: {absent_count}")
        print(f"Day wise: {attendance_per_day}")


    return render_template('monthly_data.html',
                           employees=employees_attendance,
                           days_in_month=days_in_month,
                           selected_month=month,
                           selected_year=year,
                           current_date=current_date,
                           current_month=current_month,
                           current_year=current_year,
                           date=date,
                           current_time=current_time)

@app.route('/userlist')
def view_users():
    with sqlite3.connect('users.db') as conn:
        users = conn.execute("SELECT id, name, email, userid, password FROM users").fetchall()
    return render_template('userlist.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)