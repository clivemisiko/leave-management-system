from flask import Flask
from datetime import datetime
import os
from flask_mail import Mail
#from flask_wtf.csrf import CSRFProtect
from app.extensions import mysql  # ✅ Import from extensions, not directly
from .extensions import mail

# ❌ DO NOT import routes here at the top — it causes circular import

#csrf = CSRFProtect()
mail = Mail()
def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.secret_key = os.urandom(24)
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'root'
    app.config['MYSQL_DB'] = 'leave_app'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_METHODS'] = []
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost/leave_app'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Email configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'clivebillzerean@gmail.com'
    app.config['MAIL_PASSWORD'] = 'uukuhjtaiicrgkqe'
    app.config['MAIL_DEFAULT_SENDER'] = 'clivebillzereana@gmail.com'
    app.config['SECURITY_PASSWORD_SALT'] = 'your-unique-salt-here'
    app.config.from_pyfile('config.py')
    config_path = os.path.join(os.path.dirname(__file__), 'config.py')
    app.config.from_pyfile(config_path)

    mysql.init_app(app)
    mail.init_app(app)
    #csrf.init_app(app)
    with app.app_context():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            print("✅ Successfully connected to leave_app database")
            print(f"Tables: {cur.fetchall()}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

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

    from .admin.routes import admin_bp
     
    from .staff.routes import staff_bp  # adjust if staff routes live in a different file

    
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('app.log', maxBytes=10240)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

    @app.after_request
    def after_request(response):
        response.headers['Connection'] = 'close'
        return response

    return app
