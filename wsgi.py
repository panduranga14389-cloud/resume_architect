import os
import sqlite3
from app import app

# Automatically build your database on Render if it doesn't exist yet
DATABASE_FILE = 'database.db' # Change this to match your database name in app.py

if not os.path.exists(DATABASE_FILE):
    print("Database not found. Initializing from schema.sql...")
    try:
        connection = sqlite3.connect(DATABASE_FILE)
        with open('schema.sql', 'r') as f:
            connection.executescript(f.read())
        connection.commit()
        connection.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    app.run()