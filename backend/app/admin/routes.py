from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.security import check_password_hash
from weasyprint import HTML
from backend.app.extensions import get_mysql_connection, mail, pymysql
import os
from functools import wraps
from datetime import datetime
import base64

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

# --- Login/Logout ---

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    session.clear()
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
                session['admin_logged_in'] = True
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session['last_login'] = datetime.now().strftime('%b %d, %Y %I:%M %p')

                return redirect(url_for('admin.admin_dashboard'))
            
            else:
                flash('Invalid password', 'danger')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')

    return render_template('admin/login.html')

@admin_bp.route('/logout')
@admin_required
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin.admin_login'))

# --- View Staff Members ---

@admin_bp.route('/staff-members')
@admin_required
def view_staff_members():
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM staff")
        staff_members = cur.fetchall()
        return render_template('admin/view_staff.html', staff_list=staff_members)
    except Exception as e:
        flash(f'Error fetching staff: {e}', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

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

            form_data = {
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
                'outside_country': 'outside_country' in request.form,
                'leave_balance': leave_balance,
                'last_leave_start': last_leave_start,
                'last_leave_end': last_leave_end,
                'leave_type': request.form['leave_type']
            }

            if not all([form_data['name'], form_data['pno'], form_data['designation'], form_data['start_date'], form_data['end_date']]):
                flash('Please fill all required fields', 'danger')
                return redirect(url_for('admin.create_application'))

            if not salary_continue and not salary_address:
                flash('Payment address is required when not continuing bank payments', 'danger')
                return redirect(url_for('admin.create_application'))



            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM leave_applications")
            data = cur.fetchall()

            cur.execute("""
                INSERT INTO leave_applications 
                (name, pno, designation, leave_days, start_date, end_date, 
                 contact_address, contact_tel, salary_continue, salary_address,
                 delegate, outside_country, leave_balance, last_leave_start, last_leave_end, leave_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(form_data.values()))
            conn = get_mysql_connection()

            cur = conn.cursor()

            conn.commit()
            conn.rollback()


            flash('Application created successfully', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return redirect(url_for('admin.create_application'))
        except Exception as e:
            conn = get_mysql_connection()
            cur = conn.cursor()
            conn.commit()
            conn.rollback()

            flash(f'Error creating application: {str(e)}', 'danger')
            return redirect(url_for('admin.create_application'))
        finally:
            if 'cur' in locals():
                cur.close()

    return render_template('admin/create_application.html')

@admin_bp.route('/dashboard')
@admin_bp.route('/dashboard/<status_filter>')
@admin_required
def admin_dashboard(status_filter=None):
    if request.referrer and url_for('admin.admin_login') in request.referrer:
        flash('Login successful', 'success')

    conn = get_mysql_connection()
    cur = conn.cursor()
    conn.commit()
    conn.rollback()

    base_query = """
    SELECT 
        la.id,
        COALESCE(s.username, la.name) AS name,
        COALESCE(s.pno, la.pno) AS pno,
        la.designation,
        la.leave_days,
        la.start_date,
        la.end_date,
        la.status,
        la.leave_type,
        la.approved_by,
        la.approved_at,
        la.rejected_by,
        la.rejected_at,
        la.created_at
    FROM leave_applications la
    LEFT JOIN staff s ON la.staff_id = s.id
    """

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()

    params = []
    conditions = []

    if status_filter in ['approved', 'rejected', 'pending']:
        conditions.append("la.status = %s")
        params.append(status_filter)

    if search:
        conditions.append("(COALESCE(s.username, la.name) LIKE %s OR COALESCE(s.pno, la.pno) LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions) + " ORDER BY la.created_at DESC"
    else:
        query = base_query + " ORDER BY la.created_at DESC"

    cur.execute(query, tuple(params))
    applications = cur.fetchall()

    # ✅ Fetch staff list for the staff section
    cur.execute("SELECT * FROM staff ORDER BY id DESC")
    staff_list = cur.fetchall()

    for staff in staff_list:
        if staff.get('date_created') and isinstance(staff['date_created'], str):
            try:
                staff['date_created'] = datetime.strptime(staff['date_created'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Fallback in case time format is different
                staff['date_created'] = None

    cur.close()
    return render_template(
        'admin/dashboard.html',
        applications=applications,
        staff_list=staff_list,
        current_filter=status_filter
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

@admin_bp.route('/approve/<int:app_id>')
@admin_required
def approve_application(app_id):
    
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        conn.commit()
                
        # 1. Get application details
        cur.execute("""
            SELECT staff_id, leave_days, status 
            FROM leave_applications 
            WHERE id = %s
        """, (app_id,))
        application = cur.fetchone()
        
        if not application:
            flash('Application not found', 'danger')
            return redirect(url_for('admin.admin_dashboard'))
        
        # 2. Check if already approved
        if application['status'] == 'approved':
            flash('Application already approved', 'info')
            return redirect(url_for('admin.admin_dashboard'))
        
        # 3. Verify staff exists and has enough balance
        if application['staff_id']:
            cur.execute("""
                SELECT leave_balance FROM staff 
                WHERE id = %s FOR UPDATE
            """, (application['staff_id'],))
            staff = cur.fetchone()
            
            if not staff:
                flash('Staff record not found', 'danger')
                return redirect(url_for('admin.admin_dashboard'))
                
            if staff['leave_balance'] < application['leave_days']:
                flash('Insufficient leave balance', 'warning')
                return redirect(url_for('admin.admin_dashboard'))
        
        # 4. Process approval
        if application['staff_id']:
            cur.execute("""
                UPDATE staff 
                SET leave_balance = leave_balance - %s 
                WHERE id = %s
            """, (application['leave_days'], application['staff_id']))
        
        cur.execute("""
            UPDATE leave_applications 
            SET status = 'approved',
                approved_at = NOW(),
                approved_by = %s
            WHERE id = %s
        """, (session['admin_username'], app_id))
        
        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()


        flash('Application approved', 'success')
        
    except Exception as e:
        conn = get_mysql_connection()
        cur = conn.cursor()
        conn.commit()
        conn.rollback()

        flash(f'Approval failed: {str(e)}', 'danger')
        if current_app:  # Safety check
            current_app.logger.error(f"Approval error: {str(e)}")
        else:
            print(f"Approval error: {str(e)}")  # Fallback logging
            
    finally:
        cur.close()
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/application/reject/<int:id>')
@admin_required
def reject_application(id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM leave_applications")
        data = cur.fetchall()

        cur.execute("""
                UPDATE leave_applications SET 
            status = 'rejected',
            rejected_by = %s,
            rejected_at = %s
            WHERE id = %s AND status = 'pending'
        """, (session['admin_username'], datetime.now(), id))
        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()


        flash('Application rejected', 'warning')
    except Exception as e:
        conn = get_mysql_connection()
        cur = conn.cursor()
        conn.commit()
        flash(f'Error rejecting application: {str(e)}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/application/print/<int:id>')
@admin_required
def print_application(id):
    try:
        conn = get_mysql_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT la.*,
                   COALESCE(s.username, la.name) AS name,
                   COALESCE(s.pno, la.pno) AS pno,
                   CASE
                       WHEN la.designation LIKE '%%HOD%%' OR la.designation LIKE '%%Head%%'
                       THEN 1
                       ELSE 0
                   END AS is_hod
            FROM leave_applications la
            LEFT JOIN staff s ON la.staff_id = s.id
            WHERE la.id = %s
        """, (id,))
        application = cur.fetchone()
        cur.close()

        if not application:
            flash("Application not found.", "danger")
            return redirect(url_for('admin.admin_dashboard'))

        if application['status'] != 'approved':
            flash("Only approved applications can be printed.", "warning")
            return redirect(url_for('admin.admin_dashboard'))

        # Convert string dates to datetime objects
        date_fields = ['start_date', 'end_date', 'last_leave_start', 'last_leave_end']
        for field in date_fields:
            if application.get(field) and isinstance(application[field], str):
                try:
                    application[field] = datetime.strptime(application[field], '%Y-%m-%d').date()
                except ValueError as e:
                    current_app.logger.error(f"Date parsing error for {field}: {e}")
                    application[field] = None

        # Debug: Print application data
        current_app.logger.info(f"Application data: {application}")

        # Select template
        template_name = 'admin/pdf_template_hod.html' if application['is_hod'] else 'admin/pdf_template_staff.html'

        # Get logo
        logo_base64 = current_app.get_logo_base64()
        if not logo_base64:
            current_app.logger.warning("Logo not found or could not be loaded")

        # Generate PDF
        rendered_html = render_template(template_name, app=application, logo_base64=logo_base64)
        pdf = HTML(string=rendered_html).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=leave_application_{id}.pdf'
        return response

    except Exception as e:
        current_app.logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
        flash("Failed to generate PDF. Check logs for details.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def delete_staff(staff_id):
    conn = get_mysql_connection()
    cur = conn.cursor()
    conn.commit()
    conn.rollback()
    try:
        # Fetch staff info to confirm existence
        cur.execute("SELECT * FROM staff WHERE id = %s", (staff_id,))
        staff = cur.fetchone()

        if not staff:
            flash('Staff member not found.', 'danger')
            return redirect(url_for('admin.admin_dashboard'))

        # Delete the staff record (leave_applications will be deleted automatically)
        cur.execute("DELETE FROM staff WHERE id = %s", (staff_id,))
        conn = get_mysql_connection()

        cur = conn.cursor()

        conn.commit()
        conn.rollback()
        flash(f"Staff {staff['username']} and their applications deleted successfully.", "success")
    except Exception as e:
        conn = get_mysql_connection()
        cur = conn.cursor()
        conn.commit()
        conn.rollback()
        current_app.logger.error(f"Error deleting staff: {str(e)}")
        flash("Error deleting staff member.", "danger")
    finally:
        cur.close()

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/home')
def admin_home_redirect():
    """Redirect to either main home or admin dashboard based on auth"""
    if 'admin_logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('main.home'))