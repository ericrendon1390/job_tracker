
import json

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from database import get_db

app = Flask(__name__)
app.secret_key = "job-tracker-local-project"

# Tables and their editable fields
FIELDS = {
    "companies": [
        "company_name", "industry", "website", "city", "state", "notes"
    ],
    "jobs": [
        "company_id", "job_title", "job_type", "salary_min",
        "salary_max", "job_url", "date_posted", "requirements"
    ],
    "applications": [
        "job_id", "application_date", "status",
        "resume_version", "cover_letter_sent", "interview_data"
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
    "company_name", "job_title", "application_date", "contact_name"
}

CHOICES = {
    "job_type": ["Full-time", "Part-time", "Contract", "Internship"],
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


def run_query(sql, params=(), fetch=False, single=False):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)

        if fetch:
            if single:
                return cursor.fetchone()
            return cursor.fetchall()

        connection.commit()
    finally:
        cursor.close()
        connection.close()


def check_table(table):
    if table not in FIELDS:
        abort(404)


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

    return render_template("dashboard.html", stats=stats)


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


def get_options():
    companies = run_query(
        "SELECT company_id AS id, company_name AS label "
        "FROM companies ORDER BY company_name",
        fetch=True
    )

    jobs = run_query(
        "SELECT job_id AS id, job_title AS label "
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

        if field in REQUIRED and not value:
            raise ValueError(field.replace("_", " ") + " is required.")

        if field == "cover_letter_sent":
            data[field] = 1 if request.form.get(field) else 0

        elif field == "requirements":
            skills = [
                skill.strip()
                for skill in value.split(",")
                if skill.strip()
            ]
            data[field] = json.dumps(skills)

        elif field == "interview_data":
            if value:
                try:
                    data[field] = json.dumps(json.loads(value))
                except json.JSONDecodeError:
                    raise ValueError("Interview data must be valid JSON.")
            else:
                data[field] = None

        elif field in ("salary_min", "salary_max"):
            try:
                data[field] = int(value) if value else None
            except ValueError:
                raise ValueError("Salary must be a number.")

        else:
            data[field] = value if value else None

    return data


def show_form(table, record=None):
    if record:
        record = dict(record)

        if table == "jobs" and record.get("requirements"):
            skills = json.loads(record["requirements"])
            record["requirements"] = ", ".join(skills)

    return render_template(
        "form.html",
        table=table,
        fields=FIELDS[table],
        record=record or {},
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
            placeholders = ", ".join(["%s"] * len(data))

            sql = "INSERT INTO " + table + " (" + columns + \
                  ") VALUES (" + placeholders + ")"

            run_query(sql, tuple(data.values()))
            flash("Record added successfully.")
            return redirect(url_for("list_records", table=table))

        except (ValueError, Exception) as error:
            flash(str(error))

    return show_form(table)


@app.route("/<table>/<int:record_id>/edit", methods=["GET", "POST"])
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
                field + " = %s" for field in data
            )

            sql = "UPDATE " + table + " SET " + updates + \
                  " WHERE " + primary_key + " = %s"

            run_query(sql, tuple(data.values()) + (record_id,))
            flash("Record updated successfully.")
            return redirect(url_for("list_records", table=table))

        except Exception as error:
            flash(str(error))

    return show_form(table, record)


@app.route("/<table>/<int:record_id>/delete", methods=["POST"])
def delete_record(table, record_id):
    check_table(table)

    run_query(
        "DELETE FROM " + table +
        " WHERE " + PRIMARY_KEYS[table] + " = %s",
        (record_id,)
    )

    flash("Record deleted.")
    return redirect(url_for("list_records", table=table))


@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    results = []
    skills_input = ""

    if request.method == "POST":
        skills_input = request.form.get("skills", "")

        user_skills = {
            skill.strip().lower()
            for skill in skills_input.split(",")
            if skill.strip()
        }

        jobs = run_query(
            "SELECT j.job_title, j.requirements, "
            "c.company_name "
            "FROM jobs j LEFT JOIN companies c "
            "ON j.company_id = c.company_id",
            fetch=True
        )

        for job in jobs:
            requirements = json.loads(
                job["requirements"] or "[]"
            )

            required_skills = [
                str(skill).strip()
                for skill in requirements
            ]

            matched = [
                skill for skill in required_skills
                if skill.lower() in user_skills
            ]

            missing = [
                skill for skill in required_skills
                if skill.lower() not in user_skills
            ]

            percentage = (
                round(len(matched) / len(required_skills) * 100)
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
