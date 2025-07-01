# app/__init__.py
from flask import Flask
from .routes import staff_bp  # Import directly from routes
from .routes import staff_bp

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = 'your-secret-key-here'
    
    # Register blueprints with URL prefix
    app.register_blueprint(staff_bp, url_prefix='/staff')
    
    return app
