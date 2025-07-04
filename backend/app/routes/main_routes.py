# routes/main_routes.py
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    """Route for the landing/home page"""
    return render_template('landing.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')
@main_bp.route('/')
def home():
    """Public home page"""
    return render_template('landing.html')