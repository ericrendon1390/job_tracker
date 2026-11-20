import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="job_tracker"
    )

if __name__ == "__main__":
    connection = get_db()
    print("Successfully connected to MySQL!")
    connection.close()
