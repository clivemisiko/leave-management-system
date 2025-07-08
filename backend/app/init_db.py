from flask import Flask
from backend.app.extensions import db
from backend.app.models import Staff, LeaveApplication
from config import DevelopmentConfig  # ✅ import from root
import os

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)  # ✅ cleaner, safer
db.init_app(app)

def initialize_database():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully in Neon.")
        except Exception as e:
            print(f"❌ Error initializing DB: {e}")

if __name__ == '__main__':
    initialize_database()
