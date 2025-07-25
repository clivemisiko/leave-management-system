import os
import base64
from datetime import datetime
import pytz
from flask import Flask, current_app
from dotenv import load_dotenv
from backend.app.extensions import mail

load_dotenv()

# ✅ Constants
NAIROBI_TZ = pytz.timezone('Africa/Nairobi')

# ✅ Load Logo (used globally in templates and PDFs)
def get_logo_base64():
    logo_path = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'static', 'images', 'kenya_logo.png'
    ))

    try:
        with open(logo_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except FileNotFoundError:
        try:
            current_app.logger.warning(f"⚠️ Logo not found at: {logo_path}")
        except:
            print(f"⚠️ Logo not found at: {logo_path}")
        return None

# ✅ Load Signature (dynamic for PDF)
def load_signature_base64():
    try:
        signature_path = os.path.join(current_app.static_folder, 'images', 'signature.png')
        with open(signature_path, 'rb') as image_file:
            return 'data:image/png;base64,' + base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        try:
            current_app.logger.warning(f"⚠️ Signature load failed: {e}")
        except:
            print(f"⚠️ Signature load failed: {e}")
        return None

def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    )

    # ✅ Configurations
    app.config['TIMEZONE'] = 'Africa/Nairobi'
    app.config['DB_TIMEZONE'] = 'UTC'
    app.secret_key = os.urandom(24)
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB upload limit

    # ✅ Email (Flask-Mail)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    mail.init_app(app)

    # ✅ Logo and Signature access
    app.get_logo_base64 = get_logo_base64
    app.get_signature_base64 = load_signature_base64

    print("✅ Using PyMySQL. Skipping SQLAlchemy config.")

    # ✅ Global Template Context
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow(),
            'logo_base64': get_logo_base64()
        }

    # ✅ Custom Filters
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%b %d, %Y %I:%M %p'):
        if not value:
            return ""
        try:
            if isinstance(value, str):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    value = datetime.strptime(value, '%Y-%m-%d')
                value = pytz.utc.localize(value)
            if value.tzinfo is None:
                value = pytz.utc.localize(value)
            local_dt = value.astimezone(NAIROBI_TZ)
            return local_dt.strftime(format)
        except Exception:
            return value

    @app.template_filter('format_date')
    def format_date(value, format='%d/%m/%Y'):
        return format_datetime(value, format)

    # ✅ Blueprints
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
