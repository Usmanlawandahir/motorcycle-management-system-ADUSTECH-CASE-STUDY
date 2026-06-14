import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'adustech-riders-secret-key-2024')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'adustech_riders')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
