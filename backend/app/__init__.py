import os
import base64
from datetime import datetime
from flask import Flask, current_app
from dotenv import load_dotenv
from flask_mail import Mail
from backend.app.extensions import get_mysql_connection, mail

load_dotenv()

# ✅ Base64 logo function (global scope so routes can access it)
def get_logo_base64():
    # Try multiple possible locations
    possible_paths = [
        # Absolute path (development)
        r"C:\Users\ADMIN\leave_app_system\backend\static\images\kenya_logo.png",
        # Relative path from __init__.py
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'kenya_logo.png')),
        # Common production path
        os.path.join(current_app.root_path, 'static', 'images', 'kenya_logo.png')
    ]
    
    for logo_path in possible_paths:
        try:
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    current_app.logger.info(f"✅ Logo found at: {logo_path}")
                    return f"data:image/png;base64,{encoded_string}"
            else:
                current_app.logger.warning(f"⚠️ Logo not found at: {logo_path}")
        except Exception as e:
            current_app.logger.error(f"❌ Error loading logo from {logo_path}: {str(e)}")
    
    current_app.logger.error("❌ Could not find logo in any of the checked locations")
    return None


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    )
    app.get_logo_base64 = get_logo_base64

    app.secret_key = os.urandom(24)

    # 📧 Mail Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    mail.init_app(app)

    # ✅ Database connection check
    with app.app_context():
        try:
            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            print("✅ Connected to TiDB. Tables:", cur.fetchall())
            cur.close()
        except Exception as e:
            print("❌ TiDB Connection Error:", e)

    # 🌐 Template context: inject current time and logo
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow(),
            'logo_base64': get_logo_base64()
        }

    # 📆 Template filters
    @app.template_filter('format_datetime')
    def format_datetime(value):
        if not value:
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
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        try:
            return value.strftime(format)
        except Exception:
            return str(value)

    # 🔌 Register blueprints
    from .admin.routes import admin_bp
    from .staff.routes import staff_bp
    from .test_routes import test_bp
    from .setup_db_routes import setup_db_bp
    from .routes.contact import contact_bp
    from .routes.main_routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(setup_db_bp)
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
