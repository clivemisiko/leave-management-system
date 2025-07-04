from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, session, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from backend.app.extensions import get_mysql_connection, mail
from functools import wraps
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from ..utils.email import send_reset_email
from ..utils.auth import update_password
from flask_mail import Message
from weasyprint import HTML, CSS
from email_validator import validate_email, EmailNotValidError
import smtplib
import base64
import os
import re

# ✅ Function to encode logo to base64
def get_logo_base64():
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'kenya_logo.png')

    if not os.path.exists(logo_path):
        print("❌ LOGO FILE NOT FOUND:", logo_path)
        return ""

    try:
        with open(logo_path, 'rb') as logo_file:
            encoded = base64.b64encode(logo_file.read()).decode('utf-8')
        print("✅ LOGO ENCODED SUCCESSFULLY")
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print("❌ ERROR READING LOGO FILE:", e)
        return ""

# Now you can safely use get_mysql_connection() anywhere below in this module.

staff_bp = Blueprint('staff', __name__)

# In your routes.py - must use same salt and secret key
def get_serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='password-reset-salt'  # Must match in both routes
    )
def get_reset_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset')

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'staff_logged_in' not in session:
            flash('Please log in as staff to access this page.', 'danger')
            return redirect(url_for('staff.staff_login'))
        return f(*args, **kwargs)
    return decorated_function

@staff_bp.route('/dashboard')
@staff_required
def staff_dashboard():

    if request.referrer and url_for('staff.staff_login') in request.referrer:
        flash('Login successful', 'success')
    from collections import Counter
    from datetime import datetime, date

    staff_id = session.get('staff_id')
    cur = conn = get_mysql_connection(); cur = conn.cursor()

    # Fetch current leave balance from staff table (don't calculate here)
    cur.execute("SELECT leave_balance FROM staff WHERE id = %s", (staff_id,))
    staff_info = cur.fetchone()
    current_balance = staff_info['leave_balance'] if staff_info else 0

    # Fetch all applications
    cur.execute("""
        SELECT 
            id, name, pno, leave_days, 
            start_date, end_date, status,
            submitted_at, approved_at, approved_by,
            rejected_at, rejected_by
        FROM leave_applications 
        WHERE staff_id = %s 
        ORDER BY submitted_at DESC
    """, (staff_id,))
    raw_rows = cur.fetchall()
    cur.close()

    applications = []
    status_list = []

    for row in raw_rows:
        # Safe fallback for missing fields
        leave_days = row.get('leave_days') or 0
        start_date = row.get('start_date')
        end_date = row.get('end_date')
        submitted_at = row.get('submitted_at')

        # Safe date parsing
        try:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except:
            start_date = None

        try:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except:
            end_date = None

        try:
            if isinstance(submitted_at, str):
                submitted_at = datetime.strptime(submitted_at, '%Y-%m-%d %H:%M:%S')
        except:
            submitted_at = None

        row['leave_days'] = leave_days
        row['start_date'] = start_date
        row['end_date'] = end_date
        row['submitted_at'] = submitted_at

        applications.append(row)
        status_list.append(row['status'])

    # Stats
    counts = Counter(status_list)
    total = len(applications)
    approved = counts.get('approved', 0)
    pending = counts.get('pending', 0)
    rejected = counts.get('rejected', 0)

    return render_template(
        'staff/dashboard.html',
        applications=applications,
        total=total,
        approved=approved,
        pending=pending,
        rejected=rejected,
        leave_balance=current_balance  # Use the stored balance directly
    
    )

