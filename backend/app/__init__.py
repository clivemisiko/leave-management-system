from flask import Flask
from datetime import datetime
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from config import Config
from .extensions import mysql, mail

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Load config from class only
    app.config.from_object(Config)

    # Initialize extensions
    mysql.init_app(app)
    mail.init_app(app)
    db.init_app(app)

    # Optional MySQL connection test
    with app.app_context():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            print("✅ Successfully connected to MySQL")
            print(f"Tables: {cur.fetchall()}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

    # Filters
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

    # Blueprints
    from .admin.routes import admin_bp
    from .staff.routes import staff_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')

    # Logging for production
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('app.log', maxBytes=10240)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

    @app.after_request
    def after_request(response):
        response.headers['Connection'] = 'close'
        return response

    return app
