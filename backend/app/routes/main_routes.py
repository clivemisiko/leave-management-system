# routes/main_routes.py
from flask import Blueprint, render_template
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/')
def home():
    """Public home page"""
    return render_template('landing.html')

@main_bp.route('/leave-policy')
def leave_policy():
    """Display the leave policy page"""
    return render_template('leave_policy.html')

@main_bp.route('/help-center')
def help_center():
    """Display the help center page"""
    faqs = [
        {
            'question': 'How do I apply for leave?',
            'answer': 'Navigate to the Leave Application section and fill out the form with your details.'
        },
        {
            'question': 'What if I forget my password?',
            'answer': 'Use the password reset feature or contact the system administrator.'
        }
    ]
    return render_template('help_center.html', faqs=faqs)


@main_bp.route('/public-holidays')
def public_holidays():
    # Kenya public holidays for 2025 (you might want to make this dynamic)
    holidays = [
        {"date": "2025-01-01", "name": "New Year's Day"},
        {"date": "2025-04-18", "name": "Good Friday"},
        {"date": "2025-04-21", "name": "Easter Monday"},
        {"date": "2025-05-01", "name": "Labour Day"},
        {"date": "2025-06-01", "name": "Madaraka Day"},
        {"date": "2025-10-10", "name": "Huduma Day"},
        {"date": "2025-10-20", "name": "Mashujaa Day"},
        {"date": "2025-12-12", "name": "Jamhuri Day"},
        {"date": "2025-12-25", "name": "Christmas Day"},
        {"date": "2025-12-26", "name": "Boxing Day"}
    ]
    
    # Convert string dates to datetime objects and add weekday
    for holiday in holidays:
        dt = datetime.strptime(holiday['date'], '%Y-%m-%d')
        holiday['date_obj'] = dt
        holiday['weekday'] = dt.strftime('%A')
        
    # Sort holidays by date
    holidays.sort(key=lambda x: x['date_obj'])
    
    return render_template('public_holidays.html', holidays=holidays)

@main_bp.app_context_processor
def inject_now():
    return {'now': datetime.utcnow()}