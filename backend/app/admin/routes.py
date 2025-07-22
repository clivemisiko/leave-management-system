from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.security import check_password_hash
from weasyprint import HTML
from backend.app.extensions import get_mysql_connection, mail, pymysql
from backend.app.utils.audit import log_action
from backend.app.utils.email import send_email
import os
from functools import wraps
from datetime import datetime
import base64
import pandas as pd
from flask import make_response
import pymysql
from flask import send_from_directory, abort
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# --- Helpers ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login as admin', 'danger')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)

    return decorated_function


def get_signature_base64():
    try:
        # Dynamically get full path
        signature_path = os.path.join(
            os.path.dirname(__file__), '..', 'static', 'images', 'signature.png'
        )
        signature_path = os.path.abspath(signature_path)
        print("🔍 Looking for signature at:", signature_path)

        with open(signature_path, "rb") as image_file:
            return "data:image/png;base64," + base64.b64encode(image_file.read()).decode('utf-8')

    except Exception as e:
        print("❌ Signature load failed:", e)
        return None


# --- Login/Logout ---
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    # Check for logout success message first
    if session.pop('logout_success', None):
        flash('You have been logged out successfully', 'success')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM admin WHERE username = %s", (username,))
            admin = cur.fetchone()
            cur.close()

            if not admin:
                flash('Username not found', 'danger')
                return render_template('admin/login.html')

            if check_password_hash(admin['password'], password):
                session.clear()  # Clear any existing session
                session['admin_logged_in'] = True
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session['last_login'] = datetime.now().strftime('%b %d, %Y %I:%M %p')
                session['login_success'] = True
                return redirect(url_for('admin.admin_dashboard'))

            flash('Invalid password', 'danger')

        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.clear()  # Clear the session first
    session['logout_success'] = True  # Set the flag after clearing
    return redirect(url_for('admin.admin_login'))


# --- View Staff Members ---

@admin_bp.route('/staff-members')
@admin_required
def view_staff_members():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM staff ORDER BY date_created DESC")
        staff_list = cur.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error fetching staff members: {e}")
        flash("Could not load staff members.", "danger")
        staff_list = []
    finally:
        cur.close()
        conn.close()

    return render_template('admin/staff_members.html', staff_list=staff_list)


# --- Delete Staff Member ---

