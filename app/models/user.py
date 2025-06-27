from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'staff', etc.
    department = db.Column(db.String(100))
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    leave_requests = db.relationship('LeaveRequest', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"
