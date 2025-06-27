import os

class Config:
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'interchange.proxy.rlwy.net')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'SCCOJeyUAanzmZTHprXobCKidCuPSflS')
    MYSQL_DB = os.getenv('MYSQL_DB', 'railway')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 24117))
