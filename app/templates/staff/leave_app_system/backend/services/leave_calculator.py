from datetime import date
from ..models import Staff

def calculate_leave_balance(staff_id):
    staff = Staff.query.get(staff_id)
    fiscal_start = date(date.today().year, 7, 1)  # Example: fiscal year starts July 1
    
    if date.today() < fiscal_start:
        fiscal_start = date(date.today().year - 1, 7, 1)
    
    used_leave = sum(
        app.leave_days for app in staff.leave_applications 
        if app.start_date >= fiscal_start and app.status == 'approved'
    )
    
    return {
        'annual_entitlement': 21,  # Example: 21 days/year
        'used_leave': used_leave,
        'current_balance': staff.leave_balance,
        'projected_balance': 21 - used_leave
    }