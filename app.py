from flask import Flask, render_template, request, redirect, session
import psycopg2

app = Flask(__name__)
app.secret_key = "secret123"

# DATABASE CONNECTION
conn = psycopg2.connect(
    host="localhost",
    database="quiz_system",
    user="postgres",
    password="1234",
    port="5432"
)
cur = conn.cursor()

# ---------------- SAFE EXECUTE ----------------
def safe_execute(query, params=None):
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
    except Exception as e:
        print("ERROR:", e)
        conn.rollback()

# ---------------- HOME ----------------
@app.route('/')
def home():
    cur.execute("SELECT * FROM student WHERE admin_username IS NOT NULL")
    students = cur.fetchall()
    return render_template('home.html', students=students)
    
    
#-----------Timer-------------------   
@app.route('/set_time', methods=['POST'])
def set_time():
    if 'admin' not in session:
        return redirect('/admin_login')

    quiz_time = int(request.form['time'])  # seconds

    safe_execute("""
        DELETE FROM admin_settings WHERE admin_username=%s
    """, (session['admin'],))

    safe_execute("""
        INSERT INTO admin_settings (admin_username, quiz_time)
        VALUES (%s, %s)
    """, (session['admin'], quiz_time))

    return redirect('/admin')
#---------------- ADD STUDENT ----------------

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'admin' not in session:
        return redirect('/admin_login')

    names = request.form.getlist('name[]')
    seatnos = request.form.getlist('seatno[]')

    for name, seatno in zip(names, seatnos):
        safe_execute("""
            INSERT INTO student (name, aadhar, admin_username)
            VALUES (%s, %s, %s)
        """, (name, seatno, session['admin']))

    return redirect('/assign_student')
# ---------------- DELETE STUDENT ----------------
@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    safe_execute("DELETE FROM student WHERE id=%s", (id,))
    return redirect('/assign_student')

