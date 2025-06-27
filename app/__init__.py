from flask import Flask
from datetime import datetime
import os
from flask_mail import Mail
from .extensions import mysql  # ✅ Ensure you have extensions/mysql.py defining mysql = MySQL()
from .extensions import mail

# ✅ Initialize mail
mail = Mail()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Secret key
    app.secret_key = os.urandom(24)

    # ✅ Railway MySQL configuration
    app.config['MYSQL_HOST'] = 'shuttle.proxy.rlwy.net'
    app.config['MYSQL_PORT'] = 49114
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'WhgfFYqECFcIkbWgscJnEAtENSjpIyaD'
    app.config['MYSQL_DB'] = 'railway'


    # ✅ Optional: SQLAlchemy URI (only if you're using SQLAlchemy anywhere)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:WhgfFYqECFcIkbWgscJnEAtENSjpIyaD@shuttle.proxy.rlwy.net:49114/railway'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # CSRF settings (if used)
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_METHODS'] = []
    app.config['WTF_CSRF_TIME_LIMIT'] = None

    # Email configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'clivebillzerean@gmail.com'
    app.config['MAIL_PASSWORD'] = 'uukuhjtaiicrgkqe'
    app.config['MAIL_DEFAULT_SENDER'] = 'clivebillzereana@gmail.com'
    app.config['SECURITY_PASSWORD_SALT'] = 'your-unique-salt-here'

    # ✅ Initialize extensions
    mysql.init_app(app)
    mail.init_app(app)

    # ✅ Test database connection
    with app.app_context():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            print("✅ Successfully connected to Railway MySQL database")
            print(f"Tables: {cur.fetchall()}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

    # ✅ Template filters
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

    # ✅ Blueprints
    from .admin.routes import admin_bp
    from .staff.routes import staff_bp

    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ✅ Logging (for production)
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('app.log', maxBytes=10240)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

    # ✅ Set headers after each request
    @app.after_request
    def after_request(response):
        response.headers['Connection'] = 'close'
        return response

    @app.route('/')
    def home():
        return 'Leave Management System is Running. Go to /admin or /staff'

    from .setup_db_routes import setup_db_bp
    app.register_blueprint(setup_db_bp)

    return app


