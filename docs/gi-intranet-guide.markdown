# GI Intranet Implementation Guide

This guide provides a comprehensive implementation plan for the **GI Intranet**, a distributed, offline-first educational platform with gated access, tailored Daily Briefs, and mesh networking capabilities. It includes architecture, file structures, code scaffolds, user flows, and best practices for developers and administrators.

---

## System Architecture

### Overview
The GI Intranet is a Flask-based web application with SQLite for user profiles, Jinja2 for templating, and cron jobs for Daily Brief generation. It operates on a mesh network, prioritizing offline functionality and blackout-proof infrastructure. Access control is enforced via YAML flags (`accepted` and `paid`), and Stripe handles payments.

### System Diagram
```
[User] --> [Mesh Network] --> [GI Intranet]
  |                          |
  |                          v
  |                [Flask App: app.py]
  |                          |
  |                [Access Control]
  |                - YAML Flags
  |                - SQLite DB
  |                          |
  v                          v
[Intro Portal]       [Onboarding + Daily Brief]
  /welcome.html        - Form + Quiz
                       - Profile Generation
                       - Brief Generator (Cron)
                            |
                            v
                       [user@gi-intranet.org.html]
```

### Key Components
1. **Access Control**: Gated via `accepted: true` and `paid: true` flags.
2. **Onboarding**: Form for class preferences and knowledge quiz.
3. **Daily Brief Generator**: Pulls curated data, renders personalized HTML.
4. **Mesh Infrastructure**: Offline-first, solar/wind-powered nodes.
5. **Tooling**: Flask, SQLite, Jinja2, cron, Sphinx, Stripe.

---

## File Structure

The project follows the specified file tree for modularity and scalability.

```
gi-intranet/
├── access-control/           # Access control configs
│   ├── users.yaml            # User flags (accepted, paid)
│   └── admin.py              # Admin tools for managing users
├── apis/                     # Curated APIs
│   ├── education.json        # API endpoints for educational content
│   └── research.json         # Research API endpoints
├── sites/                    # Scrapable site lists
│   ├── blogs.csv             # Blog URLs and tags
│   └── knowledge.md          # Markdown list of resources
├── books/                    # Public-domain content
│   ├── titles.txt            # Book titles and summaries
│   └── metadata.yaml         # Book metadata
├── docs/                     # Sphinx documentation
│   ├── education.md
│   ├── plans.md
│   ├── roadmap.md
│   └── conf.py               # Sphinx config
├── infrastructure/           # Mesh and power configs
│   ├── solar.md              # Solar setup guide
│   └── wind.md               # Wind power setup
├── platform/
│   ├── git-server/           # Git server setup
│   │   └── setup.sh
│   ├── code-client/          # Offline IDE configs
│   │   └── vscode-config.json
│   ├── daily-brief/
│   │   ├── profiles/         # User profile SQLite DB
│   │   │   └── profiles.db
│   │   ├── scripts/          # Brief generation scripts
│   │   │   └── generate_brief.py
│   │   ├── templates/        # Jinja2 templates
│   │   │   └── brief.html
│   │   └── web/              # Generated briefs
│   │       └── user@gi-intranet.org.html
│   └── onboard/
│       ├── app.py            # Flask onboarding app
│       ├── templates/        # Onboarding templates
│       │   ├── welcome.html
│       │   ├── onboarding.html
│       │   └── quiz.html
│       └── submissions/      # User-submitted resumes/portfolios
│           └── user123.pdf
├── education/                # Educational resources
│   ├── curricula/
│   ├── rubrics/
│   └── exams/
├── scripts/
│   ├── setup.sh              # Project setup script
│   └── cron_daily_brief.sh   # Cron job for briefs
└── README.md
```

---

## Access Control & Gated Onboarding

### Logic
- Users start at `/welcome.html` until `accepted: true` and `paid: true`.
- Admin reviews submissions via `admin.py` and updates `users.yaml`.
- Payment is processed via Stripe, updating `paid` flag.
- Post-approval, users access onboarding and quiz forms.

### Code: Access Control (`access-control/admin.py`)

