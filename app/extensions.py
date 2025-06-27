import pymysql
pymysql.install_as_MySQLdb()  # Do this first before importing MySQL

from flask_mysqldb import MySQL
mysql = MySQL()

from flask_mail import Mail
mail = Mail()