# ---------------- EDIT STUDENT ----------------
@app.route('/edit_student/<int:id>')
def edit_student(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    cur.execute("SELECT * FROM student WHERE id=%s", (id,))
    student = cur.fetchone()

    return render_template('edit_student.html', student=student)

# ---------------- UPDATE STUDENT ----------------
@app.route('/update_student/<int:id>', methods=['POST'])
def update_student(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    name = request.form['name']
    seatno= request.form['seatno']

    safe_execute("""
        UPDATE student
        SET name=%s, aadhar=%s
        WHERE id=%s
    """, (name, seatno, id))

    return redirect('/assign_student')

# ---------------- ADMIN REGISTER ----------------
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            return "Passwords do not match"

        try:
            safe_execute(
                "INSERT INTO admin (username, password) VALUES (%s, %s)",
                (username, password)
            )
            return redirect('/admin_login')
        except:
            return "Username already exists"

    return render_template('admin_register.html')

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cur.fetchone()

        if user:
            session['admin'] = username
            return redirect('/admin')
        else:
            return "Invalid Credentials"

    return render_template('admin_login.html')

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')

    # get questions
    cur.execute(
        "SELECT * FROM questions WHERE admin_username=%s",
        (session['admin'],)
    )
    questions = cur.fetchall()

    # get students
    cur.execute(
        "SELECT * FROM student WHERE admin_username=%s",
        (session['admin'],)
    )
    students = cur.fetchall()

    # ✅ GET LATEST TIMER FROM DB (FIXED INDENTATION)
    cur.execute("""
        SELECT quiz_time
        FROM admin_settings
        WHERE admin_username=%s
    """, (session['admin'],))

    result = cur.fetchone()
    quiz_time = result[0] if result else 60

    return render_template(
        'admin.html',
        questions=questions,
        students=students,
        quiz_time=quiz_time
    )
    
# ---------------- ADD QUESTION ----------------
@app.route('/add', methods=['POST'])
def add():
    if 'admin' not in session:
        return redirect('/admin_login')

  
    safe_execute("""
        INSERT INTO questions (question, option1, option2, option3, option4, answer, admin_username)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        request.form['question'],
        request.form['option1'],
        request.form['option2'],
        request.form['option3'],
        request.form['option4'],
        request.form['answer'],
        session['admin']
    ))

    return redirect('/admin')

# ---------------- DELETE QUESTION ----------------
@app.route('/delete/<int:id>')
def delete(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    safe_execute("DELETE FROM questions WHERE id=%s", (id,))
    return redirect('/admin')

# ---------------- EDIT QUESTION ----------------
@app.route('/edit/<int:id>')
def edit(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    cur.execute("SELECT * FROM questions WHERE id=%s", (id,))
    q = cur.fetchone()

    return render_template('edit.html', q=q)

# ---------------- UPDATE QUESTION ----------------
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    safe_execute("""
        UPDATE questions
        SET question=%s, option1=%s, option2=%s,
            option3=%s, option4=%s, answer=%s
        WHERE id=%s
    """, (
        request.form['question'],
        request.form['option1'],
        request.form['option2'],
        request.form['option3'],
        request.form['option4'],
        request.form['answer'],
        id
    ))

    return redirect('/admin')

# ---------------- ASSIGN STUDENT ----------------
@app.route('/assign_student', methods=['GET', 'POST'])
def assign_student():
    if 'admin' not in session:
        return redirect('/admin_login')

    cur.execute(
        "SELECT * FROM student WHERE admin_username=%s",
        (session['admin'],)
    )
    students = cur.fetchall()

    if request.method == 'POST':

        student_ids = request.form.getlist('student_id')

        print("SELECTED STUDENTS:", student_ids)

        # get timer from admin_settings
        cur.execute("""
            SELECT quiz_time
            FROM admin_settings
            WHERE admin_username=%s
        """, (session['admin'],))

        result = cur.fetchone()

        if result:
            quiz_time = result[0]
        else:
            quiz_time = 60

        print("ADMIN TIMER:", quiz_time)

        # INSERT FIX (THIS IS MOST IMPORTANT PART)
        for sid in student_ids:
            cur.execute("""
                INSERT INTO quiz_assignments (student_id, admin_username, time)
                VALUES (%s, %s, %s)
            """, (sid, session['admin'], quiz_time))

        conn.commit()

        return redirect('/assign_success')

    return render_template('assign_student.html', students=students)

# ---------------- ASSIGN SUCCESS ----------------
@app.route('/assign_success')
def assign_success():
    if 'admin' not in session:
        return redirect('/admin_login')

    return render_template('assign_success.html')
# ---------------- STUDENT LOGIN ----------------
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        name = request.form['name']
        seatno = request.form['seatno']

        cur.execute(
            "SELECT * FROM student WHERE name=%s AND aadhar=%s",
            (name, seatno)
        )
        student = cur.fetchone()

        if student:
            session['student'] = name
            session['student_id'] = student[0] 
            session['student_admin'] = student[3]
            return redirect('/student_quiz')
        else:
            return "Not Assigned / Invalid"

    return render_template('student_login.html')

 
# ---------------- STUDENT QUIZ ------------
@app.route('/student_quiz', methods=['GET', 'POST'])
def student_quiz():
    if 'student' not in session:
        return redirect('/student_login')

    admin_user = session['student_admin']
    student_name = session['student']
    student_id = session.get('student_id')

    # ✅ GET TIMER FROM DATABASE
      
    cur.execute("""
        SELECT quiz_time
        FROM admin_settings
        WHERE admin_username=%s
    """, (admin_user,))

    result = cur.fetchone()
    quiz_time = result[0] if result else 60

    # GET QUESTIONS
    cur.execute(
        "SELECT * FROM questions WHERE admin_username=%s",
        (admin_user,)
    )
    questions = cur.fetchall()

    # SUBMIT QUIZ
    if request.method == 'POST':
        score = 0

        for q in questions:
            selected = request.form.get(str(q[0]))
            correct = str(q[6]).strip()

            if selected and selected.strip() == correct:
                score += 1

        safe_execute("""
            INSERT INTO results (name, aadhar, score, total, admin_username)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            student_name,
            request.form.get("aadhar"),
            score,
            len(questions),
            admin_user
        ))

        return render_template(
            'result.html',
            name=student_name,
            score=score,
            total=len(questions)
        )

    return render_template(
        'quiz.html',
        questions=questions,
        time=quiz_time
    )
# ---------------- RESULTS DASHBOARD ----------------
@app.route('/assigned_dashboard')
def assigned_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    cur.execute("""
        SELECT r.title, s.name, s.aadhar, r.score, r.total
        FROM results r
        JOIN student s ON s.name = r.name
        WHERE r.admin_username = %s
        ORDER BY r.title
    """, (session['admin'],))

    rows = cur.fetchall()

    grouped = {}

    for title, name, aadhar, score, total in rows:
        if title not in grouped:
            grouped[title] = []
        grouped[title].append((name, aadhar, score, total))

    return render_template('assigned_dashboard.html', grouped=grouped)
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