@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        pno = request.form.get('pno', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()  # Normalize email
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate required fields
        if not all([pno, username, email, password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('staff.register'))
        
        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('staff.register'))
        
        # Validate email format
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            flash('Please enter a valid email address', 'danger')
            return redirect(url_for('staff.register'))
        
        # Check if user already exists
        cur = None
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()

            # Check if pno or email already exists
            cur.execute("SELECT id FROM staff WHERE pno = %s OR email = %s", (pno, email))
            if cur.fetchone():
                flash('P/Number or email already registered', 'danger')
                return redirect(url_for('staff.register'))
            
            # Hash password and create user
            hashed_password = generate_password_hash(password)
            cur.execute(
                "INSERT INTO staff (pno, username, email, password) VALUES (%s, %s, %s, %s)",
                (pno, username, email, hashed_password)
            )
            conn = get_mysql_connection()

            cur = conn.cursor()

            conn.commit()
            conn.rollback()


            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('staff.staff_login'))
            
        except Exception as registration_error:
            if 'conn' in locals():
                conn.rollback()
            current_app.logger.error(f"Registration error: {registration_error}")
            flash(f"Registration failed: {registration_error}", 'danger')
            return redirect(url_for('staff.register'))

        finally:
            if cur:
                cur.close()
    
    # GET request - show registration form
    return render_template('staff/register.html')

@staff_bp.route('/login', methods=['GET', 'POST'])
def staff_login():
    session.clear() 
    if request.method == 'POST':
        login_input = request.form['login_input'].strip()  # Can be email or pno
        password = request.form['password']
        
        cur = conn = get_mysql_connection()
        cur = conn.cursor()
        try:
            # Check if input is email or pno
            is_email = '@' in login_input
            
            if is_email:
                cur.execute(
                    "SELECT id, pno, username, password FROM staff WHERE email = %s", 
                    (login_input,)
                )
            else:
                cur.execute(
                    "SELECT id, pno, username, password FROM staff WHERE pno = %s", 
                    (login_input,)
                )
            
            staff = cur.fetchone()
            
            if staff and check_password_hash(staff['password'], password):
                session['staff_logged_in'] = True
                session['staff_id'] = staff['id']
                session['staff_pno'] = staff['pno']
                session['staff_name'] = staff['username']
                return redirect(url_for('staff.staff_dashboard'))
            
            flash('Invalid login credentials', 'danger')
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('Login error', 'danger')
        finally:
            cur.close()
    
    return render_template('staff/login.html')


from flask_mail import Message

@staff_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address', 'danger')
            return redirect(url_for('staff.forgot_password'))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please enter a valid email address', 'danger')
            return redirect(url_for('staff.forgot_password'))

        try:
            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, username FROM staff WHERE email = %s", (email,))
            staff = cur.fetchone()

            # Always flash the same message for security
            flash('If an account exists with this email, a reset link has been sent.', 'success')

            if staff:
                # Generate a secure token
                serializer = get_serializer()
                token = serializer.dumps(email)
                reset_url = url_for('staff.reset_password', token=token, _external=True)
                expires_at = datetime.utcnow() + timedelta(hours=1)

                # Save token and expiry to DB
                cur.execute("""
                    UPDATE staff 
                    SET reset_token = %s, reset_token_expires = %s 
                    WHERE email = %s
                """, (token, expires_at, email))
                conn.commit()

                # Send reset email
                msg = Message(
                    subject='Password Reset Request',
                    recipients=[email],
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    body=f"Hi,\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you didn’t request this, ignore this email."
                )
                mail.send(msg)

            return redirect(url_for('staff.staff_login'))

        except Exception as e:
            current_app.logger.error(f"Forgot password error: {str(e)}")
            flash('Failed to send reset email. Please try again.', 'danger')
            return redirect(url_for('staff.forgot_password'))

        finally:
            if 'cur' in locals():
                cur.close()

    return render_template('staff/forgot_password.html')


