
import json
import os
import re
from datetime import date
from urllib.parse import urlparse

import mysql.connector
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)

from database import get_db

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "job-tracker-local-development"
)

FIELDS = {
    "companies": [
        "company_name", "industry", "website",
        "city", "state", "notes"
    ],
    "jobs": [
        "company_id", "job_title", "job_type",
        "salary_min", "salary_max", "job_url",
        "date_posted", "requirements"
    ],
    "applications": [
        "job_id", "application_date", "status",
        "resume_version", "cover_letter_sent",
        "interview_data"
    ],
    "contacts": [
        "company_id", "contact_name", "title",
        "email", "phone", "linkedin_url", "notes"
    ]
}

PRIMARY_KEYS = {
    "companies": "company_id",
    "jobs": "job_id",
    "applications": "application_id",
    "contacts": "contact_id"
}

REQUIRED = {
    "company_name", "job_title",
    "application_date", "contact_name",
    "company_id", "job_id"
}

CHOICES = {
    "job_type": [
        "Full-time", "Part-time",
        "Contract", "Internship"
    ],
    "status": [
        "Applied", "Screening", "Interview",
        "Offer", "Rejected", "Withdrawn"
    ]
}

FIELD_TYPES = {
    "notes": "textarea",
    "requirements": "textarea",
    "interview_data": "textarea",
    "date_posted": "date",
    "application_date": "date",
    "salary_min": "number",
    "salary_max": "number",
    "cover_letter_sent": "checkbox",
    "email": "email"
}

FIELD_LIMITS = {
    "company_name": 100,
    "industry": 50,
    "website": 200,
    "city": 50,
    "state": 50,
    "job_title": 100,
    "job_url": 300,
    "resume_version": 50,
    "contact_name": 100,
    "title": 100,
    "email": 100,
    "phone": 20,
    "linkedin_url": 200
}

FOREIGN_KEYS = {
    "company_id": ("companies", "company_id"),
    "job_id": ("jobs", "job_id")
}


def run_query(sql, params=(), fetch=False, single=False):
    connection = get_db()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)

        if fetch:
            if single:
                return cursor.fetchone()
            return cursor.fetchall()

        connection.commit()

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def check_table(table):
    if table not in FIELDS:
        abort(404)


def readable_name(field):
    return field.replace("_", " ").title()


def valid_url(value):
    if not value:
        return True

    parsed = urlparse(value)

    return (
        parsed.scheme in ("http", "https")
        and bool(parsed.netloc)
        and " " not in value
    )


def valid_email(value):
    if not value:
        return True

    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            value
        )
    )


def valid_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def foreign_key_exists(field, record_id):
    table, primary_key = FOREIGN_KEYS[field]

    result = run_query(
        "SELECT " + primary_key +
        " FROM " + table +
        " WHERE " + primary_key + " = %s",
        (record_id,),
        fetch=True,
        single=True
    )

    return result is not None


def parse_skills(value):
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return []

    if not isinstance(parsed, list):
        return []

    return [
        str(skill).strip()
        for skill in parsed
        if str(skill).strip()
    ]


@app.route("/")
def dashboard():
    stats = {}

    for table in FIELDS:
        result = run_query(
            "SELECT COUNT(*) AS total FROM " + table,
            fetch=True,
            single=True
        )

        stats[table] = result["total"]

    return render_template(
        "dashboard.html",
        stats=stats
    )


@app.route("/<table>")
def list_records(table):
    check_table(table)

    records = run_query(
        "SELECT * FROM " + table +
        " ORDER BY " + PRIMARY_KEYS[table] + " DESC",
        fetch=True
    )

    return render_template(
        table + ".html",
        records=records,
        table=table,
        fields=FIELDS[table],
        primary_key=PRIMARY_KEYS[table]
    )


@app.route("/<table>/<int:record_id>")
def view_record(table, record_id):
    check_table(table)

    primary_key = PRIMARY_KEYS[table]

    record = run_query(
        "SELECT * FROM " + table +
        " WHERE " + primary_key + " = %s",
        (record_id,),
        fetch=True,
        single=True
    )

    if not record:
        abort(404)

    return render_template(
        "detail.html",
        table=table,
        record=record,
        fields=FIELDS[table],
        primary_key=primary_key
    )


