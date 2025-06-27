# Database Configuration
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'root'
MYSQL_DB = 'leave_app'
MYSQL_CURSORCLASS = 'DictCursor'

# Flask Configuration
SECRET_KEY = '0e59c04308c4a59abdfbc4750a15d2876b86019739fbd6b7f03eb6ced7b9b648'  # Generate a strong secret key

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'clivebillzerean@gmail.com'
MAIL_PASSWORD = 'uukuhjtaiicrgkqe'  # Use app-specific password for Gmail
MAIL_DEFAULT_SENDER = 'clivebillzerean@gmail.com'

PASSWORD_RESET_EXPIRATION = 3600  

import os

class Config:
    SECRET_KEY = os.urandom(24)
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'root'
    MYSQL_DB = 'leave_app'