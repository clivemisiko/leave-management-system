import os
from datetime import datetime
from flask import Flask
from flask_mail import Mail
from .app.extensions import mysql, mail
from .config import Config

def create_app():
    # Get absolute path to the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(
        __name__,
        template_folder=os.path.join(app_dir, 'templates'),  # Absolute path
        static_folder=os.path.join(app_dir, 'static')
    )

    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions
    mysql.init_app(app)
    mail.init_app(app)

    # Register template filters
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

    # Register blueprints
    from app.admin.routes import admin_bp
    from app.staff.routes import staff_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')

    # Configure logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')

    # Add security headers
    @app.after_request
    def after_request(response):
        response.headers['Connection'] = 'close'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app