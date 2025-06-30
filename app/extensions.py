# app/extensions.py

import pymysql
pymysql.install_as_MySQLdb()  # Must come before importing MySQL

from flask_mail import Mail
from flask_mysqldb import MySQL

mail = Mail()
mysql = MySQL()
