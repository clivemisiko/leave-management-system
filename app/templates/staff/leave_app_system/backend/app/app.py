from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from weasyprint import HTML, CSS
import MySQLdb.cursors
import os
from functools import wraps
from datetime import datetime
from flask import Blueprint
from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)
app.secret_key = os.urandom(24)
csrf = CSRFProtect(app)

@app.after_request
def after_request(response):
    response.headers['Connection'] = 'close'
    return response

@app.template_filter('format_date')
def format_date(value):
    if isinstance(value, (str, bytes)):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime('%d %b %Y')

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'leave_app'
mysql = MySQL(app)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login as admin', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()
        cur.close()

        if admin and check_password_hash(admin[2], password):
            session['admin_logged_in'] = True
            session['admin_id'] = admin[0]
            session['admin_username'] = admin[1]
            flash('Login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/application/new', methods=['GET', 'POST'])
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
                'last_leave_end': last_leave_end
            }

            if not all([form_data['name'], form_data['pno'], form_data['designation'], form_data['start_date'], form_data['end_date']]):
                flash('Please fill all required fields', 'danger')
                return redirect(url_for('create_application'))

            if not salary_continue and not salary_address:
                flash('Payment address is required when not continuing bank payments', 'danger')
                return redirect(url_for('create_application'))

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO leave_applications 
                (name, pno, designation, leave_days, start_date, end_date, 
                 contact_address, contact_tel, salary_continue, salary_address,
                 delegate, outside_country, leave_balance, last_leave_start, last_leave_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(form_data.values()))
            mysql.connection.commit()
            flash('Application created successfully', 'success')
            return redirect(url_for('admin_dashboard'))

        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return redirect(url_for('create_application'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error creating application: {str(e)}', 'danger')
            return redirect(url_for('create_application'))
        finally:
            if 'cur' in locals():
                cur.close()

    return render_template('admin/create_application.html')

@app.route('/admin/dashboard')
@app.route('/admin/dashboard/<status_filter>')
@admin_required
def admin_dashboard(status_filter=None):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    base_query = """
        SELECT id, name, pno, designation, leave_days,
               start_date, end_date, status,
               approved_by, approved_at,
               rejected_by, rejected_at,
               created_at
        FROM leave_applications
    """

    if status_filter in ['approved', 'rejected', 'pending']:
        query = base_query + " WHERE status = %s ORDER BY created_at DESC"
        cur.execute(query, (status_filter,))
    else:
        query = base_query + " ORDER BY created_at DESC"
        cur.execute(query)

    applications = cur.fetchall()
    cur.close()
    return render_template('admin/dashboard.html', applications=applications, current_filter=status_filter)

@app.route('/admin/application/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_application(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("""
            UPDATE leave_applications SET 
            name = %s, pno = %s, designation = %s, leave_days = %s, 
            start_date = %s, end_date = %s, contact_address = %s, 
            contact_tel = %s, status = %s 
            WHERE id = %s
        """, (request.form['name'], request.form['pno'], request.form['designation'],
              request.form['leave_days'], request.form['start_date'], request.form['end_date'],
              request.form['contact_address'], request.form['contact_tel'],
              request.form['status'], id))
        mysql.connection.commit()
        cur.close()
        flash('Application updated successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    cur.execute("SELECT * FROM leave_applications WHERE id = %s", (id,))
    application = cur.fetchone()
    cur.close()

    if not application:
        flash('Application not found', 'danger')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_application.html', application=application)

@app.route('/admin/application/delete/<int:id>')
@admin_required
def delete_application(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM leave_applications WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Application deleted successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/application/approve/<int:id>')
@admin_required
def approve_application(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE leave_applications SET 
            status = 'approved',
            approved_by = %s,
            approved_at = %s
            WHERE id = %s AND status = 'pending'
        """, (session['admin_username'], datetime.now(), id))
        mysql.connection.commit()
        flash('Application approved successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error approving application: {str(e)}', 'danger')
    finally:
        cur.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/application/reject/<int:id>')
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
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/application/print/<int:id>')
@admin_required
def print_application(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT *,
               CASE
                   WHEN designation LIKE '%%HOD%%'
                     OR designation LIKE '%%Head%%'
                   THEN 1
                   ELSE 0
               END AS is_hod
        FROM leave_applications
        WHERE id = %s
    """, (id,))
    application = cur.fetchone()
    cur.close()

    if not application:
        flash('Application not found', 'danger')
        return redirect(url_for('admin_dashboard'))

    for field in ('start_date', 'end_date', 'last_leave_start', 'last_leave_end', 'created_at'):
        val = application.get(field)
        if isinstance(val, str):
            try:
                application[field] = datetime.fromisoformat(val)
            except ValueError:
                application[field] = None

    template = 'pdf_template_hod.html' if application['is_hod'] else 'pdf_template_staff.html'

    rendered = render_template(template, app=application)
    pdf = HTML(string=rendered, base_url=request.root_url).write_pdf(
        stylesheets=[CSS(string='@page { margin: 2cm; }')]
    )

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=leave_application_{id}.pdf'
    return response

if __name__ == '__main__':
    app.run(debug=True)