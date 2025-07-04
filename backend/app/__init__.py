from flask import Flask, render_template
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_mail import Mail
from backend.app.extensions import get_mysql_connection, mail  # ✅ Correct import here

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.urandom(24)

    # Mail Config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    mail.init_app(app)

    # ✅ Test DB Connection (TiDB)
    with app.app_context():
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            print("✅ Connected to TiDB. Tables:", cur.fetchall())
            cur.close()
        except Exception as e:
            print("❌ TiDB Connection Error:", e)

    # Template filters
    @app.template_filter('format_datetime')
    def format_datetime(value):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return value
        return value.strftime('%b %d, %Y %I:%M %p')

    @app.template_filter('format_date')
    def format_date(value, format='%b %d, %Y'):
        if not value:
            return ""
        if isinstance(value, str):
            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y'):
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        try:
            return value.strftime(format)
        except:
            return str(value)

    # Routes and blueprints
    from .admin.routes import admin_bp
    from .staff.routes import staff_bp
    from .test_routes import test_bp
    from .setup_db_routes import setup_db_bp

    app.register_blueprint(test_bp)
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(setup_db_bp)

    @app.route('/')
    def home():
        return render_template('landing.html')

    return app
