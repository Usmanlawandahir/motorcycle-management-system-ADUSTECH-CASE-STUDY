import pymysql
from config import Config

def get_db_connection():
    try:
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            port=Config.MYSQL_PORT,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return connection
    except pymysql.Error as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(query, params=None, fetch=False, fetch_one=False):
    connection = get_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            connection.commit()
            result = cursor.lastrowid if cursor.lastrowid else True
        cursor.close()
        connection.close()
        return result
    except pymysql.Error as e:
        print(f"Query error: {e}")
        if connection:
            connection.rollback()
            connection.close()
        return None
