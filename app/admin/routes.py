from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from weasyprint import HTML, CSS
from app.extensions import mysql  # ✅ use the correct extension import
import MySQLdb.cursors
import os
from functools import wraps
from datetime import datetime
#from ..services.notification_service import send_leave_notification
import base64
import os

def get_logo_base64():
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'gov_logo.png')  # Adjust path if needed
    with open(logo_path, 'rb') as logo_file:
        encoded_logo = base64.b64encode(logo_file.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded_logo}"

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Your routes will follow here...

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login as admin', 'danger')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor
            cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
            admin = cur.fetchone()
            cur.close()

            if not admin:
                flash('Username not found', 'danger')
                return render_template('admin/login.html')

            # Access columns by name instead of index
            if check_password_hash(admin['password'], password):
                session['admin_logged_in'] = True
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                return redirect(url_for('admin.admin_dashboard'))  # Fixed endpoint name
            else:
                flash('Invalid password', 'danger')

        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
            # Consider logging the error: current_app.logger.error(str(e))

    return render_template('admin/login.html')

@admin_bp.route('/logout')
@admin_required
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin.admin_login'))


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

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO leave_applications 
                (name, pno, designation, leave_days, start_date, end_date, 
                 contact_address, contact_tel, salary_continue, salary_address,
                 delegate, outside_country, leave_balance, last_leave_start, last_leave_end, leave_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(form_data.values()))
            mysql.connection.commit()
            flash('Application created successfully', 'success')
            return redirect(url_for('admin.admin_dashboard'))

        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return redirect(url_for('admin.create_application'))
        except Exception as e:
            mysql.connection.rollback()
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

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

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
        conditions.append("status = %s")
        params.append(status_filter)

    if search:
        conditions.append("(COALESCE(s.username, la.name) LIKE %s OR COALESCE(s.pno, la.pno) LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])


    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions) + " ORDER BY created_at DESC"
    else:
        query = base_query + " ORDER BY created_at DESC"

    # 🧠 Corrected this line: `cursor` -> `cur`
    cur.execute(query, tuple(params))

    # ✅ cur is already a DictCursor, so rows will be dictionaries
    applications = cur.fetchall()

    cur.close()
    return render_template('admin/dashboard.html', applications=applications, current_filter=status_filter)

@admin_bp.route('/application/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_application(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

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
        mysql.connection.commit()
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
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM leave_applications WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        flash('Application deleted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to delete application', 'danger')
        # Log the error: current_app.logger.error(f"Delete error: {str(e)}")
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/approve/<int:app_id>')
@admin_required
def approve_application(app_id):
    
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
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
        
        mysql.connection.commit()
        flash('Application approved', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
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
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE leave_applications SET 
            status = 'rejected',
            rejected_by = %s,
            rejected_at = %s
            WHERE id = %s AND status = 'pending'
        """, (session['admin_username'], datetime.now(), id))
        mysql.connection.commit()
        flash('Application rejected', 'warning')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error rejecting application: {str(e)}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/application/print/<int:id>')
@admin_required
def print_application(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT la.*,
               COALESCE(s.username, la.name) AS name,
               COALESCE(s.pno, la.pno) AS pno,
               CASE
                   WHEN la.designation LIKE '%%HOD%%'
                        OR la.designation LIKE '%%Head%%'
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
        flash('Application not found', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    if application['status'] != 'approved':
        flash('Only approved applications can be printed.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    for field in ('start_date', 'end_date', 'last_leave_start', 'last_leave_end', 'created_at'):
        val = application.get(field)
        if isinstance(val, str):
            try:
                application[field] = datetime.fromisoformat(val)
            except ValueError:
                application[field] = None

    template = 'admin/pdf_template_hod.html' if application['is_hod'] else 'admin/pdf_template_staff.html'

    logo = get_logo_base64()
    rendered = render_template(template, app=application, logo=logo)

    pdf = HTML(string=rendered, base_url=request.root_url).write_pdf(
        stylesheets=[CSS(string='@page { margin: 2cm; }')]
    )

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=leave_application_{id}.pdf'
    return response


