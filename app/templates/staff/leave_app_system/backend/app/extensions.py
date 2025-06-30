# app/extensions.py

from flask_mysqldb import MySQL
#from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

mail = Mail()
mysql = MySQL()
#csrf = CSRFProtect()
