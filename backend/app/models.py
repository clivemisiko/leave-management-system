# backend/app/models.py

from backend.app.extensions import db
from datetime import datetime

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    pno = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    leave_balance = db.Column(db.Integer, default=0)

    leave_applications = db.relationship('LeaveApplication', backref='staff', lazy=True)

class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    delegated_worker = db.Column(db.String(100))
