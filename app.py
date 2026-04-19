import io
import json
import os
import random
from datetime import datetime, timezone

from flask import Flask, render_template, request, session, make_response
from dotenv import load_dotenv

from profiler import build_profile

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))


def _int_or_none(value: str):
    """Return integer if value is a non-empty digit string, else None."""
    v = value.strip() if value else ""
    return int(v) if v.isdigit() else None


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/dashboard", methods=["GET", "POST"])
def index():
    profile = None
    error = None
    form = {}

    if request.method == "POST":
        form = request.form
        name = form.get("name", "").strip()
        city = form.get("city", "").strip() or None
        domain = form.get("domain", "").strip() or None
        exact_age = _int_or_none(form.get("exact_age", ""))
        min_age = _int_or_none(form.get("min_age", ""))
        max_age = _int_or_none(form.get("max_age", ""))

        debug = request.args.get("debug", "0") == "1"

        if not name:
            error = "Name is required."
        else:
            try:
                profile = build_profile(
                    entity_name=name,
                    city=city,
                    domain=domain,
                    exact_age=exact_age,
                    min_age=min_age,
                    max_age=max_age,
                    debug=debug,
                )
                # Store for PDF export
                session["last_profile"] = profile
            except Exception as e:
                error = f"Failed to build profile: {e}"

    return render_template("index.html", profile=profile, error=error, form=form)


@app.route("/export-pdf")
def export_pdf():
    from weasyprint import HTML

    profile = session.get("last_profile")
    if not profile:
        return "No profile in session. Generate a profile first.", 400

    report_id = "RPT-{}-{:03d}".format(
        datetime.now(timezone.utc).strftime("%Y%m%d"),
        random.randint(100, 999),
    )

    html_string = render_template("pdf_report.html", profile=profile, report_id=report_id)
    pdf_bytes = HTML(string=html_string).write_pdf()

    entity_slug = profile["entity_name"].replace(" ", "_")
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"OSINT_{entity_slug}_{date_slug}.pdf"

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
