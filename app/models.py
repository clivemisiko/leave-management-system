from . import db
from datetime import datetime

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pno = db.Column(db.String(20), unique=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    leave_balance = db.Column(db.Integer, default=0)
    leave_applications = db.relationship('LeaveApplication', backref='staff', lazy=True)

class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    leave_type = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    # ... add all other fields from your current table