```python
import yaml
import sqlite3
from flask import Flask, request, render_template

app = Flask(__name__)

def load_users():
    with open("access-control/users.yaml", "r") as f:
        return yaml.safe_load(f) or {}

def save_users(users):
    with open("access-control/users.yaml", "w") as f:
        yaml.safe_dump(users, f)

def update_user_status(handle, accepted=None, paid=None):
    users = load_users()
    if handle not in users:
        users[handle] = {"accepted": False, "paid": False}
    if accepted is not None:
        users[handle]["accepted"] = accepted
    if paid is not None:
        users[handle]["paid"] = paid
    save_users(users)

@app.route("/admin/review", methods=["GET", "POST"])
def admin_review():
    if request.method == "POST":
        handle = request.form["handle"]
        accepted = request.form.get("accepted") == "true"
        update_user_status(handle, accepted=accepted)
        return "Updated!"
    users = load_users()
    return render_template("admin.html", users=users)

# Example SQLite for profiles
def save_profile(handle, preferences, quiz_results):
    conn = sqlite3.connect("platform/daily-brief/profiles/profiles.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO profiles (handle, preferences, quiz_results) VALUES (?, ?, ?)",
        (handle, str(preferences), str(quiz_results))
    )
    conn.commit()
    conn.close()
```

### YAML: User Flags (`access-control/users.yaml`)

```yaml
user123:
  accepted: false
  paid: false
user456:
  accepted: true
  paid: true
```

---

## Daily Brief Generator

### Logic
- A Python script (`generate_brief.py`) runs daily via cron.
- Pulls data from `apis/`, `sites/`, and `books/` based on user profile.
- Uses Jinja2 to render `user@gi-intranet.org.html` in `platform/daily-brief/web/`.

### Code: Brief Generator (`platform/daily-brief/scripts/generate_brief.py`)

```python
import sqlite3
import yaml
import requests
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import csv
import os

# Load user profiles
def get_user_profiles():
    conn = sqlite3.connect("platform/daily-brief/profiles/profiles.db")
    cursor = conn.cursor()
    cursor.execute("SELECT handle, preferences, quiz_results FROM profiles")
    profiles = cursor.fetchall()
    conn.close()
    return profiles

# Fetch curated data
def fetch_data(sources):
    data = []
    with open("sites/blogs.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["tag"] in sources:
                data.append({"title": row["title"], "url": row["url"]})
    return data

# Render brief
def render_brief(handle, preferences, quiz_results):
    env = Environment(loader=FileSystemLoader("platform/daily-brief/templates"))
    template = env.get_template("brief.html")
    data = fetch_data(preferences["classes"])
    brief_content = template.render(
        handle=handle,
        date=datetime.now().strftime("%Y-%m-%d"),
        articles=data,
        reading_level=quiz_results["reading_level"]
    )
    with open(f"platform/daily-brief/web/{handle}@gi-intranet.org.html", "w") as f:
        f.write(brief_content)

# Main
def main():
    profiles = get_user_profiles()
    for handle, preferences, quiz_results in profiles:
        users = yaml.safe_load(open("access-control/users.yaml"))
        if users.get(handle, {}).get("accepted") and users.get(handle, {}).get("paid"):
            render_brief(handle, eval(preferences), eval(quiz_results))

if __name__ == "__main__":
    main()
```

### Template: Brief (`platform/daily-brief/templates/brief.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Daily Brief for {{ handle }}</title>
</head>
<body>
    <h1>Daily Brief - {{ date }}</h1>
    <h2>Welcome, {{ handle }}!</h2>
    {% for article in articles %}
        <p><a href="{{ article.url }}">{{ article.title }}</a></p>
    {% endfor %}
</body>
</html>
```

### Cron Job (`scripts/cron_daily_brief.sh`)

```bash
#!/bin/bash
cd /path/to/gi-intranet
python3 platform/daily-brief/scripts/generate_brief.py
```

**Cron Setup**:
```bash
0 2 * * * /path/to/gi-intranet/scripts/cron_daily_brief.sh
```

---

## Onboarding System

### Logic
- Flask app (`platform/onboard/app.py`) serves `/welcome.html` for unauthenticated users.
- Post-approval, users access `/onboard` to submit preferences and quiz.
- Profile data is stored in `profiles.db`.

### Code: Onboarding App (`platform/onboard/app.py`)

```python
from flask import Flask, request, render_template, redirect
import yaml
import sqlite3

app = Flask(__name__)

def check_access(handle):
    users = yaml.safe_load(open("access-control/users.yaml"))
    return users.get(handle, {}).get("accepted") and users.get(handle, {}).get("paid")

