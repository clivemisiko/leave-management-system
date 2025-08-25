from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, abort, \
    send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
import os, re, uuid, base64
from werkzeug.utils import secure_filename
from collections import Counter
from email_validator import validate_email, EmailNotValidError
from backend.app.extensions import get_postgres_connection, mail, db
from backend.app.models import Staff, LeaveApplication
from backend.app.utils.email import send_email, send_reset_email
from backend.app.utils.auth import update_password
from backend.app.utils.audit import log_action
from flask_mail import Message  # Added this import
from datetime import datetime, date
from weasyprint import HTML
from psycopg2.extras import RealDictCursor
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, make_response, abort, send_from_directory,
    current_app  # Added this import
)
import uuid
from flask_mail import Message
import psycopg2

# Initialize Blueprint
staff_bp = Blueprint('staff', __name__, template_folder='templates')

# Constants
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}


# Helper Functions
def get_serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='password-reset-salt'
    )


def get_reset_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_signature_base64():
    try:
        signature_path = os.path.join(
            os.path.dirname(__file__), '..', 'static', 'images', 'signature.png'
        )
        signature_path = os.path.abspath(signature_path)
        with open(signature_path, "rb") as image_file:
            return "data:image/png;base64," + base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        current_app.logger.error(f"Signature load failed: {e}")
        return None


# Decorators
def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'staff_logged_in' not in session:
            flash('Please log in as staff to access this page.', 'danger')
            return redirect(url_for('staff.staff_login'))
        return f(*args, **kwargs)

    return decorated_function

def get_postgres_connection():
    return psycopg2.connect(
        host="nozomi.proxy.rlwy.net",
        port=45865,
        user="postgres",   # 👈 update if Railway gave different username
        password="BPfofFISBoCNEKDBjoHcDWvmVLXuotem",
        dbname="railway",
        cursor_factory=RealDictCursor
    )

# Authentication Routes
@staff_bp.route('/login', methods=['GET', 'POST'])
def staff_login():
    if session.pop('logout_success', None):
        flash('Logged out successfully', 'success')

    if request.method == 'POST':
        login_input = request.form['login_input'].strip()
        password = request.form['password']

        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if '@' in login_input:
            cur.execute("SELECT * FROM staff WHERE email = %s", (login_input,))
        else:
            cur.execute("SELECT * FROM staff WHERE pno = %s", (login_input,))

        staff = cur.fetchone()
        cur.close()
        conn.close()

        if not staff:
            flash('Invalid email or staff number', 'danger')
            return redirect(url_for('staff.staff_login'))

        if not check_password_hash(staff['password'], password):
            flash('Incorrect password', 'danger')
            return redirect(url_for('staff.staff_login'))

        if not staff['is_verified']:
            flash('Please verify your email before logging in.', 'warning')
            return redirect(url_for('staff.staff_login'))

        # ✅ Set session
        session['staff_logged_in'] = True
        session['staff_id'] = staff['id']
        session['staff_pno'] = staff['pno']
        session['staff_name'] = staff['username']
        session['staff_email'] = staff['email']
        session['staff_designation'] = staff['designation']
        session['login_success'] = True
        return redirect(url_for('staff.staff_dashboard'))

    return render_template('staff/login.html')

@staff_bp.route('/logout')
def staff_logout():
    session['logout_success'] = True
    session.clear()
    return redirect(url_for('staff.staff_login'))

