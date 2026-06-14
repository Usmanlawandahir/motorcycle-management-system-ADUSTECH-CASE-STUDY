"""
Database setup script for ADUSTech Riders Management System.
Run this once to create the database and tables.

Usage: python setup_db.py
"""
import pymysql
import os
import sys

DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'port': int(os.environ.get('MYSQL_PORT', 3306))
}

def setup():
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')

    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        sys.exit(1)

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        conn.commit()
        cursor.close()
        conn.close()

        print("Database setup completed successfully!")
        print("Database: adustech_riders")
        print("\nNext steps:")
        print("  1. pip install -r backend/requirements.txt")
        print("  2. cd backend && python app.py")
        print("  3. Visit http://localhost:5000/api/init-admin to create admin account")
        print("  4. Login as admin@adustech.edu.ng / admin123")

    except pymysql.Error as e:
        print(f"Database setup failed: {e}")
        print("\nMake sure MySQL is running and credentials are correct.")
        print("Set environment variables if needed: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD")
        sys.exit(1)

if __name__ == '__main__':
    setup()
