# app/init_db.py
from app.extensions import mysql
from flask import Flask

app = Flask(__name__)
app.config.from_object('your_config_module')  # Replace this with your actual config

with app.app_context():
    cur = mysql.connection.cursor()
    with open('schema.sql', 'r') as f:
        cur.execute(f.read())
    mysql.connection.commit()
    cur.close()