def get_options():
    companies = run_query(
        "SELECT company_id AS id, "
        "company_name AS label "
        "FROM companies ORDER BY company_name",
        fetch=True
    )

    jobs = run_query(
        "SELECT job_id AS id, "
        "job_title AS label "
        "FROM jobs ORDER BY job_title",
        fetch=True
    )

    return {
        "company_id": companies,
        "job_id": jobs
    }


def get_form_data(table):
    data = {}

    for field in FIELDS[table]:
        value = request.form.get(field, "").strip()

        # Check required information
        if field in REQUIRED and not value:
            raise ValueError(
                readable_name(field) + " is required."
            )

        # Checkbox
        if field == "cover_letter_sent":
            data[field] = (
                1 if request.form.get(field) else 0
            )
            continue

        # Foreign key validation
        if field in FOREIGN_KEYS:
            if not value:
                data[field] = None
                continue

            try:
                record_id = int(value)
            except ValueError:
                raise ValueError(
                    readable_name(field) +
                    " must be a valid selection."
                )

            if record_id <= 0 or not foreign_key_exists(
                field, record_id
            ):
                raise ValueError(
                    "The selected " +
                    readable_name(field) +
                    " does not exist."
                )

            data[field] = record_id
            continue

        # Job requirements stored as JSON
        if field == "requirements":
            skills = [
                skill.strip()
                for skill in value.split(",")
                if skill.strip()
            ]

            data[field] = json.dumps(skills)
            continue

        # Interview information stored as JSON
        if field == "interview_data":
            if value:
                try:
                    parsed = json.loads(value)
                    data[field] = json.dumps(parsed)

                except json.JSONDecodeError:
                    raise ValueError(
                        "Interview Data must contain valid JSON."
                    )
            else:
                data[field] = None

            continue

        # Salary validation
        if field in ("salary_min", "salary_max"):
            if not value:
                data[field] = None
                continue

            try:
                salary = int(value)
            except ValueError:
                raise ValueError(
                    readable_name(field) +
                    " must be a whole number."
                )

            if salary < 0:
                raise ValueError(
                    "Salary cannot be negative."
                )

            if salary > 2147483647:
                raise ValueError(
                    "Salary exceeds the supported limit."
                )

            data[field] = salary
            continue

        # Validate dates
        if field in ("date_posted", "application_date"):
            if value and not valid_date(value):
                raise ValueError(
                    readable_name(field) +
                    " must be a valid date."
                )

            data[field] = value or None
            continue

        # Validate dropdown selections
        if field in CHOICES:
            if value and value not in CHOICES[field]:
                raise ValueError(
                    "Invalid selection for " +
                    readable_name(field)
                )

        # Validate email address
        if field == "email":
            if not valid_email(value):
                raise ValueError(
                    "Please enter a valid email address."
                )

        # Validate website links
        if field in (
            "website", "job_url", "linkedin_url"
        ):
            if not valid_url(value):
                raise ValueError(
                    readable_name(field) +
                    " must be a valid http or https URL."
                )

        # Validate field length
        if field in FIELD_LIMITS:
            if len(value) > FIELD_LIMITS[field]:
                raise ValueError(
                    readable_name(field) +
                    " is too long. Maximum " +
                    str(FIELD_LIMITS[field]) +
                    " characters."
                )

        data[field] = value or None

    # Compare salary minimum and maximum
    if table == "jobs":
        minimum = data.get("salary_min")
        maximum = data.get("salary_max")

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                raise ValueError(
                    "Minimum salary cannot be "
                    "greater than maximum salary."
                )

    return data


