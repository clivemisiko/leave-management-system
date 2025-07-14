from flask import Blueprint, render_template, request,redirect, url_for, current_app, flash, session, make_response
from flask import abort, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from backend.app.extensions import get_mysql_connection, mail
from functools import wraps
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
from ..utils.email import send_reset_email
from ..utils.auth import update_password
from flask_mail import Message
from weasyprint import HTML, CSS
from backend.app.models import Staff, LeaveApplication
from backend.app.extensions import db
from email_validator import validate_email, EmailNotValidError
import os, pymysql
from werkzeug.utils import secure_filename
from backend.app.utils.email import send_email
from backend.app.utils.email import send_email
from backend.app.utils.audit import log_action
from flask import current_app
from collections import Counter
from werkzeug.utils import secure_filename
import tempfile
import os
import uuid
import re

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

# ✅ Function to encode logo to base64

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

from functools import wraps
from flask import session, redirect, url_for, flash

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"Checking staff login - session: {dict(session)}")  # Debug
        if 'staff_logged_in' not in session:
            flash('Please log in as staff to access this page.', 'danger')
            return redirect(url_for('staff.staff_login'))  # ✅ this was missing
        return f(*args, **kwargs)
    return decorated_function

@staff_bp.route('/dashboard')
@staff_required
def staff_dashboard():
    # Show login success message if coming from login page
    if request.referrer and url_for('staff.staff_login') in request.referrer:
        flash('Login successful', 'success')

    staff_id = session.get('staff_id')
    if not staff_id:
        flash('Session expired. Please login again.', 'danger')
        return redirect(url_for('staff.staff_login'))

    conn = None
    cur = None
    try:
        # Initialize database connection
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get staff basic information
        cur.execute("""
            SELECT username, pno, leave_balance 
            FROM staff 
            WHERE id = %s
        """, (staff_id,))
        staff = cur.fetchone()
        
        if not staff:
            flash('Staff record not found', 'danger')
            return redirect(url_for('staff.staff_login'))
            
        current_balance = staff['leave_balance']

        # Get all leave applications for this staff member
        cur.execute("""
            SELECT 
                id, start_date, end_date, status,
                submitted_at, approved_at, approved_by,
                rejected_at, rejected_by, supporting_doc,
                leave_type, designation, contact_address,
                contact_tel, delegate
            FROM leave_applications 
            WHERE staff_id = %s 
            ORDER BY submitted_at DESC
        """, (staff_id,))
        leave_apps = cur.fetchall()

        # Process applications data
        applications = []
        status_counts = {
            'approved': 0,
            'pending': 0,
            'rejected': 0
        }

        for app in leave_apps:
            # Calculate leave days
            leave_days = 0
            if app['start_date'] and app['end_date']:
                try:
                    leave_days = (app['end_date'] - app['start_date']).days + 1
                except Exception:
                    current_app.logger.warning(f"Invalid date range for application {app['id']}")

            # Build application data
            application_data = {
                'id': app['id'],
                'name': staff['username'],
                'pno': staff['pno'],
                'leave_days': leave_days,
                'start_date': app['start_date'],
                'end_date': app['end_date'],
                'status': app['status'],
                'submitted_at': app['submitted_at'],
                'approved_at': app.get('approved_at'),
                'approved_by': app.get('approved_by'),
                'rejected_at': app.get('rejected_at'),
                'rejected_by': app.get('rejected_by'),
                'supporting_doc': app.get('supporting_doc'),
                'leave_type': app.get('leave_type'),
                'designation': app.get('designation')
            }
            applications.append(application_data)
            
            # Count statuses
            if app['status'] in status_counts:
                status_counts[app['status']] += 1

        return render_template(
            'staff/dashboard.html',
            applications=applications,
            total=len(applications),
            approved=status_counts['approved'],
            pending=status_counts['pending'],
            rejected=status_counts['rejected'],
            leave_balance=current_balance
        )

    except pymysql.Error as db_error:
        current_app.logger.error(f"Database error in staff_dashboard: {str(db_error)}")
        flash("A database error occurred. Please try again.", "danger")
        return redirect(url_for('staff.staff_login'))

    except Exception as e:
        current_app.logger.error(f"Unexpected error in staff_dashboard: {str(e)}", exc_info=True)
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('staff.staff_login'))

    finally:
        # Ensure database connections are closed
        if cur:
            cur.close()
        if conn:
            conn.close()

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
        login_input = request.form['login_input'].strip()
        password = request.form['password']

        print(f"\n--- LOGIN ATTEMPT ---")
        print(f"Login input: {login_input}")
        print(f"Password: {password}")

        try:
            from backend.app.extensions import get_mysql_connection
            import pymysql
            from werkzeug.security import check_password_hash

            conn = get_mysql_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)

            # ✅ Determine login method
            if '@' in login_input:
                print("Querying by email")
                cur.execute("SELECT * FROM staff WHERE email = %s", (login_input,))
            else:
                print("Querying by pno")
                cur.execute("SELECT * FROM staff WHERE pno = %s", (login_input,))

            staff = cur.fetchone()
            cur.close()
            conn.close()

            print(f"Found staff: {staff}")

            if not staff:
                flash('No user found with those credentials', 'danger')
                return redirect(url_for('staff.staff_login'))

            # ✅ Password check
            print(f"Staff password hash: {staff['password']}")
            if not check_password_hash(staff['password'], password):
                flash('Incorrect password', 'danger')
                return redirect(url_for('staff.staff_login'))

            # ✅ Set session
            session['staff_logged_in'] = True
            session['staff_id'] = staff['id']
            session['staff_pno'] = staff['pno']
            session['staff_name'] = staff['username']

            print(f"Session set: {dict(session)}")

            return redirect(url_for('staff.staff_dashboard'))

        except Exception as e:
            print(f"Login error: {str(e)}")
            current_app.logger.error(f"Login error: {str(e)}")
            flash('Something went wrong during login.', 'danger')

    return render_template('staff/login.html')



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
    from werkzeug.utils import secure_filename
    import tempfile
    import os

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {
            'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'
        }

    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z").date()
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return None  # or raise Exception if you want to fail hard

    if request.method == 'POST':
        action = request.form.get('action')

        # 📅 Dates
        start_date = parse_date(request.form.get('start_date', ''))
        end_date = parse_date(request.form.get('end_date', ''))
        last_leave_start = parse_date(request.form.get('last_leave_start', ''))
        last_leave_end = parse_date(request.form.get('last_leave_end', ''))

        # 💰 Salary
        salary_continue = request.form.get('salary_option', 'continue') == 'continue'
        salary_address = request.form.get('salary_address', '').strip() if not salary_continue else None

        # 📝 Form data
        form_data = {
            'name': session['staff_name'],
            'pno': session['staff_pno'],
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
            'last_leave_end': last_leave_end,
        }

        # Validate
        if not all([form_data['designation'], form_data['leave_days'], form_data['start_date'],
                    form_data['end_date'], form_data['contact_address'], form_data['contact_tel'],
                    form_data['leave_type']]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('staff.create_application'))

        if not form_data['salary_continue'] and not form_data['salary_address']:
            flash('Alternate payment address is required.', 'danger')
            return redirect(url_for('staff.create_application'))

        # 📁 Handle upload (preview mode: don't save permanently)
        uploaded_file = request.files.get('supporting_doc')
        supporting_doc_path = None
        original_filename = None

        if uploaded_file and uploaded_file.filename != '':
            if not allowed_file(uploaded_file.filename):
                flash("Invalid file type. Allowed: PDF, Word, JPG, PNG", "danger")
                return redirect(url_for('staff.create_application'))

            # ✅ Ensure uploads folder exists
            uploads_folder = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(uploads_folder, exist_ok=True)

            # ✅ Generate unique filename using UUID
            unique_filename = f"{uuid.uuid4().hex}_{secure_filename(uploaded_file.filename)}"
            saved_path = os.path.join(uploads_folder, unique_filename)

            uploaded_file.save(saved_path)

            # ✅ Store relative path (for url_for('static', filename=...))
            supporting_doc_path = os.path.join('uploads', unique_filename)
            original_filename = uploaded_file.filename

        if action == 'review':
            # ✅ Store data in session before redirecting
            session['preview_form_data'] = form_data
            session['preview_file_path'] = supporting_doc_path
            session['preview_original_filename'] = original_filename
            return redirect(url_for('staff.preview_application'))  # 🛠 matches the GET route


        elif action == 'submit':
            try:
                conn = get_mysql_connection()
                cur = conn.cursor(pymysql.cursors.DictCursor)

                cur.execute("SELECT leave_balance, email FROM staff WHERE id = %s", (form_data['staff_id'],))
                staff_row = cur.fetchone()

                if not staff_row:
                    flash("Unable to fetch staff details.", "danger")
                    return redirect(url_for('staff.create_application'))

                leave_balance = staff_row['leave_balance']
                staff_email = staff_row['email']

                # ✅ Get saved path from hidden field
                supporting_doc_path = request.form.get('saved_doc_path')
                original_filename = request.form.get('original_filename')

                # ✅ Skip re-saving — we already saved during review
                # but double-check the file exists:
                if supporting_doc_path:
                    absolute_path = os.path.join(current_app.static_folder, supporting_doc_path)
                    if not os.path.exists(absolute_path):
                        flash("Uploaded file not found. Please re-attach and try again.", "danger")
                        return redirect(url_for('staff.create_application'))

                # ✅ Insert into DB
                cur.execute("""
                    INSERT INTO leave_applications 
                    (name, pno, designation, leave_days, start_date, end_date, contact_address, contact_tel,
                    leave_type, delegate, staff_id, salary_continue, salary_address,
                    last_leave_start, last_leave_end, leave_balance, supporting_doc)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    form_data['name'], form_data['pno'], form_data['designation'],
                    form_data['leave_days'], form_data['start_date'], form_data['end_date'],
                    form_data['contact_address'], form_data['contact_tel'], form_data['leave_type'],
                    form_data['delegate'], form_data['staff_id'], form_data['salary_continue'],
                    form_data['salary_address'], form_data['last_leave_start'],
                    form_data['last_leave_end'], leave_balance, supporting_doc_path
                ))



                conn.commit()

                log_action(f"{form_data['name']} submitted a leave application", staff_id=form_data['staff_id'])

                send_email(
                    subject="Leave Application Submitted",
                    recipients=[staff_email],
                    body=f"Hello {form_data['name']},\n\nYour leave application has been submitted successfully."
                )

                send_email(
                    subject="New Leave Application Submitted",
                    recipients=["clivebillzerean@gmail.com"],
                    body=f"{form_data['name']} ({form_data['pno']}) has submitted a new leave application."
                )

                flash('Leave application submitted successfully.', 'success')
                return redirect(url_for('staff.staff_dashboard'))

            except Exception as e:
                if 'conn' in locals():
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
    conn = get_mysql_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM leave_applications 
        WHERE id = %s AND staff_id = %s
    """, (app_id, session['staff_id']))
    app = cur.fetchone()

    if not app:
        flash("Application not found or unauthorized.", "danger")
        return redirect(url_for('staff.staff_dashboard'))

    if app['status'] != 'approved':
        flash("You can only print approved leave applications.", "warning")
        return redirect(url_for('staff.staff_dashboard'))

    # Add leave balance
    cur.execute("SELECT leave_balance FROM staff WHERE id = %s", (session['staff_id'],))
    staff_info = cur.fetchone()
    cur.close()

    app['leave_balance'] = staff_info['leave_balance'] if staff_info else 'N/A'

    # Select correct template
    template_name = 'admin/pdf_template_staff.html' if app.get('user_type') == 'Staff' else 'admin/pdf_template_hod.html'

    # Generate PDF with logo
    logo_base64 = current_app.get_logo_base64()
    if not logo_base64:
            print("⚠️ WARNING: Logo not found or couldn't be loaded")
            
    rendered_html = render_template(template_name, app=app, logo_base64=logo_base64)
    pdf = HTML(string=rendered_html, base_url=request.url_root).write_pdf()

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@staff_bp.route('/application/view/<int:app_id>')
@staff_required
def view_application(app_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("SELECT * FROM leave_applications WHERE id = %s AND staff_id = %s", (app_id, session['staff_id']))
        application = cur.fetchone()

        if not application:
            flash('Application not found.', 'warning')
            return redirect(url_for('staff.staff_dashboard'))

        return render_template('staff/view_application.html', application=application)

    except Exception as e:
        print(f"🔥 Error in view_application: {str(e)}")  # <== Add this line for debugging
        flash('An error occurred while loading the application.', 'danger')
        return redirect(url_for('staff.staff_dashboard'))

    finally:
        cur.close()
        conn.close()

from flask import send_from_directory, abort
import os

@staff_bp.route('/download/<filename>')
@staff_required
def download_file(filename):
    try:
        # ✅ Prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            abort(404)

        uploads_folder = os.path.join(current_app.static_folder, 'uploads')
        file_path = os.path.join(uploads_folder, filename)

        if not os.path.exists(file_path):
            abort(404)

        return send_from_directory(uploads_folder, filename, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        abort(404)


@staff_bp.route('/application/review', methods=['GET', 'POST'])
@staff_required
def preview_application():
    def parse_date_safe(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        except Exception:
            try:
                return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S GMT').date() if date_str else None
            except Exception:
                return None

    if request.method == 'POST':
        try:
            form_data = {
                'name': session.get('staff_name', ''),
                'pno': session.get('staff_pno', ''),
                'designation': request.form.get('designation', '').strip(),
                'leave_days': request.form.get('leave_days', ''),
                'start_date': request.form.get('start_date'),
                'end_date': request.form.get('end_date'),
                'contact_address': request.form.get('contact_address', '').strip(),
                'contact_tel': request.form.get('contact_tel', '').strip(),
                'leave_type': request.form.get('leave_type', '').strip(),
                'delegate': request.form.get('delegate', '').strip(),
                'staff_id': session.get('staff_id'),
                'salary_continue': request.form.get('salary_option', 'continue') == 'continue',
                'salary_address': request.form.get('salary_address', '').strip(),
                'last_leave_start': request.form.get('last_leave_start'),
                'last_leave_end': request.form.get('last_leave_end'),
                'salary_option': request.form.get('salary_option', 'continue')
            }

            # ✅ File upload
            uploaded_file = request.files.get('supporting_doc')
            file_path = None
            original_filename = None
            if uploaded_file and uploaded_file.filename:
                if not allowed_file(uploaded_file.filename):
                    flash("Invalid file type. Allowed: PDF, Word, JPG, PNG", "danger")
                    return redirect(url_for('staff.create_application'))

                uploads_dir = os.path.join(current_app.static_folder, 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)

                original_filename = secure_filename(uploaded_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                file_path = os.path.join('uploads', unique_filename)
                uploaded_file.save(os.path.join(current_app.static_folder, file_path))

            # Store in session
            session['preview_form_data'] = form_data
            session['preview_file_path'] = file_path
            session['preview_original_filename'] = original_filename

            return redirect(url_for('staff.preview_application'))

        except Exception as e:
            current_app.logger.error(f"Preview POST error: {str(e)}", exc_info=True)
            flash("An error occurred while processing your preview.", "danger")
            return redirect(url_for('staff.create_application'))

    else:
        try:
            form_data = session.get('preview_form_data')
            if not form_data:
                flash('Session expired. Please refill the form.', 'danger')
                return redirect(url_for('staff.create_application'))

            # Convert date fields back to date objects if they’re strings
            for field in ['start_date', 'end_date', 'last_leave_start', 'last_leave_end']:
                form_data[field] = parse_date_safe(form_data.get(field))

            file_path = session.get('preview_file_path')
            original_filename = session.get('preview_original_filename')

            # Check file exists
            if file_path:
                full_path = os.path.join(current_app.static_folder, file_path)
                if not os.path.exists(full_path):
                    current_app.logger.warning(f"File not found: {full_path}")
                    file_path = None
                    original_filename = None

            return render_template(
                'staff/review_application.html',
                form_data=form_data,
                file_path=file_path,
                original_filename=original_filename
            )

        except Exception as e:
            current_app.logger.error(f"Preview GET error: {str(e)}", exc_info=True)
            flash("An error occurred while loading the preview.", "danger")
            return redirect(url_for('staff.create_application'))
