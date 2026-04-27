import json
import os
import random
import uuid
from datetime import datetime, timezone

from flask import Flask, render_template, request, make_response, jsonify
from dotenv import load_dotenv

from profiler import build_profile
from connectors.nlq_connector import parse_nlq

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Server-side profile cache — avoids cookie-size limits that break PDF export
_profile_cache = {}


def _int_or_none(value: str):
    v = value.strip() if value else ""
    return int(v) if v.isdigit() else None


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/dashboard", methods=["GET", "POST"])
def index():
    profile = None
    profile_id = None
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
                profile_id = str(uuid.uuid4())
                _profile_cache[profile_id] = profile

                # Keep cache from growing unbounded
                if len(_profile_cache) > 100:
                    for k in list(_profile_cache.keys())[:50]:
                        del _profile_cache[k]

            except Exception as e:
                error = f"Failed to build profile: {e}"

    return render_template(
        "index.html",
        profile=profile,
        profile_id=profile_id,
        error=error,
        form=form,
    )


@app.route("/export-pdf/<profile_id>")
def export_pdf(profile_id):
    from weasyprint import HTML

    profile = _profile_cache.get(profile_id)
    if not profile:
        return (
            "Profile not found or expired. Please generate a new profile first.",
            404,
        )

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


@app.route("/nlq", methods=["POST"])
def nlq_query():
    user_query = request.form.get("nlq_query", "").strip()
    if not user_query:
        return jsonify({"intent": "unclear", "interpretation": "Empty query"})

    try:
        history = json.loads(request.form.get("history_json", "[]"))
    except (ValueError, TypeError):
        history = []

    parsed = parse_nlq(user_query, history)
    return jsonify(parsed)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