@staff_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        pno = request.form.get('pno', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        designation = request.form.get('designation', '').strip()

        if not all([pno, username, email, password, confirm_password, designation]):
            flash('All fields are required including designation.', 'danger')
            return redirect(url_for('staff.register'))

        if designation not in ['Staff Member', 'HOD']:
            flash('Invalid designation selected.', 'danger')
            return redirect(url_for('staff.register'))

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('staff.register'))

        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            flash('Please enter a valid email address', 'danger')
            return redirect(url_for('staff.register'))

        conn = None
        cur = None
        try:
            conn = get_postgres_connection()
            cur = conn.cursor()

            cur.execute("SELECT id FROM staff WHERE pno = %s OR email = %s", (pno, email))
            if cur.fetchone():
                flash('P/Number or email already registered', 'danger')
                return redirect(url_for('staff.register'))

            hashed_password = generate_password_hash(password)
            verification_token = str(uuid.uuid4())

            cur.execute("""
                INSERT INTO staff (pno, username, email, password, designation, is_verified, verification_token)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (pno, username, email, hashed_password, designation, False, verification_token))
            conn.commit()

            # ✅ Send verification email
            verification_link = url_for('staff.verify_email', token=verification_token, _external=True)
            msg = Message("Verify Your Account", recipients=[email])
            msg.body = f"Hi {username},\n\nClick the link below to verify your account:\n{verification_link}"
            mail.send(msg)

            flash('Registration successful! Please check your email to verify your account.', 'info')
            return redirect(url_for('staff.staff_login'))

        except Exception as e:
            if conn:
                conn.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash(f"Registration failed: {e}", 'danger')
            return redirect(url_for('staff.register'))

        finally:
            if cur: cur.close()
            if conn: conn.close()

    return render_template('staff/register.html')



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
            conn = get_postgres_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, username FROM staff WHERE email = %s", (email,))
            staff = cur.fetchone()

            flash('If an account exists with this email, a reset link has been sent.', 'success')

            if staff:
                serializer = get_serializer()
                token = serializer.dumps(email)
                reset_url = url_for('staff.reset_password', token=token, _external=True)
                expires_at = datetime.utcnow() + timedelta(hours=1)

                cur.execute("""
                    UPDATE staff 
                    SET reset_token = %s, reset_token_expires = %s 
                    WHERE email = %s
                """, (token, expires_at, email))
                conn.commit()

                msg = Message(
                    subject='Password Reset Request',
                    recipients=[email],
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    body=f"Hi,\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you didn't request this, ignore this email."
                )
                mail.send(msg)

            return redirect(url_for('staff.staff_login'))

        except Exception as e:
            current_app.logger.error(f"Forgot password error: {e}")
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
        serializer = get_serializer()
        try:
            email = serializer.loads(token, max_age=3600)
        except:
            flash('Reset link has expired or is invalid.', 'danger')
            return redirect(url_for('staff.forgot_password'))

        conn = get_postgres_connection()
        cur = conn.cursor()

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
                return render_template('staff/reset_password.html', token=token)

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('staff/reset_password.html', token=token)

            hashed_password = generate_password_hash(password)

            cur.execute("""
                UPDATE staff 
                SET password = %s, reset_token = NULL, reset_token_expires = NULL 
                WHERE email = %s
            """, (hashed_password, email))
            conn.commit()

            flash('Your password has been reset. Please login.', 'success')
            return redirect(url_for('staff.staff_login'))

        return render_template('staff/reset_password.html', token=token)

    except Exception as e:
        current_app.logger.error(f"Password reset error: {e}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('staff.forgot_password'))
    finally:
        if 'cur' in locals():
            cur.close()


# Dashboard Routes
@staff_bp.route('/dashboard')
@staff_required
def staff_dashboard():
    staff_id = session.get('staff_id')
    if not staff_id:
        flash('Session expired. Please login again.', 'danger')
        return redirect(url_for('staff.staff_login'))

    conn = None
    cur = None
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get staff info
        cur.execute("SELECT username, pno FROM staff WHERE id = %s", (staff_id,))
        staff = cur.fetchone()
        if not staff:
            flash('Staff record not found', 'danger')
            return redirect(url_for('staff.staff_login'))

        # Define entitlements
        entitlements = {
            'Annual': 30,
            'Sick': 30,
            'Maternity': 90,
            'Paternity': 14,
            'Compassionate': 7,
            'Study': None,
            'Unpaid': None
        }

        # Get approved leaves
        cur.execute("""
            SELECT leave_type, leave_days 
            FROM leave_applications 
            WHERE staff_id = %s AND status = 'approved'
        """, (staff_id,))
        approved_leaves = cur.fetchall()

        # Calculate used days
        used_days = {}
        for row in approved_leaves:
            ltype = row['leave_type']
            days = row['leave_days'] or 0
            used_days[ltype] = used_days.get(ltype, 0) + days

        # Compute remaining
        remaining_days = {}
        for ltype, max_days in entitlements.items():
            if max_days is not None:
                remaining = max_days - used_days.get(ltype, 0)
                remaining_days[ltype] = max(remaining, 0)
            else:
                remaining_days[ltype] = 'Unlimited'

        # Define working day calculator
        from datetime import timedelta
        def calculate_working_days(start_date, end_date):
            total_days = (end_date - start_date).days + 1
            return sum(1 for d in range(total_days) if (start_date + timedelta(days=d)).weekday() < 5)

        # Fetch all applications
        cur.execute("""
            SELECT 
                id, start_date, end_date, status, leave_days,
                submitted_at, approved_at, approved_by,
                rejected_at, rejected_by, supporting_doc,
                leave_type, designation, contact_address,
                contact_tel, delegate
            FROM leave_applications 
            WHERE staff_id = %s 
            ORDER BY submitted_at DESC
        """, (staff_id,))
        leave_apps = cur.fetchall()

        applications = []
        status_counts = {'approved': 0, 'pending': 0, 'rejected': 0}

        for app in leave_apps:
            working_days = 0
            if app['start_date'] and app['end_date']:
                working_days = calculate_working_days(app['start_date'], app['end_date'])

            applications.append({
                'id': app['id'],
                'name': staff['username'],
                'pno': staff['pno'],
                'leave_type': app['leave_type'],
                'leave_days': working_days,  # ✅ Show real leave days now
                'start_date': app['start_date'],
                'end_date': app['end_date'],
                'status': app['status'],
                'submitted_at': app['submitted_at'],
                'approved_at': app.get('approved_at'),
                'approved_by': app.get('approved_by'),
                'rejected_at': app.get('rejected_at'),
                'rejected_by': app.get('rejected_by'),
                'supporting_doc': app.get('supporting_doc'),
                'designation': app.get('designation')
            })

            if app['status'] in status_counts:
                status_counts[app['status']] += 1

        return render_template(
            'staff/dashboard.html',
            applications=applications,
            total=len(applications),
            approved=status_counts['approved'],
            pending=status_counts['pending'],
            rejected=status_counts['rejected'],
            leave_balance=remaining_days.get('Annual', 0),
            remaining_leave_days=remaining_days
        )

    except Exception as e:
        current_app.logger.error(f"Error in staff_dashboard: {e}", exc_info=True)
        flash("Unexpected error occurred", "danger")
        return redirect(url_for('staff.staff_login'))
    finally:
        # ✅ Safe cleanup - check if variables exist
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

# Profile and Settings Routes
@staff_bp.route('/profile')
@staff_required
def staff_profile():
    try:
        staff_id = session.get('staff_id')
        if not staff_id:
            flash('Session expired. Please login again.', 'danger')
            return redirect(url_for('staff.staff_login'))

        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        current_app.logger.debug(f"Fetching profile for staff_id: {staff_id}")  # Debug log

        cur.execute("""
            SELECT id, username, email, pno, designation, 
                   leave_balance
            FROM staff 
            WHERE id = %s
        """, (staff_id,))

        staff = cur.fetchone()
        current_app.logger.debug(f"Retrieved staff data: {staff}")  # Debug log

        cur.close()
        conn.close()

        if not staff:
            flash('Staff profile not found', 'danger')
            return redirect(url_for('staff.staff_dashboard'))

        return render_template('staff/profile.html', staff=staff)

    except Exception as e:
        current_app.logger.error(f"Profile load error: {str(e)}", exc_info=True)
        flash('Failed to load profile data. Please try again later.', 'danger')
        return redirect(url_for('staff.staff_dashboard'))

    except Exception as e:
        current_app.logger.error(f"Profile load error: {str(e)}")
        flash('Failed to load profile data. Please try again later.', 'danger')
        return redirect(url_for('staff.staff_dashboard'))


@staff_bp.route('/change-password', methods=['GET', 'POST'])
@staff_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('staff.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('staff.change_password'))

        staff_id = session.get('staff_id')
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT password FROM staff WHERE id = %s", (staff_id,))
        staff = cur.fetchone()

        if not staff or not check_password_hash(staff['password'], current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('staff.change_password'))

        hashed_password = generate_password_hash(new_password)
        cur.execute("UPDATE staff SET password = %s WHERE id = %s", (hashed_password, staff_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('Password changed successfully', 'success')
        return redirect(url_for('staff.staff_profile'))

    return render_template('staff/change_password.html')


@staff_bp.route('/notification-settings', methods=['GET', 'POST'])
@staff_required
def notification_settings():
    staff_id = session.get('staff_id')

    if request.method == 'POST':
        email_notifications = request.form.get('email_notifications') == 'on'
        sms_notifications = request.form.get('sms_notifications') == 'on'
        leave_approvals = request.form.get('leave_approvals') == 'on'

        try:
            conn = get_postgres_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                UPDATE staff 
                SET email_notifications = %s, 
                    sms_notifications = %s, 
                    leave_approvals = %s 
                WHERE id = %s
            """, (email_notifications, sms_notifications, leave_approvals, staff_id))
            conn.commit()
            flash('Notification settings updated successfully', 'success')
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Error updating notification settings: {e}")
            flash('Failed to update notification settings', 'danger')
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
        return redirect(url_for('staff.notification_settings'))

    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT email_notifications, sms_notifications, leave_approvals 
            FROM staff 
            WHERE id = %s
        """, (staff_id,))
        settings = cur.fetchone()

        if not settings:
            settings = {
                'email_notifications': True,
                'sms_notifications': False,
                'leave_approvals': True
            }
    except Exception as e:
        current_app.logger.error(f"Error fetching notification settings: {e}")
        settings = {
            'email_notifications': True,
            'sms_notifications': False,
            'leave_approvals': True
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

    return render_template('staff/notification_settings.html', settings=settings)


# Leave Application Routes
@staff_bp.route('/application/new', methods=['GET', 'POST'])
@staff_required
def create_application():
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z").date()
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return None

    def calculate_working_days(start_date, end_date):
        if not start_date or not end_date:
            return 0
        delta = end_date - start_date
        total_days = delta.days + 1
        return sum(1 for i in range(total_days) if (start_date + timedelta(days=i)).weekday() < 5)

    leave_entitlements = {
        "Annual": {"max_days": 30, "deducts": True},
        "Sick": {"max_days": 30, "deducts": False},
        "Maternity": {"max_days": 90, "deducts": False},
        "Paternity": {"max_days": 14, "deducts": False},
        "Compassionate": {"max_days": 7, "deducts": False},
        "Study": {"max_days": None, "deducts": False},
        "Unpaid": {"max_days": None, "deducts": False}
    }

    if request.method == 'POST':
        action = request.form.get('action')
        start_date = parse_date(request.form.get('start_date'))
        end_date = parse_date(request.form.get('end_date'))
        last_leave_start = parse_date(request.form.get('last_leave_start'))
        last_leave_end = parse_date(request.form.get('last_leave_end'))
        leave_type = request.form.get('leave_type', '').strip()
        leave_days = calculate_working_days(start_date, end_date)

        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT id, email, leave_balance FROM staff WHERE id = %s", (session['staff_id'],))
        staff_row = cur.fetchone()
        if not staff_row:
            flash("Unable to fetch your staff details.", "danger")
            return redirect(url_for('staff.create_application'))

        staff_email = staff_row['email']
        current_annual_balance = staff_row['leave_balance']

        cur.execute("""
            SELECT leave_type, SUM(leave_days) AS used_days
            FROM leave_applications
            WHERE staff_id = %s AND status = 'approved'
            GROUP BY leave_type
        """, (session['staff_id'],))
        used_days = {row['leave_type']: row['used_days'] for row in cur.fetchall()}

        remaining_days = {}
        for ltype, config in leave_entitlements.items():
            if config['max_days'] is not None:
                remaining = config['max_days'] - used_days.get(ltype, 0)
                remaining_days[ltype] = max(remaining, 0)
            else:
                remaining_days[ltype] = 'Unlimited'

        if leave_type not in leave_entitlements:
            flash("Invalid leave type selected.", "danger")
            return redirect(url_for('staff.create_application'))

        leave_config = leave_entitlements[leave_type]
        max_days = leave_config['max_days']
        remaining = remaining_days.get(leave_type, 0)

        if max_days and leave_days > max_days:
            flash(f"Maximum {max_days} days allowed for {leave_type} leave", "danger")
            return redirect(url_for('staff.create_application'))

        if remaining != 'Unlimited' and leave_days > remaining:
            flash(f"You only have {remaining} days remaining for {leave_type} leave", "danger")
            return redirect(url_for('staff.create_application'))

        form_data = {
            'name': session['staff_name'],
            'pno': session['staff_pno'],
            'designation': request.form.get('designation', '').strip(),
            'leave_days': leave_days,
            'start_date': start_date,
            'end_date': end_date,
            'contact_address': request.form.get('contact_address', '').strip(),
            'contact_tel': request.form.get('contact_tel', '').strip(),
            'leave_type': leave_type,
            'delegate': request.form.get('delegate', '').strip(),
            'staff_id': session['staff_id'],
            'salary_continue': request.form.get('salary_option', 'continue') == 'continue',
            'salary_address': request.form.get('salary_address', '').strip() if request.form.get('salary_option') != 'continue' else None,
            'last_leave_start': last_leave_start,
            'last_leave_end': last_leave_end,
            'leave_balance': current_annual_balance if leave_config['deducts'] else None
        }

        required_fields = ['designation', 'leave_days', 'start_date', 'end_date', 'contact_address', 'contact_tel']
        if not all(form_data[field] for field in required_fields):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('staff.create_application'))

        if not form_data['salary_continue'] and not form_data['salary_address']:
            flash('Alternate payment address is required.', 'danger')
            return redirect(url_for('staff.create_application'))

        # File upload
        uploaded_file = request.files.get('supporting_doc')
        supporting_doc_path = None
        if uploaded_file and uploaded_file.filename != '':
            if not allowed_file(uploaded_file.filename):
                flash("Invalid file type. Allowed: PDF, Word, JPG, PNG", "danger")
                return redirect(url_for('staff.create_application'))

            uploads_folder = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(uploads_folder, exist_ok=True)
            unique_filename = f"{uuid.uuid4().hex}_{secure_filename(uploaded_file.filename)}"
            uploaded_file.save(os.path.join(uploads_folder, unique_filename))
            supporting_doc_path = f"uploads/{unique_filename}"
            current_app.logger.info(f"[DEBUG] Uploaded file received: {uploaded_file.filename}")
            current_app.logger.info(f"[DEBUG] File saved at: {os.path.join(uploads_folder, unique_filename)}")
            current_app.logger.info(f"[DEBUG] DB path set as: {supporting_doc_path}")
        else:
            current_app.logger.warning("[DEBUG] No supporting document uploaded.")

        if action == 'review':
            session['preview_form_data'] = form_data
            session['preview_file_path'] = supporting_doc_path
            session['preview_original_filename'] = uploaded_file.filename if uploaded_file else None
            return redirect(url_for('staff.preview_application'))

        elif action == 'submit':
            try:
                # Reuse preview file path if no new file uploaded
                if not supporting_doc_path and session.get('preview_file_path'):
                    supporting_doc_path = session['preview_file_path']
                    current_app.logger.info(f"[DEBUG] Using preview file path: {supporting_doc_path}")

                current_app.logger.info(
                    f"[DEBUG] Inserting application with supporting_doc_path={supporting_doc_path}"
                )

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
                    form_data['last_leave_end'], form_data['leave_balance'], supporting_doc_path
                ))

                if leave_config['deducts']:
                    cur.execute("""
                        UPDATE staff 
                        SET leave_balance = leave_balance - %s 
                        WHERE id = %s
                    """, (leave_days, session['staff_id']))

                conn.commit()
                log_action(f"{form_data['name']} submitted a leave application", staff_id=form_data['staff_id'])

                send_email(
                    subject="Leave Application Submitted",
                    recipients=[staff_email],
                    body=f"Hello {form_data['name']},\n\nYour {leave_type} leave application for {leave_days} days has been submitted successfully."
                )

                send_email(
                    subject="New Leave Application Submitted",
                    recipients=["clivebillzerean@gmail.com"],
                    body=f"{form_data['name']} ({form_data['pno']}) has submitted a new {leave_type} leave application."
                )

                flash('Leave application submitted successfully.', 'success')
                return redirect(url_for('staff.staff_dashboard'))

            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"Application submission error: {str(e)}", exc_info=True)
                flash(f'Error submitting application: {str(e)}', 'danger')
                return redirect(url_for('staff.create_application'))
            finally:
                cur.close()
                conn.close()

    # GET: Load form with balances
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT leave_type, SUM(leave_days) AS used_days
            FROM leave_applications
            WHERE staff_id = %s AND status = 'approved'
            GROUP BY leave_type
        """, (session['staff_id'],))
        used_days = {row['leave_type']: row['used_days'] for row in cur.fetchall()}

        remaining_days = {}
        for ltype, config in leave_entitlements.items():
            if config['max_days'] is not None:
                remaining = config['max_days'] - used_days.get(ltype, 0)
                remaining_days[ltype] = max(remaining, 0)
            else:
                remaining_days[ltype] = 'Unlimited'

        cur.execute("SELECT leave_balance FROM staff WHERE id = %s", (session['staff_id'],))
        remaining_days['Annual'] = cur.fetchone()['leave_balance']

        return render_template(
            'staff/create_application.html',
            leave_balances=remaining_days,
            leave_entitlements=leave_entitlements
        )

    except Exception as e:
        current_app.logger.error(f"Error loading application form: {str(e)}", exc_info=True)
        flash("Error loading application form. Please try again.", "danger")
        return redirect(url_for('staff.staff_dashboard'))
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()