@staff_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not token or len(token) < 30:
        flash('Invalid reset link format', 'danger')
        return redirect(url_for('staff.forgot_password'))

    try:
        # Decode token
        serializer = get_serializer()
        try:
            email = serializer.loads(token, max_age=3600)
        except:
            flash('Reset link has expired or is invalid.', 'danger')
            return redirect(url_for('staff.forgot_password'))

        conn = get_mysql_connection()
        cur = conn.cursor()

        # Validate token in DB
        cur.execute("""
            SELECT id FROM staff 
            WHERE email = %s AND reset_token = %s AND reset_token_expires > UTC_TIMESTAMP()
        """, (email, token))
        user = cur.fetchone()

        if not user:
            flash('Invalid or expired reset token.', 'danger')
            return redirect(url_for('staff.forgot_password'))

        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if not password or len(password) < 8:
                flash('Password must be at least 8 characters.', 'danger')
                return render_template('staff/reset-password.html', token=token)

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('staff/reset-password.html', token=token)

            hashed_password = generate_password_hash(password)

            # Update password and clear reset token
            cur.execute("""
                UPDATE staff 
                SET password = %s, reset_token = NULL, reset_token_expires = NULL 
                WHERE email = %s
            """, (hashed_password, email))
            conn.commit()

            flash('Your password has been reset. Please login.', 'success')
            return redirect(url_for('staff.staff_login'))

        return render_template('staff/reset-password.html', token=token)

    except Exception as e:
        current_app.logger.error(f"Password reset error: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('staff.forgot_password'))

    finally:
        if 'cur' in locals():
            cur.close()

    
@staff_bp.route('/application/details/<int:app_id>')
@staff_required
def application_details(app_id):
    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leave_applications")
    data = cur.fetchall()

    cur.execute("""
        SELECT * FROM leave_applications 
        WHERE id = %s AND pno = %s
    """, (app_id, session['staff_id']))
    application = cur.fetchone()
    cur.close()
    
    if not application:
        return "Application not found", 404
    
    return render_template('staff/application_details.html', application=application)

@staff_bp.route('/application/new', methods=['GET', 'POST'], endpoint='create_application')
@staff_required
def create_staff_application():
    if request.method == 'POST':
        try:
            def parse_date(date_str):
                return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

            start_date = parse_date(request.form.get('start_date', ''))
            end_date = parse_date(request.form.get('end_date', ''))

            
            # Handle salary option
            salary_continue = request.form.get('salary_option', 'continue') == 'continue'
            salary_address = request.form.get('salary_address', '').strip() if not salary_continue else None

            last_leave_start = parse_date(request.form.get('last_leave_start', ''))
            last_leave_end = parse_date(request.form.get('last_leave_end', ''))

            form_data = {
                'name': session['staff_name'],
                'pno' : session['staff_pno'],
                'designation': request.form.get('designation', '').strip(),
                'leave_days': int(request.form['leave_days']),
                'start_date': start_date,
                'end_date': end_date,
                'contact_address': request.form['contact_address'],
                'contact_tel': request.form['contact_tel'],
                'leave_type': request.form['leave_type'],
                'delegate': request.form.get('delegate', '').strip(),
                'staff_id': session['staff_id'],
                'salary_continue': salary_continue,
                'salary_address': salary_address,
                'last_leave_start': last_leave_start,
                'last_leave_end': last_leave_end
            }

            # Validate required fields
            if not all([
                form_data['designation'],
                form_data['leave_days'],
                form_data['start_date'],
                form_data['end_date'],
                form_data['contact_address'],
                form_data['contact_tel'],
                form_data['leave_type'],
            ]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('staff.create_application'))

            if not form_data['salary_continue'] and not form_data['salary_address']:
                flash('Alternate payment address is required when salary is not continuing through the bank.', 'danger')
                return redirect(url_for('staff.create_application'))
            

            
            # Open a cursor to fetch staff leave balance
            conn = get_mysql_connection(); cur = conn.cursor()
            cur.execute("SELECT leave_balance FROM staff WHERE id = %s", (form_data['staff_id'],))
            staff_row = cur.fetchone()

            if not staff_row:
                flash("Unable to fetch leave balance for current staff.", "danger")
                return redirect(url_for('staff.create_application'))

            leave_balance = staff_row['leave_balance']
            # Save to DB


            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM leave_applications")
            data = cur.fetchall()

            cur.execute("""
    INSERT INTO leave_applications 
    (name, pno, designation, leave_days, start_date, end_date, contact_address, contact_tel,
     leave_type, delegate, staff_id, salary_continue, salary_address,
     last_leave_start, last_leave_end, leave_balance)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    form_data['name'],
    form_data['pno'],
    form_data['designation'],
    form_data['leave_days'],
    form_data['start_date'],
    form_data['end_date'],
    form_data['contact_address'],
    form_data['contact_tel'],
    form_data['leave_type'],
    form_data['delegate'],
    form_data['staff_id'],
    form_data['salary_continue'],
    form_data['salary_address'],
    form_data['last_leave_start'],
    form_data['last_leave_end'],
    leave_balance  # ✅ Newly added
))

            conn = get_mysql_connection()

            cur = conn.cursor()

            conn.commit()
            conn.rollback()


            flash('Leave application submitted successfully.', 'success')
            return redirect(url_for('staff.staff_dashboard'))

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('staff.create_application'))

        finally:
            if 'cur' in locals():
                cur.close()

    return render_template('staff/create_application.html')

@staff_bp.route('/application/print/<int:app_id>')
@staff_required
def print_application(app_id):
    cur = conn = get_mysql_connection(); cur = conn.cursor()

    cur.execute("""
        SELECT * FROM leave_applications WHERE id = %s AND staff_id = %s
    """, (app_id, session['staff_id']))
    app = cur.fetchone()

    if not app:
        flash("Application not found or unauthorized.", "danger")
        return redirect(url_for('staff.staff_dashboard'))

    if app['status'] != 'approved':
        flash("You can only print approved leave applications.", "warning")
        return redirect(url_for('staff.staff_dashboard'))

    cur.execute("SELECT leave_balance FROM staff WHERE id = %s", (session['staff_id'],))
    staff_info = cur.fetchone()
    cur.close()

    app['leave_balance'] = staff_info['leave_balance'] if staff_info else 'N/A'

    # ✅ Select correct PDF template
    template_name = 'admin/pdf_template_staff.html' if app.get('user_type') == 'Staff' else 'admin/pdf_template_hod.html'

        # ✅ Render PDF with full base_url so logo resolves
    logo_base64 = get_logo_base64()
    rendered = render_template(template_name, app=app, logo_base64=logo_base64)
    pdf = HTML(string=rendered, base_url=request.url_root).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=leave_application_{app_id}.pdf'
    return response

@staff_bp.route('/logout')
def staff_logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('staff.staff_login'))

@staff_bp.route('/application/cancel/<int:id>')
@staff_required
def cancel_application(id):
    staff_id = session.get('staff_id')
    cur = conn = get_mysql_connection(); cur = conn.cursor()
    try:
        # Fetch application
        cur.execute("""
            SELECT leave_days, status 
            FROM leave_applications 
            WHERE id = %s AND staff_id = %s
        """, (id, staff_id))
        app = cur.fetchone()

        if not app:
            flash('Application not found or unauthorized.', 'danger')
            return redirect(url_for('staff.staff_dashboard'))

        if app['status'] != 'pending':
            flash('Only pending applications can be cancelled.', 'warning')
            return redirect(url_for('staff.staff_dashboard'))

        # Restore balance
        cur.execute("UPDATE staff SET leave_balance = leave_balance + %s WHERE id = %s", (app['leave_days'], staff_id))

        # Cancel the application
        cur.execute("""
            UPDATE leave_applications 
            SET status = 'cancelled' 
            WHERE id = %s
        """, (id,))

        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()


        flash('Application cancelled and balance restored.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error cancelling application: {str(e)}', 'danger')

    finally:
        cur.close()

    return redirect(url_for('staff.staff_dashboard'))

