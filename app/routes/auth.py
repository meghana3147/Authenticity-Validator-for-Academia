from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import bcrypt, get_db
from app.models import User, create_user, create_university, create_student
from bson import ObjectId

auth_bp = Blueprint('auth', __name__)

ROLE_DASHBOARDS = {
    'admin':      'admin.dashboard',
    'university': 'university.dashboard',
    'student':    'student.dashboard',
    'employer':   'employer.dashboard',
}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_DASHBOARDS.get(current_user.role, 'main.index')))

    if request.method == 'POST':
        db    = get_db()
        email = request.form.get('email', '').strip().lower()
        pw    = request.form.get('password', '')
        doc   = db.users.find_one({'email': email})

        if doc and bcrypt.check_password_hash(doc['password'], pw):
            if not doc.get('is_approved') and doc['role'] != 'admin':
                flash('Account pending admin approval.', 'warning')
                return render_template('auth/login.html')
            user = User(doc)
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')
            return redirect(url_for(ROLE_DASHBOARDS.get(user.role, 'main.index')))
        flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db    = get_db()
        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pw    = request.form.get('password', '')
        role  = request.form.get('role', 'student')

        if db.users.find_one({'email': email}):
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        hashed = bcrypt.generate_password_hash(pw).decode('utf-8')
        auto_approve = role in ('student', 'employer')
        user_doc = create_user(name, email, hashed, role, is_approved=auto_approve)
        uid = str(user_doc['_id'])

        if role == 'university':
            inst = request.form.get('institution_name', name)
            create_university(uid, inst)
            flash('Registration submitted! Waiting for admin approval.', 'info')
        elif role == 'student':
            counter = db.students.count_documents({}) + 1
            create_student(uid, f'STU{counter:05d}')
            flash('Account created! You can now log in.', 'success')
        else:
            flash('Account created! You can now log in.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
