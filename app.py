from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_session import Session
import oracledb
import re
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

DB_DSN = "localhost:1521/FREEPDB1"

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            test_conn = oracledb.connect(user=username, password=password, dsn=DB_DSN)
            test_conn.close()
            
            session['user'] = username
            session['pwd'] = password
            return redirect(url_for('dashboard'))
            
        except oracledb.Error as e:
            flash("Login Failed: Invalid Username or Password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    pwd = session['pwd']
    
    is_admin = user.upper().startswith('A') or user.upper().startswith('SYS')
    is_teacher = user.upper().startswith('T') or 'TEACHER' in user.upper()
    
    students_data = []
    audit_data = []

    try:
        with oracledb.connect(user=user, password=pwd, dsn=DB_DSN) as conn:
            with conn.cursor() as cursor:
                if is_admin:
                    cursor.execute("SELECT student_id, name, grade, national_id FROM SYS.students ORDER BY student_id")
                    students_data = cursor.fetchall()
                    
                    cursor.execute("""
                        SELECT event_timestamp, dbusername, action_name, object_name 
                        FROM UNIFIED_AUDIT_TRAIL 
                        WHERE object_name = 'STUDENTS' 
                           OR action_name IN ('CREATE USER', 'DROP USER')
                        ORDER BY event_timestamp DESC 
                        FETCH FIRST 10 ROWS ONLY
                    """)
                    audit_data = cursor.fetchall()

                elif is_teacher:
                    cursor.execute("SELECT student_id, name, grade FROM SYS.view_all_students_public ORDER BY student_id")
                    students_data = cursor.fetchall()

                else:
                    cursor.execute("SELECT student_id, name, grade FROM SYS.view_my_record")
                    students_data = cursor.fetchall()

    except oracledb.Error as e:
        flash(f"Database Error: {e}")

    return render_template('dashboard.html', 
                           students=students_data, audit_logs=audit_data,
                           is_admin=is_admin, is_teacher=is_teacher, username=user)

@app.route('/update_grade', methods=['POST'])
def update_grade():
    if 'user' not in session: return redirect(url_for('login'))
    
    student_id = request.form['student_id']
    new_grade = request.form['grade']

    try:
        with oracledb.connect(user=session['user'], password=session['pwd'], dsn=DB_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE SYS.view_all_students_public 
                    SET grade = :1 
                    WHERE student_id = :2
                """, [new_grade, student_id])
                conn.commit()
    except oracledb.Error as e:
        flash(f"Update Failed: {e}")

    return redirect(url_for('dashboard'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'user' not in session: return redirect(url_for('login'))
    
    new_id = request.form['student_id'].upper()
    new_name = request.form['name']
    new_grade = request.form['grade']
    new_nat_id = request.form['national_id']
    new_pass = request.form['password']

    if not re.match(r"^[A-Z0-9_]+$", new_id):
        flash("Error: User ID must be alphanumeric.")
        return redirect(url_for('dashboard'))

    if not re.match(r"^[A-Za-z0-9_#$]+$", new_pass):
        flash("Error: Password contains invalid characters.")
        return redirect(url_for('dashboard'))

    try:
        with oracledb.connect(user=session['user'], password=session['pwd'], dsn=DB_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE USER {new_id} IDENTIFIED BY \"{new_pass}\"")
                cursor.execute(f"GRANT CREATE SESSION TO {new_id}")
                
                if new_id.startswith('S'):
                    cursor.execute(f"GRANT sec_student_role TO {new_id}")
                elif new_id.startswith('T'):
                    cursor.execute(f"GRANT sec_teacher_role TO {new_id}")

                cursor.execute("""
                    INSERT INTO SYS.students (student_id, name, grade, national_id) 
                    VALUES (:1, :2, :3, :4)
                """, [new_id, new_name, new_grade, new_nat_id])
                
                conn.commit()
                flash(f"Success! User {new_id} created.")
    except oracledb.Error as e:
        flash(f"Creation Failed: {e}")

    return redirect(url_for('dashboard'))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    if 'user' not in session: return redirect(url_for('login'))
    
    target_user = request.form['student_id'].upper()
    
    if target_user in ['SYS', 'SYSTEM', session['user'].upper()]:
        flash("Cannot delete a system or active admin account.")
        return redirect(url_for('dashboard'))

    try:
        with oracledb.connect(user=session['user'], password=session['pwd'], dsn=DB_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM SYS.students WHERE student_id = :1", [target_user])
                
                if re.match(r"^[A-Z0-9_]+$", target_user):
                    cursor.execute(f"DROP USER {target_user} CASCADE")
                
                conn.commit()
                flash(f"User {target_user} completely removed from system.")
    except oracledb.Error as e:
        flash(f"Deletion Failed: {e}")

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)