@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/onboard", methods=["GET", "POST"])
def onboard():
    handle = request.args.get("handle")
    if not check_access(handle):
        return redirect("/")
    if request.method == "POST":
        preferences = request.form.getlist("classes")
        quiz_results = {
            "reading_level": request.form["reading_level"],
            "skill_level": request.form["skill_level"]
        }
        save_profile(handle, preferences, quiz_results)
        return redirect(f"/daily-brief/web/{handle}@gi-intranet.org.html")
    return render_template("onboarding.html")

def save_profile(handle, preferences, quiz_results):
    conn = sqlite3.connect("platform/daily-brief/profiles/profiles.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS profiles (handle TEXT PRIMARY KEY, preferences TEXT, quiz_results TEXT)"
    )
    cursor.execute(
        "INSERT OR REPLACE INTO profiles (handle, preferences, quiz_results) VALUES (?, ?, ?)",
        (handle, str(preferences), str(quiz_results))
    )
    conn.commit()
    conn.close()
```

### Template: Onboarding (`platform/onboard/templates/onboarding.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Onboarding</title>
</head>
<body>
    <h1>Onboarding Form</h1>
    <form method="POST">
        <label>Class Preferences:</label><br>
        <input type="checkbox" name="classes" value="math"> Math<br>
        <input type="checkbox" name="classes" value="science"> Science<br>
        <label>Reading Level:</label>
        <select name="reading_level">
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
        </select><br>
        <label>Skill Level:</label>
        <input type="text" name="skill_level"><br>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
```

---

## Tooling Setup

1. **Flask/FastAPI**: Flask is used for simplicity and offline compatibility.
2. **Jinja2**: For rendering Daily Briefs and onboarding templates.
3. **SQLite**: Lightweight, offline-first database for profiles.
4. **Sphinx**: Generate offline docs in `docs/` with `make html`.
5. **Cron**: Daily Brief generation at 2 AM.
6. **Stripe**: Mocked for payment processing (replace with real keys in production).
7. **Redis** (optional): Cache briefs for faster access.

### Sphinx Config (`docs/conf.py`)

```python
project = "GI Intranet"
extensions = ["sphinx.ext.autodoc"]
html_theme = "alabaster"
```

---

## User Flow

1. User joins mesh network → sees `/welcome.html`.
2. Submits resume/portfolio to `platform/onboard/submissions/`.
3. Admin reviews via `/admin/review`, sets `accepted: true`.
4. User pays via Stripe → `paid: true`.
5. User accesses `/onboard`, submits preferences and quiz.
6. Profile saved in `profiles.db`.
7. Cron generates `user@gi-intranet.org.html` daily.
8. User accesses brief at `gi-intranet.local/daily-brief/{handle}.html`.

---

## Best Practices

### Scalability
- Use SQLite for small-scale; migrate to PostgreSQL for larger deployments.
- Cache briefs in Redis for high-traffic setups.
- Modularize scripts for easy updates (e.g., separate API fetching).

### Modularity
- Keep APIs, sites, and books in separate directories for easy curation.
- Use Jinja2 partials for reusable template components.

### Privacy
- Store minimal PII in `profiles.db`.
- Encrypt `users.yaml` in production.
- Use HTTPS for mesh network communications if online.

### Offline-First
- Ensure all resources (`apis/`, `sites/`, `books/`) are cached locally.
- Use Sphinx for offline documentation access.
- Test cron jobs in blackout scenarios.

---

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone /path/to/gi-intranet
   cd gi-intranet
   ```

2. Install dependencies:
   ```bash
   pip install flask pyyaml jinja2 sqlite3 requests
   ```

3. Initialize SQLite:
   ```bash
   sqlite3 platform/daily-brief/profiles/profiles.db "CREATE TABLE profiles (handle TEXT PRIMARY KEY, preferences TEXT, quiz_results TEXT)"
   ```

4. Set up cron:
   ```bash
   crontab -e
   # Add: 0 2 * * * /path/to/gi-intranet/scripts/cron_daily_brief.sh
   ```

5. Run Flask:
   ```bash
   cd platform/onboard
   python app.py
   ```

6. Access at `gi-intranet.local:5000`.

---

This guide provides a robust foundation for the GI Intranet. Extend it with additional APIs, mesh optimizations, or advanced caching as needed.