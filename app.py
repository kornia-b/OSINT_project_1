from flask import Flask, render_template, request

from dotenv import load_dotenv
from profiler import build_profile

load_dotenv()

app = Flask(__name__)


def _int_or_none(value: str):
    """Return integer if value is a non-empty digit string, else None."""
    v = value.strip() if value else ""
    return int(v) if v.isdigit() else None


@app.route("/", methods=["GET", "POST"])
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
            except Exception as e:
                error = f"Failed to build profile: {e}"

    return render_template("index.html", profile=profile, error=error, form=form)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