@staff_bp.route('/application/review', methods=['GET'])
@staff_required
def preview_application():
    def ensure_date_object(date_value):
        if not date_value:
            return None
        if isinstance(date_value, date):
            return date_value
        for fmt in ['%Y-%m-%d', '%a, %d %b %Y %H:%M:%S GMT', '%b %d, %Y']:
            try:
                return datetime.strptime(date_value, fmt).date()
            except (ValueError, TypeError):
                continue
        return None

    try:
        form_data = session.get('preview_form_data')
        if not form_data:
            flash('Preview session expired. Please refill the form.', 'warning')
            return redirect(url_for('staff.create_application'))

        # Format date fields
        for key in ['start_date', 'end_date', 'last_leave_start', 'last_leave_end']:
            raw_value = form_data.get(key)
            parsed_date = ensure_date_object(raw_value)
            form_data[f'{key}_formatted'] = parsed_date.strftime('%b %d, %Y') if parsed_date else 'N/A'

        # File info
        file_path = session.get('preview_file_path')
        original_filename = session.get('preview_original_filename')

        # Confirm file exists
        full_file_path = os.path.join(current_app.static_folder, file_path) if file_path else None
        if file_path and not os.path.isfile(full_file_path):
            current_app.logger.warning(f"[Preview] File missing: {full_file_path}")
            file_path = None
            original_filename = None

        return render_template(
            'staff/review_application.html',
            form_data=form_data,
            file_path=file_path,
            original_filename=original_filename
        )

    except Exception as e:
        current_app.logger.error(f"Preview load error: {str(e)}", exc_info=True)
        flash('Unable to load preview. Please try again.', 'danger')
        return redirect(url_for('staff.create_application'))