def show_form(table, record=None):
    record = dict(record) if record else {}

    # Convert database JSON into editable skill text
    if table == "jobs" and record.get("requirements"):
        requirements = record["requirements"]

        try:
            parsed = json.loads(requirements)

            if isinstance(parsed, list):
                record["requirements"] = ", ".join(
                    str(skill) for skill in parsed
                )

        except (ValueError, TypeError):
            pass

    # Preserve selected dropdown values on errors
    for field in FOREIGN_KEYS:
        value = record.get(field)

        if isinstance(value, str) and value.isdigit():
            record[field] = int(value)

    return render_template(
        "form.html",
        table=table,
        fields=FIELDS[table],
        record=record,
        choices=CHOICES,
        field_types=FIELD_TYPES,
        required=REQUIRED,
        options=get_options()
    )


@app.route("/<table>/add", methods=["GET", "POST"])
def add_record(table):
    check_table(table)

    if request.method == "POST":
        try:
            data = get_form_data(table)

            columns = ", ".join(data.keys())
            placeholders = ", ".join(
                ["%s"] * len(data)
            )

            sql = (
                "INSERT INTO " + table +
                " (" + columns + ") VALUES (" +
                placeholders + ")"
            )

            run_query(sql, tuple(data.values()))

            flash("Record added successfully.")

            return redirect(
                url_for("list_records", table=table)
            )

        except ValueError as error:
            flash(str(error))

        except mysql.connector.Error:
            flash(
                "Could not save the record. "
                "Please check your information."
            )

        return show_form(
            table,
            request.form.to_dict()
        )

    return show_form(table)


@app.route(
    "/<table>/<int:record_id>/edit",
    methods=["GET", "POST"]
)
def edit_record(table, record_id):
    check_table(table)

    primary_key = PRIMARY_KEYS[table]

    record = run_query(
        "SELECT * FROM " + table +
        " WHERE " + primary_key + " = %s",
        (record_id,),
        fetch=True,
        single=True
    )

    if not record:
        abort(404)

    if request.method == "POST":
        try:
            data = get_form_data(table)

            updates = ", ".join(
                field + " = %s"
                for field in data
            )

            sql = (
                "UPDATE " + table +
                " SET " + updates +
                " WHERE " + primary_key + " = %s"
            )

            run_query(
                sql,
                tuple(data.values()) + (record_id,)
            )

            flash("Record updated successfully.")

            return redirect(
                url_for("list_records", table=table)
            )

        except ValueError as error:
            flash(str(error))

        except mysql.connector.Error:
            flash(
                "Could not update the record. "
                "Please check your information."
            )

        return show_form(
            table,
            request.form.to_dict()
        )

    return show_form(table, record)


@app.route(
    "/<table>/<int:record_id>/delete",
    methods=["POST"]
)
def delete_record(table, record_id):
    check_table(table)

    try:
        run_query(
            "DELETE FROM " + table +
            " WHERE " + PRIMARY_KEYS[table] + " = %s",
            (record_id,)
        )

        flash("Record deleted successfully.")

    except mysql.connector.Error:
        flash("Unable to delete the record.")

    return redirect(
        url_for("list_records", table=table)
    )


@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    results = []
    skills_input = ""

    if request.method == "POST":
        skills_input = request.form.get(
            "skills", ""
        )

        user_skills = {
            skill.strip().lower()
            for skill in skills_input.split(",")
            if skill.strip()
        }

        jobs = run_query(
            "SELECT j.job_title, j.requirements, "
            "c.company_name "
            "FROM jobs j "
            "LEFT JOIN companies c "
            "ON j.company_id = c.company_id",
            fetch=True
        )

        for job in jobs:
            required_skills = parse_skills(
                job["requirements"]
            )

            matched = [
                skill
                for skill in required_skills
                if skill.lower() in user_skills
            ]

            missing = [
                skill
                for skill in required_skills
                if skill.lower() not in user_skills
            ]

            percentage = (
                round(
                    len(matched) /
                    len(required_skills) * 100
                )
                if required_skills else 0
            )

            results.append({
                "title": job["job_title"],
                "company": job["company_name"],
                "percentage": percentage,
                "matched": len(matched),
                "total": len(required_skills),
                "missing": missing
            })

        results.sort(
            key=lambda item: item["percentage"],
            reverse=True
        )

    return render_template(
        "job_match.html",
        results=results,
        skills_input=skills_input
    )


if __name__ == "__main__":
    app.run(debug=True)
