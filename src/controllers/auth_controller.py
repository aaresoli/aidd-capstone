"""
Authentication Controller
Handles user registration, login, and logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.data_access.user_dal import UserDAL
from src.utils.validators import Validator

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department = request.form.get('department', '').strip()
        role = request.form.get('role', 'student')
        
        # Validation
        valid, msg = Validator.validate_string(name, 2, 100, "Name")
        if not valid:
            flash(msg, 'danger')
            return render_template('auth/register.html')
        
        if not Validator.validate_email(email):
            flash('Invalid email address', 'danger')
            return render_template('auth/register.html')
        
        allowed_domains = current_app.config.get('ALLOWED_EMAIL_DOMAINS')
        if allowed_domains:
            email_domain = email.split('@')[-1]
            if email_domain not in allowed_domains:
                allowed_list = ', '.join(sorted(allowed_domains))
                flash(f'Registration is limited to {allowed_list} email addresses', 'danger')
                return render_template('auth/register.html')
        
        valid, msg = Validator.validate_password(password)
        if not valid:
            flash(msg, 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
        
        valid, msg = Validator.validate_role(role)
        if not valid:
            flash(msg, 'danger')
            return render_template('auth/register.html')

        if department:
            valid, msg = Validator.validate_string(department, 2, 120, "Department")
            if not valid:
                flash(msg, 'danger')
                return render_template('auth/register.html')
            department = Validator.sanitize_html(department)

        name = Validator.sanitize_html(name)
        
        # Check if email already exists
        existing_user = UserDAL.get_user_by_email(email)
        if existing_user:
            flash('Email already registered', 'danger')
            return render_template('auth/register.html')
        
        # Create user
        try:
            user = UserDAL.create_user(name, email, password, role, department)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return render_template('auth/login.html')

        if not Validator.validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/login.html')
        
        user = UserDAL.verify_password(email, password)
        if user:
            if getattr(user, 'is_suspended', False):
                flash('Your account is suspended. Contact an administrator for assistance.', 'danger')
                return render_template('auth/login.html')
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))