@staff_bp.route('/application/view/<int:app_id>')
@staff_required
def view_application(app_id):
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM leave_applications WHERE id = %s AND staff_id = %s", (app_id, session['staff_id']))
        application = cur.fetchone()

        if not application:
            flash('Application not found.', 'warning')
            return redirect(url_for('staff.staff_dashboard'))

        return render_template('staff/view_application.html', application=application)

    except Exception as e:
        current_app.logger.error(f"Error in view_application: {str(e)}")
        flash('An error occurred while loading the application.', 'danger')
        return redirect(url_for('staff.staff_dashboard'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


@staff_bp.route('/application/print/<int:app_id>')
@staff_required
def print_application(app_id):
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Fetch the application and related staff info
        cur.execute("""
            SELECT 
                la.*,
                s.leave_balance,
                s.designation AS staff_designation,
                CASE
                    WHEN la.designation LIKE '%%HOD%%' OR s.designation LIKE '%%Head%%'
                    THEN 1 ELSE 0
                END AS is_hod
            FROM leave_applications la
            JOIN staff s ON la.staff_id = s.id
            WHERE la.id = %s AND la.staff_id = %s
        """, (app_id, session['staff_id']))
        application = cur.fetchone()

        if not application:
            flash("Application not found or unauthorized.", "danger")
            return redirect(url_for('staff.staff_dashboard'))

        if application['status'] != 'approved':
            flash("You can only print approved leave applications.", "warning")
            return redirect(url_for('staff.staff_dashboard'))

        # Convert date strings to date objects if necessary
        for field in ['start_date', 'end_date', 'last_leave_start', 'last_leave_end']:
            if application.get(field) and isinstance(application[field], str):
                try:
                    application[field] = datetime.strptime(application[field], '%Y-%m-%d').date()
                except:
                    application[field] = None

        leave_type = application.get('leave_type')
        leave_days = application.get('leave_days', 0)

        # Leave entitlement definitions
        entitlement_map = {
            "Annual": {"max_days": 30, "deducts": True, "track_usage": True},
            "Maternity": {"max_days": 90, "deducts": False, "track_usage": True},
            "Paternity": {"max_days": 14, "deducts": False, "track_usage": True},
            "Compassionate": {"max_days": 7, "deducts": False, "track_usage": True},
            "Sick": {"max_days": 30, "deducts": False, "track_usage": True},
            "Study": {"max_days": None, "deducts": False, "track_usage": False},
            "Unpaid": {"max_days": None, "deducts": False, "track_usage": False}
        }

        leave_info = entitlement_map.get(leave_type, {"max_days": None, "deducts": False, "track_usage": False})

        # Calculate usage for all tracked leave types
        if leave_info['track_usage']:
            cur.execute("""
                SELECT SUM(leave_days) AS used_days
                FROM leave_applications
                WHERE staff_id = %s AND leave_type = %s AND status = 'approved'
            """, (session['staff_id'], leave_type))
            used = cur.fetchone()
            used_days = used['used_days'] or 0

            entitlement = leave_info['max_days']
            remaining = entitlement - used_days if entitlement else None

            application['max_days'] = entitlement
            application['used_days'] = used_days
            application['remaining_days'] = remaining
            
            if leave_info['deducts']:
                # For annual leave, show both annual balance and entitlement usage
                application['balance_description'] = (
                    f"Annual leave balance: {application['leave_balance']} days (out of {entitlement})\n"
                    f"Used this year: {used_days} days, Remaining entitlement: {remaining} days"
                )
            else:
                # For other tracked leave types
                application['balance_description'] = (
                    f"{leave_type} leave entitlement: {entitlement} days\n"
                    f"Used: {used_days} days, Remaining: {remaining} days"
                )
        else:
            # For untracked leave types
            application['max_days'] = None
            application['used_days'] = None
            application['remaining_days'] = None
            application['balance_description'] = "No entitlement tracking for this leave type"

        # PDF rendering
        logo_base64 = current_app.get_logo_base64()
        signature_base64 = current_app.get_signature_base64()
        template = 'staff/pdf_template_hod.html' if application['is_hod'] else 'staff/pdf_template_staff.html'

        rendered = render_template(
            template,
            app=application,
            logo_base64=logo_base64,
            signature_base64=signature_base64
        )
        pdf = HTML(string=rendered, base_url=request.url_root).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=leave_application_{app_id}.pdf'
        return response

    except Exception as e:
        current_app.logger.error(f"PDF generation error: {e}", exc_info=True)
        flash("Failed to generate PDF. Try again later.", "danger")
        return redirect(url_for('staff.staff_dashboard'))

    finally:
        if cur: cur.close()
        if conn: conn.close()


@staff_bp.route('/application/cancel/<int:id>')
@staff_required
def cancel_application(id):
    staff_id = session.get('staff_id')
    conn = None
    cur = None
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()

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

        cur.execute("UPDATE staff SET leave_balance = leave_balance + %s WHERE id = %s", (app['leave_days'], staff_id))

        cur.execute("""
            UPDATE leave_applications 
            SET status = 'cancelled' 
            WHERE id = %s
        """, (id,))

        conn.commit()
        flash('Application cancelled and balance restored.', 'success')

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error cancelling application: {str(e)}', 'danger')
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return redirect(url_for('staff.staff_dashboard'))


@staff_bp.route('/download/<filename>')
@staff_required
def download_file(filename):
    try:
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

@staff_bp.route('/verify/<token>')
def verify_email(token):
    conn = None
    cur = None
    
    try:
        conn = get_postgres_connection()
        # Use psycopg2's DictCursor, not pymysql's
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Check if token exists and account is not already verified
        cur.execute("""
            SELECT id FROM staff 
            WHERE verification_token = %s AND is_verified = FALSE
        """, (token,))
        result = cur.fetchone()

        if result:
            staff_id = result['id']
            # Mark account as verified and clear the token
            cur.execute("""
                UPDATE staff 
                SET is_verified = TRUE, verification_token = NULL 
                WHERE id = %s
            """, (staff_id,))
            conn.commit()
            flash("Account verified successfully! You may now log in.", "success")
        else:
            # Check if token exists but account is already verified
            cur.execute("""
                SELECT id FROM staff 
                WHERE verification_token = %s AND is_verified = TRUE
            """, (token,))
            if cur.fetchone():
                flash("Account already verified. Please log in.", "info")
            else:
                flash("Invalid or expired verification link.", "danger")

    except Exception as e:
        current_app.logger.error(f"Verification error: {e}", exc_info=True)
        flash("An error occurred during verification. Please try again.", "danger")
        if conn:
            conn.rollback()

    finally:
        # Safe cleanup
        if 'cur' in locals() and cur:
            try:
                cur.close()
            except:
                pass
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except:
                pass
    
    return redirect(url_for('staff.staff_login'))