@admin_bp.route('/delete-staff/<int:staff_id>', methods=['POST'])
@admin_required
def delete_staff_user(staff_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Confirm staff exists
        cur.execute("SELECT * FROM staff WHERE id = %s", (staff_id,))
        staff = cur.fetchone()
        if not staff:
            flash("Staff member not found.", "danger")
            return redirect(url_for('admin.view_staff_members'))

        # Check for pending/approved applications
        cur.execute("""
            SELECT COUNT(*) AS count FROM leave_applications 
            WHERE staff_id = %s AND status IN ('pending', 'approved')
        """, (staff_id,))
        result = cur.fetchone()
        if result and result['count'] > 0:
            flash("Cannot delete staff with pending or approved applications.", "warning")
            return redirect(url_for('admin.view_staff_members'))

        # ✅ Step 1: Delete related applications first
        cur.execute("DELETE FROM leave_applications WHERE staff_id = %s", (staff_id,))

        # ✅ Step 2: Delete the staff record
        cur.execute("DELETE FROM staff WHERE id = %s", (staff_id,))
        conn.commit()

        flash("Staff and their applications deleted successfully.", "success")

    except Exception as e:
        error_message = f"Error deleting staff: {str(e)}"
        current_app.logger.error(error_message)
        flash(error_message, "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin.view_staff_members'))


# Other routes like dashboard, application CRUD, approve/reject, PDF generation continue below...
@admin_bp.route('/application/new', methods=['GET', 'POST'])
@admin_required
def create_application():
    if request.method == 'POST':
        try:
            def parse_date(date_str):
                return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

            start_date = parse_date(request.form.get('start_date', ''))
            end_date = parse_date(request.form.get('end_date', ''))
            last_leave_start = parse_date(request.form.get('last_leave_start', ''))
            last_leave_end = parse_date(request.form.get('last_leave_end', ''))

            salary_continue = request.form.get('salary_option', 'continue') == 'continue'
            salary_address = request.form.get('salary_address', '') if not salary_continue else None

            leave_balance_raw = request.form.get('leave_balance', '')
            leave_balance = int(leave_balance_raw) if leave_balance_raw.isdigit() else 0

            # Try to fetch staff ID (optional)
            conn = get_mysql_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT id FROM staff WHERE pno = %s", (request.form['pno'],))
            staff_row = cur.fetchone()
            staff_id = staff_row['id'] if staff_row else None  # NULL if staff doesn't exist

            # Prepare data
            form_data = {
                'staff_id': staff_id,
                'name': request.form['name'],
                'pno': request.form['pno'],
                'designation': request.form['designation'],
                'leave_days': int(request.form['leave_days']),
                'start_date': start_date,
                'end_date': end_date,
                'contact_address': request.form['contact_address'],
                'contact_tel': request.form['contact_tel'],
                'salary_continue': salary_continue,
                'salary_address': salary_address,
                'delegate': request.form.get('delegate', '').strip(),
                'outside_country': 1 if 'outside_country' in request.form else 0,
                'leave_balance': leave_balance,
                'last_leave_start': last_leave_start,
                'last_leave_end': last_leave_end,
                'leave_type': request.form['leave_type']
            }

            if not all([form_data['name'], form_data['pno'], form_data['designation'], form_data['start_date'],
                        form_data['end_date']]):
                flash('Please fill all required fields', 'danger')
                return redirect(url_for('admin.create_application'))

            if not salary_continue and not salary_address:
                flash('Payment address is required when not continuing bank payments', 'danger')
                return redirect(url_for('admin.create_application'))

            # Insert into DB
            cur.execute("""
                INSERT INTO leave_applications 
                (staff_id, name, pno, designation, leave_days, start_date, end_date, 
                 contact_address, contact_tel, salary_continue, salary_address,
                 delegate, outside_country, leave_balance, last_leave_start, last_leave_end, leave_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(form_data.values()))

            conn.commit()
            flash('Application created successfully', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return redirect(url_for('admin.create_application'))
        except Exception as e:
            flash(f'Error creating application: {str(e)}', 'danger')
            return redirect(url_for('admin.create_application'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    return render_template('admin/create_application.html')


@admin_bp.route('/dashboard')
@admin_bp.route('/dashboard/<status_filter>')
@admin_required
def admin_dashboard(status_filter=None):
    # Only flash if redirected with success flag
    if session.pop('login_success', None):
        flash('Login successful', 'success')

    conn = get_mysql_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Base query with improved selection
    base_query = """
    SELECT 
        la.id,
        COALESCE(s.username, la.name) AS name,
        COALESCE(s.pno, la.pno) AS pno,
        la.designation,
        la.leave_days,
        la.start_date,
        la.end_date,
        DATEDIFF(la.end_date, la.start_date) + 1 AS calendar_days,
        la.status,
        la.leave_type,
        la.approved_by,
        la.approved_at,
        la.rejected_by,
        la.rejected_at,
        la.created_at,
        la.supporting_doc,
        s.id AS staff_id,
        s.leave_balance
    FROM leave_applications la
    LEFT JOIN staff s ON la.staff_id = s.id
    """

    # Get filter parameters
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip().lower()
    leave_type_filter = request.args.get('leave_type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    params = []
    conditions = []

    # Status filter
    if status_filter in ['approved', 'rejected', 'pending']:
        conditions.append("la.status = %s")
        params.append(status_filter)

    # Search filter
    if search:
        conditions.append("""
            (COALESCE(s.username, la.name) LIKE %s 
            OR COALESCE(s.pno, la.pno) LIKE %s
            OR la.leave_type LIKE %s
            OR la.designation LIKE %s)
        """)
        params.extend([f"%{search}%"] * 4)

    # Leave type filter
    if leave_type_filter:
        conditions.append("la.leave_type = %s")
        params.append(leave_type_filter)

    # Date range filter
    if date_from:
        try:
            datetime.strptime(date_from, '%Y-%m-%d')
            conditions.append("la.start_date >= %s")
            params.append(date_from)
        except ValueError:
            flash('Invalid start date format', 'warning')

    if date_to:
        try:
            datetime.strptime(date_to, '%Y-%m-%d')
            conditions.append("la.end_date <= %s")
            params.append(date_to)
        except ValueError:
            flash('Invalid end date format', 'warning')

    # Build final query
    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions) + " ORDER BY la.created_at DESC"
    else:
        query = base_query + " ORDER BY la.created_at DESC"

    # Execute applications query
    cur.execute(query, tuple(params))
    applications = cur.fetchall()

    # Enhance application data with calculated values
    for app in applications:
        # Calculate working days if not properly stored (backward compatibility)
        if not app['leave_days'] and app['start_date'] and app['end_date']:
            delta = app['end_date'] - app['start_date']
            total_days = delta.days + 1
            working_days = 0
            for n in range(total_days):
                current_day = app['start_date'] + timedelta(days=n)
                if current_day.weekday() < 5:  # 0-4 = Monday-Friday
                    working_days += 1
            app['leave_days'] = working_days

        # Format dates for display
        for date_field in ['start_date', 'end_date', 'approved_at', 'rejected_at', 'created_at']:
            if app.get(date_field):
                app[f'{date_field}_formatted'] = app[date_field].strftime('%b %d, %Y %I:%M %p')

    # Get staff list with leave balances
    cur.execute("""
        SELECT id, username, pno, designation, leave_balance, 
               email, date_created 
        FROM staff 
        ORDER BY username ASC
    """)
    staff_list = cur.fetchall()

    # Get status counts for summary cards
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
        FROM leave_applications
    """)
    status_counts = cur.fetchone()

    # Get leave type distribution
    cur.execute("""
        SELECT leave_type, COUNT(*) as count 
        FROM leave_applications 
        GROUP BY leave_type 
        ORDER BY count DESC
    """)
    leave_types = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'admin/dashboard.html',
        applications=applications,
        staff_list=staff_list,
        status_counts=status_counts,
        leave_types=leave_types,
        current_filters={
            'status': status_filter,
            'search': search,
            'leave_type': leave_type_filter,
            'date_from': date_from,
            'date_to': date_to
        }
    )


@admin_bp.route('/application/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_application(id):
    conn = get_mysql_connection()
    cur = conn.cursor()
    conn.commit()
    conn.rollback()

    if request.method == 'POST':
        # Update the leave application with the submitted form data
        cur.execute("""
            UPDATE leave_applications SET 
                name = %s, 
                pno = %s, 
                designation = %s, 
                leave_days = %s, 
                start_date = %s, 
                end_date = %s, 
                contact_address = %s, 
                contact_tel = %s, 
                status = %s
            WHERE id = %s
        """, (
            request.form['name'],
            request.form['pno'],
            request.form['designation'],
            request.form['leave_days'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['contact_address'],
            request.form['contact_tel'],
            request.form['status'],
            id
        ))
        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()

        cur.close()

        flash('Application updated successfully', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    # Fetch application for display
    cur.execute("""
    SELECT 
    la.*, 
    CASE 
        WHEN s.username IS NOT NULL THEN s.username 
        ELSE la.name 
    END AS display_name,
    CASE 
        WHEN s.pno IS NOT NULL THEN s.pno 
        ELSE la.pno 
    END AS display_pno
FROM leave_applications la
LEFT JOIN staff s ON la.staff_id = s.id
WHERE la.id = %s

""", (id,))

    application = cur.fetchone()
    cur.close()

    if not application:
        flash('Application not found', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin/edit_application.html', application=application)


@admin_bp.route('/application/delete/<int:id>', methods=['POST'])
@admin_required
def delete_application(id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM leave_applications")
        data = cur.fetchall()

        cur.execute("DELETE FROM leave_applications WHERE id = %s", (id,))
        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()

        cur.close()
        flash('Application deleted successfully', 'success')
    except Exception as e:
        conn = get_mysql_connection()
        cur = conn.cursor()
        conn.commit()
        conn.rollback()
        flash('Failed to delete application', 'danger')
        # Log the error: current_app.logger.error(f"Delete error: {str(e)}")
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/approve/<int:app_id>', methods=['GET', 'POST'])
@admin_required
def approve_application(app_id):
    conn = get_mysql_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        approval_comments = request.form.get('approval_comments', '').strip()

        try:
            # ✅ Fetch application details
            cur.execute("SELECT * FROM leave_applications WHERE id = %s", (app_id,))
            application = cur.fetchone()
            if not application:
                flash('Application not found', 'danger')
                return redirect(url_for('admin.admin_dashboard'))

            if application['status'] == 'approved':
                flash('Application already approved', 'info')
                return redirect(url_for('admin.admin_dashboard'))

            staff_id = application['staff_id']
            leave_days = application['leave_days']
            leave_type = application['leave_type']

            # ✅ Fetch staff leave balance, email, name
            cur.execute("SELECT leave_balance, email, username FROM staff WHERE id = %s FOR UPDATE", (staff_id,))
            staff = cur.fetchone()
            if not staff:
                flash('Staff not found', 'danger')
                return redirect(url_for('admin.admin_dashboard'))

            # ✅ Check and deduct only if Annual leave
            if leave_type == 'Annual':
                if staff['leave_balance'] < leave_days:
                    flash('Insufficient annual leave balance', 'warning')
                    return redirect(url_for('admin.admin_dashboard'))

                cur.execute("""
                    UPDATE staff 
                    SET leave_balance = leave_balance - %s 
                    WHERE id = %s
                """, (leave_days, staff_id))

            # ✅ Approve leave
            cur.execute("""
                UPDATE leave_applications 
                SET status = 'approved', approved_at = NOW(), approved_by = %s, approval_comments = %s
                WHERE id = %s
            """, (session['admin_username'], approval_comments, app_id))

            conn.commit()

            # ✅ Log & Notify
            log_action(f"Admin {session['admin_username']} approved leave ID {app_id}",
                       admin_username=session['admin_username'])

            send_email(
                subject="Leave Approved",
                recipients=[staff['email']],
                body=f"Hello {staff['username']},\n\nYour {leave_type} leave request has been approved. Kindly login and print your leave form."
            )

            flash(f'{leave_type} leave approved successfully.', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Approval failed: {str(e)}", exc_info=True)
            flash(f'Error during approval: {str(e)}', 'danger')

        finally:
            cur.close()

    # Render approval form
    cur.execute("SELECT * FROM leave_applications WHERE id = %s", (app_id,))
    app = cur.fetchone()
    cur.close()

    return render_template('admin/approve_form.html', app=app)


@admin_bp.route('/application/reject/<int:id>', methods=['GET', 'POST'])
@admin_required
def reject_application(id):
    if request.method == 'POST':
        try:
            rejection_reason = request.form.get('rejection_reason', '').strip()
            if not rejection_reason:
                flash('Please provide a rejection reason', 'danger')
                return redirect(url_for('admin.reject_application', id=id))

            conn = get_mysql_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)

            # Fetch application and staff info
            cur.execute("""
                SELECT la.*, s.email, s.username 
                FROM leave_applications la
                LEFT JOIN staff s ON la.staff_id = s.id
                WHERE la.id = %s AND la.status = 'pending'
            """, (id,))
            application = cur.fetchone()

            if not application:
                flash('Application not found or already processed', 'danger')
                return redirect(url_for('admin.admin_dashboard'))

            # Update application with rejection details
            cur.execute("""
                UPDATE leave_applications SET 
                    status = 'rejected',
                    rejected_by = %s,
                    rejected_at = NOW(),
                    rejection_reason = %s
                WHERE id = %s
            """, (session['admin_username'], rejection_reason, id))

            conn.commit()

            # Send email notification if staff exists
            if application.get('email'):
                send_email(
                    subject="Leave Application Rejected",
                    recipients=[application['email']],
                    body=f"""Hello {application['username']},

Your leave application from {application['start_date']} to {application['end_date']} 
has been rejected.

Reason: {rejection_reason}

Please contact HR if you have any questions.
"""
                )

            flash('Application rejected with reason sent to staff', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        except Exception as e:
            conn.rollback()
            current_app.logger.error(f"Rejection error: {str(e)}")
            flash(f'Error rejecting application: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_dashboard'))
        finally:
            if 'cur' in locals():
                cur.close()

    # GET request - show rejection form
    return render_template('admin/reject_application.html', application_id=id)


@admin_bp.route('/application/print/<int:app_id>')
@admin_required
def print_application(app_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Fetch the application and related staff info
        cur.execute("""
            SELECT 
                la.*,
                COALESCE(s.username, la.name) AS name,
                COALESCE(s.pno, la.pno) AS pno,
                s.leave_balance,
                s.designation AS staff_designation,
                CASE
                    WHEN la.designation LIKE '%%HOD%%' OR la.designation LIKE '%%Head%%'
                    THEN 1 ELSE 0
                END AS is_hod
            FROM leave_applications la
            LEFT JOIN staff s ON la.staff_id = s.id
            WHERE la.id = %s
        """, (app_id,))
        application = cur.fetchone()

        if not application:
            flash("Application not found.", "danger")
            return redirect(url_for('admin.admin_dashboard'))

        if application['status'] != 'approved':
            flash("You can only print approved leave applications.", "warning")
            return redirect(url_for('admin.admin_dashboard'))

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
        if leave_info['track_usage'] and application.get('staff_id'):
            cur.execute("""
                SELECT SUM(leave_days) AS used_days
                FROM leave_applications
                WHERE staff_id = %s AND leave_type = %s AND status = 'approved'
            """, (application['staff_id'], leave_type))
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
            # For untracked leave types or external applicants
            application['max_days'] = None
            application['used_days'] = None
            application['remaining_days'] = None
            application['balance_description'] = "No entitlement tracking for this leave type"

        # PDF rendering
        logo_base64 = current_app.get_logo_base64()
        signature_base64 = current_app.get_signature_base64()
        template = 'admin/pdf_template_hod.html' if application['is_hod'] else 'admin/pdf_template_staff.html'

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
        return redirect(url_for('admin.admin_dashboard'))

    finally:
        if cur: cur.close()
        if conn: conn.close()


@admin_bp.route('/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def delete_staff(staff_id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Step 1: Check staff exists
        cur.execute("SELECT username FROM staff WHERE id = %s", (staff_id,))
        staff = cur.fetchone()
        if not staff:
            flash('Staff not found.', 'danger')
            return redirect(url_for('admin.view_staff_members'))

        username = staff['username']

        # Step 2: Delete related leave applications
        cur.execute("DELETE FROM leave_applications WHERE staff_id = %s", (staff_id,))

        # Step 3: Delete the staff record
        cur.execute("DELETE FROM staff WHERE id = %s", (staff_id,))

        conn.commit()
        flash(f"Staff '{username}' and their applications deleted successfully.", "success")

    except Exception as e:
        conn.rollback()
        import traceback
        current_app.logger.error(f"Error deleting staff: {str(e)}\n{traceback.format_exc()}")
        flash("An error occurred while deleting the staff.", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin.view_staff_members'))


@admin_bp.route('/home')
def admin_home_redirect():
    """Redirect to either main home or admin dashboard based on auth"""
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('main.home'))


@admin_bp.route('/audit-log')
@admin_required
def view_audit_log():
    conn = get_mysql_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 100")
    logs = cur.fetchall()
    cur.close()
    return render_template('admin/audit_log.html', logs=logs)


@admin_bp.route('/export/excel')
@admin_required
def export_leave_excel():
    conn = get_mysql_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ✅ Fetch all leave applications
    cur.execute("""
        SELECT id, name, pno, designation, leave_type, leave_days, start_date, end_date, 
               status, approved_by, rejected_by, submitted_at, approved_at, rejected_at 
        FROM leave_applications ORDER BY submitted_at DESC
    """)
    data = cur.fetchall()

    if not data:
        flash('No data found to export.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    # ✅ Convert to DataFrame
    df = pd.DataFrame(data)

    # ✅ Create Excel file in memory
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='LeaveApplications')

    # ✅ Send as response
    output.seek(0)
    response = make_response(output.read())
    response.headers["Content-Disposition"] = "attachment; filename=leave_applications.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


@admin_bp.route('/download/<path:filename>')
@admin_required
def download_uploaded_document(filename):
    try:
        filename = filename.replace('\\', '/')  # 🔥 normalize Windows slashes

        # Security check - prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            abort(404)

        # Extract just the filename part (remove 'uploads/' if present)
        clean_filename = filename.split('/')[-1] if '/' in filename else filename

        uploads_folder = os.path.join(current_app.static_folder, 'uploads')
        file_path = os.path.join(uploads_folder, clean_filename)

        if not os.path.exists(file_path):
            current_app.logger.error(f"File not found: {file_path}")
            abort(404)

        return send_from_directory(uploads_folder, clean_filename, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        abort(404)