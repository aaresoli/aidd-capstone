"""
Authentication Controller
Handles user registration, login, and logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.data_access.user_dal import UserDAL
from src.utils.validators import Validator
from src.utils.email_verification import EmailVerificationService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration endpoint.
    
    Handles both GET (display registration form) and POST (process registration)
    requests. Validates all input fields, checks for duplicate emails, and
    creates new user accounts with email verification tokens.
    
    Returns:
        Response: Registration form (GET) or redirect to verification page (POST)
    """
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
            user = UserDAL.create_user(name, email, password, role, department, email_verified=False)

            # Generate verification token
            token = EmailVerificationService.generate_verification_token()
            expiry = EmailVerificationService.get_token_expiry()
            UserDAL.set_verification_token(user.user_id, token, expiry)
            verification_url = EmailVerificationService.build_verification_url(token)

            flash('Registration successful! Use the link below to verify your account.', 'success')
            return render_template(
                'auth/verification_link.html',
                verification_url=verification_url,
                email=email,
                user_name=name,
                just_registered=True,
                token_ttl=EmailVerificationService.TOKEN_EXPIRY_HOURS
            )
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User authentication endpoint.
    
    Handles both GET (display login form) and POST (authenticate user) requests.
    Validates credentials, checks account status (suspended/verified), and
    establishes user session via Flask-Login.
    
    Returns:
        Response: Login form (GET) or redirect to dashboard (POST on success)
    """
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
            # Security check: prevent login for suspended accounts
            if getattr(user, 'is_suspended', False):
                flash('Your account is suspended. Contact an administrator for assistance.', 'danger')
                return render_template('auth/login.html')

            # Email verification check: enforce verification if enabled in config
            # This prevents unverified users from accessing the system
            verification_required = current_app.config.get('EMAIL_VERIFICATION_ENABLED', True)
            if verification_required and not getattr(user, 'email_verified', False):
                flash('Please verify your email address before logging in. Use the link displayed after registration or request a new one.', 'warning')
                # Provide link to resend verification
                flash('Need a fresh link? <a href="' + url_for('auth.resend_verification_form') + '">Generate verification link</a>', 'info')
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
    """
    User logout endpoint.
    
    Clears the current user session via Flask-Login and redirects to homepage.
    Requires authentication to prevent CSRF attacks on logout actions.
    
    Returns:
        Response: Redirect to homepage with logout confirmation message
    """
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """
    Email verification endpoint via secure token.
    
    Verifies user email addresses using cryptographically secure tokens sent
    via email. Tokens are single-use and time-limited for security.
    
    Args:
        token (str): Verification token from email link
        
    Returns:
        Response: Redirect to login (success) or resend verification page (failure)
    """
    if not token:
        flash('Invalid verification link', 'danger')
        return redirect(url_for('index'))

    user = UserDAL.verify_email_by_token(token)

    if user:
        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    else:
        flash('Invalid or expired verification link. Please request a new one.', 'danger')
        return redirect(url_for('auth.resend_verification_form'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification_form():
    """
    Resend email verification link endpoint.
    
    Allows users to request a new verification token if the original link
    expired or was lost. Security: doesn't reveal whether email exists to
    prevent user enumeration attacks.
    
    Returns:
        Response: Resend verification form (GET) or verification link display (POST)
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address', 'danger')
            return render_template('auth/resend_verification.html')

        if not Validator.validate_email(email):
            flash('Invalid email address', 'danger')
            return render_template('auth/resend_verification.html')

        user = UserDAL.get_user_by_email(email)

        # Security: Don't reveal if email exists or not to prevent user enumeration
        if not user:
            # Generic message regardless of whether user exists
            flash('If an account exists with this email, a verification link has been sent.', 'info')
            return render_template('auth/resend_verification.html')

        # Check if already verified
        if getattr(user, 'email_verified', False):
            flash('Your email is already verified. You can log in.', 'info')
            return redirect(url_for('auth.login'))

        # Generate new token and display link
        try:
            token = EmailVerificationService.generate_verification_token()
            expiry = EmailVerificationService.get_token_expiry()
            UserDAL.resend_verification_token(user.user_id, token, expiry)
            verification_url = EmailVerificationService.build_verification_url(token)

            flash('Here is your refreshed verification link.', 'success')
            return render_template(
                'auth/verification_link.html',
                verification_url=verification_url,
                email=email,
                user_name=user.name,
                from_resend=True,
                token_ttl=EmailVerificationService.TOKEN_EXPIRY_HOURS
            )
        except Exception as e:
            flash('Failed to generate verification link. Please try again later.', 'danger')

        return render_template('auth/resend_verification.html')

    return render_template('auth/resend_verification.html')
