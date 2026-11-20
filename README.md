
# Job Application Tracker

## Project Description

This project is a web application designed to help users organize and track their job applications.

It was developed using Python, Flask, MySQL, HTML, and CSS
for the COP4751 Course Project.

## Features

- Dashboard showing application statistics
- Add, view, edit, and delete companies
- Add, view, edit, and delete jobs
- Add, view, edit, and delete job applications
- Add, view, edit, and delete contacts
- Job Match feature that compares user skills with job requirements
- MySQL database with four related tables

## Technologies Used

- Python 3
- Flask
- MySQL
- HTML
- CSS
- GitHub
- ChatGPT (AI development assistance)

## Database Tables

1. companies
2. jobs
3. applications
4. contacts

The database includes foreign keys and JSON columns
for storing job requirements and interview information.

## Installation Instructions

### 1. Download the Project

Clone the GitHub repository or download it as a ZIP file.

### 2. Install Dependencies

Make sure Python and MySQL Server are installed.

Open a terminal inside the project folder and run:

pip install -r requirements.txt

### 3. Create the Database

Open MySQL Workbench and connect to your MySQL server.

Open the schema.sql file and execute the entire script.

This creates the job_tracker database and its four tables.

### 4. Configure Database Credentials

Create a file named .env in the main project folder.

Add the following line:

DB_PASSWORD="your_mysql_password"

Replace your_mysql_password with your local MySQL root password.

The application connects to localhost using the root user.

### 5. Run the Application

Open a terminal in the project folder and enter:

python app.py

Then open your browser and visit:

http://127.0.0.1:5000

## How to Use

1. Add a company.
2. Add a job associated with that company.
3. Enter job requirements separated by commas.
4. Add job applications and contacts.
5. Use Edit and Delete to manage existing records.
6. Visit Job Match and enter skills separated by commas.
7. View the calculated skill match percentage.

## Job Match Example

Job: Software Developer

Required skills: Python, SQL, Flask

User skills: Python, SQL

Result: 67% match (2 out of 3 skills)

Missing skill: Flask

## AI Usage

ChatGPT was used to assist with generating Flask routes,
HTML templates, SQL code, and the Job Match algorithm. 
Created an in depth README document

Additional details are documented in AI_USAGE.md.

