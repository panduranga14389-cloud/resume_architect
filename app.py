import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'system_core_brutal_secret_key_matrix'

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def enforce_fresh_database():
    """Forces an aggressive baseline check and initial compilation of tables."""
    db_is_empty = True
    if os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if cursor.fetchone():
                db_is_empty = False
        except Exception:
            pass
        finally:
            conn.close()

    # If tables are missing or database file is structurally broken, clean rebuild
    if db_is_empty:
        print("⚠️ System Core Database tables missing. Reinitializing target context...")
        if os.path.exists('schema.sql'):
            conn = sqlite3.connect(DATABASE)
            with open('schema.sql', 'r') as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
            print("✅ Database successfully built out from schema.sql constraints.")
        else:
            print("❌ Critical System Error: schema.sql file not located in root folder path!")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SYSTEM ACCESS INTERFACES (AUTH) ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login authentication parameters.', 'error')
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Security keys misaligned. Password confirmation match failed.', 'error')
            return render_template('signup.html')
            
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)',
                         (full_name, email, hashed_password))
            conn.commit()
            flash('Identity registration successful. Log in below.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email entity already mapped to existing system profile.', 'error')
        finally:
            conn.close()
            
    return render_template('signup.html')

# --- SIMPLIFIED DIRECT PASSWORD OVERWRITE ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password)
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            conn.execute('UPDATE users SET password = ? WHERE email = ?', (hashed_password, email))
            conn.commit()
            conn.close()
            flash('System credentials successfully updated!', 'success')
            return redirect(url_for('login'))
        else:
            conn.close()
            flash('No matching identity mapped to that email address.', 'error')
            
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- INTERACTIVE WORKSPACE MONITOR ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    resume = conn.execute('SELECT * FROM resumes WHERE user_id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('dashboard.html', resume=resume)

# --- ARRAY COMPILATION ENGINE (BUILDER) ---

@app.route('/builder', methods=['GET', 'POST'])
def builder():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        linkedin = request.form.get('linkedin')
        github = request.form.get('github')
        portfolio = request.form.get('portfolio')
        professional_summary = request.form.get('professional_summary')
        skills = request.form.get('skills')
        
        profile_img_path = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"user_{user_id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_img_path = f"/static/uploads/{filename}"

        existing = conn.execute('SELECT id FROM resumes WHERE user_id = ?', (user_id,)).fetchone()
        if existing:
            resume_id = existing['id']
            if profile_img_path:
                conn.execute('''UPDATE resumes SET full_name=?, phone=?, email=?, address=?, linkedin=?, github=?, portfolio=?, professional_summary=?, skills=?, profile_image=? WHERE id=?''',
                             (full_name, phone, email, address, linkedin, github, portfolio, professional_summary, skills, profile_img_path, resume_id))
            else:
                conn.execute('''UPDATE resumes SET full_name=?, phone=?, email=?, address=?, linkedin=?, github=?, portfolio=?, professional_summary=?, skills=? WHERE id=?''',
                             (full_name, phone, email, address, linkedin, github, portfolio, professional_summary, skills, resume_id))
        else:
            cur = conn.execute('''INSERT INTO resumes (user_id, full_name, phone, email, address, linkedin, github, portfolio, professional_summary, skills, profile_image) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (user_id, full_name, phone, email, address, linkedin, github, portfolio, professional_summary, skills, profile_img_path))
            resume_id = cur.lastrowid

        conn.execute('DELETE FROM education WHERE resume_id = ?', (resume_id,))
        conn.execute('DELETE FROM projects WHERE resume_id = ?', (resume_id,))
        conn.execute('DELETE FROM certifications WHERE resume_id = ?', (resume_id,))
        conn.execute('DELETE FROM achievements WHERE resume_id = ?', (resume_id,))
        conn.execute('DELETE FROM coding_profiles WHERE resume_id = ?', (resume_id,))

        institutions = request.form.getlist('institution[]')
        degrees = request.form.getlist('degree[]')
        scores = request.form.getlist('score[]')
        years = request.form.getlist('passing_year[]')
        for i in range(len(institutions)):
            if institutions[i].strip():
                conn.execute('INSERT INTO education (resume_id, institution, degree, score, passing_year) VALUES (?, ?, ?, ?, ?)',
                             (resume_id, institutions[i], degrees[i], scores[i], years[i]))

        p_titles = request.form.getlist('p_title[]')
        p_techs = request.form.getlist('p_tech[]')
        p_descs = request.form.getlist('p_desc[]')
        for i in range(len(p_titles)):
            if p_titles[i].strip():
                conn.execute('INSERT INTO projects (resume_id, title, tech_stack, description) VALUES (?, ?, ?, ?)',
                             (resume_id, p_titles[i], p_techs[i], p_descs[i]))

        certs = request.form.getlist('cert[]')
        for cert in certs:
            if cert.strip():
                conn.execute('INSERT INTO certifications (resume_id, cert_name) VALUES (?, ?)', (resume_id, cert))

        achs = request.form.getlist('ach[]')
        for ach in achs:
            if ach.strip():
                conn.execute('INSERT INTO achievements (resume_id, achievement_detail) VALUES (?, ?)', (resume_id, ach))

        leetcode = request.form.get('leetcode')
        codechef = request.form.get('codechef')
        hackerrank = request.form.get('hackerrank')
        conn.execute('INSERT INTO coding_profiles (resume_id, leetcode, codechef, hackerrank) VALUES (?, ?, ?, ?)',
                     (resume_id, leetcode, codechef, hackerrank))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    resume = conn.execute('SELECT * FROM resumes WHERE user_id = ?', (user_id,)).fetchone()
    education, projects, certifications, achievements, coding = [], [], [], [], None
    
    if resume:
        resume_id = resume['id']
        education = conn.execute('SELECT * FROM education WHERE resume_id = ?', (resume_id,)).fetchall()
        projects = conn.execute('SELECT * FROM projects WHERE resume_id = ?', (resume_id,)).fetchall()
        certifications = conn.execute('SELECT * FROM certifications WHERE resume_id = ?', (resume_id,)).fetchall()
        achievements = conn.execute('SELECT * FROM achievements WHERE resume_id = ?', (resume_id,)).fetchall()
        coding = conn.execute('SELECT * FROM coding_profiles WHERE resume_id = ?', (resume_id,)).fetchone()
        
    conn.close()
    return render_template('builder.html', resume=resume, education=education, projects=projects, certifications=certifications, achievements=achievements, coding=coding)

# --- PRODUCTION MATRIX RENDER COMPILE ---

@app.route('/view')
def view_resume():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    resume = conn.execute('SELECT * FROM resumes WHERE user_id = ?', (session['user_id'],)).fetchone()
    
    if not resume:
        conn.close()
        return "No template map context active.", 404
        
    resume_id = resume['id']
    education = conn.execute('SELECT * FROM education WHERE resume_id = ?', (resume_id,)).fetchall()
    projects = conn.execute('SELECT * FROM projects WHERE resume_id = ?', (resume_id,)).fetchall()
    certifications = conn.execute('SELECT * FROM certifications WHERE resume_id = ?', (resume_id,)).fetchall()
    achievements = conn.execute('SELECT * FROM achievements WHERE resume_id = ?', (resume_id,)).fetchall()
    coding = conn.execute('SELECT * FROM coding_profiles WHERE resume_id = ?', (resume_id,)).fetchone()
    conn.close()
    
    return render_template('resume_template.html', resume=resume, education=education, projects=projects, certifications=certifications, achievements=achievements, coding=coding)

if __name__ == '__main__':
    # Force runtime infrastructure alignment parsing check
    enforce_fresh_database()
    app.run(debug=True)