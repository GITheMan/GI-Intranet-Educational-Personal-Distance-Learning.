import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
import yaml
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change in production!

USERS_FILE = "users.yaml"

# Load users data
def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}}
    with open(USERS_FILE, "r") as f:
        return yaml.safe_load(f) or {"users": {}}

def save_users(data):
    with open(USERS_FILE, "w") as f:
        yaml.dump(data, f)

data = load_users()
users = data["users"]

# QUESTIONS for evaluation
QUESTIONS = [
    {
        "id": "q1",
        "question": "What is 2 + 2?",
        "choices": ["3", "4", "5"],
        "answer": "4"
    },
    {
        "id": "q2",
        "question": "What color is the sky?",
        "choices": ["Blue", "Green", "Red"],
        "answer": "Blue"
    },
    {
        "id": "q3",
        "question": "Is GI Intranet offline-first?",
        "choices": ["Yes", "No"],
        "answer": "Yes"
    }
]

# ------------- ROUTES -------------

@app.route("/")
def index():
    if "username" in session:
        user = users.get(session["username"])
        if user:
            if user.get("status") != "approved":
                return redirect(url_for("pending"))
            if not user.get("paid", False):
                return redirect(url_for("payment"))
            return redirect(url_for("dashboard"))
    return render_template("index.html")


# Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")
        if not username or not password or not confirm:
            flash("Please fill all fields.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if username in users:
            flash("Username already exists.", "error")
            return redirect(url_for("register"))
        # Create user
        users[username] = {
            "password": generate_password_hash(password),
            "role": "user",
            "status": "pending_evaluation",
            "evaluation_score": 0,
            "paid": False
        }
        save_users({"users": users})
        session["username"] = username
        flash("Registration successful! Please take the evaluation test.", "success")
        return redirect(url_for("evaluation"))
    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        user = users.get(username)
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


# Evaluation test
@app.route("/evaluation", methods=["GET", "POST"])
def evaluation():
    if "username" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))
    user = users.get(session["username"])
    if not user or user.get("status") != "pending_evaluation":
        flash("You are not eligible to take the evaluation.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        answers = {}
        for q in QUESTIONS:
            ans = request.form.get(q["id"])
            if ans:
                answers[q["id"]] = ans
            else:
                flash("Please answer all questions.", "error")
                return redirect(url_for("evaluation"))

        # Score calculation
        correct = 0
        for q in QUESTIONS:
            if answers.get(q["id"]) == q["answer"]:
                correct += 1
        score = int((correct / len(QUESTIONS)) * 100)

        # Update user status based on score
        user["evaluation_score"] = score
        if score >= 70:
            user["status"] = "pending_approval"
            flash(f"Congratulations! You passed with {score}%. Awaiting admin approval.", "success")
        else:
            user["status"] = "pending_evaluation"
            flash(f"Unfortunately, you scored {score}%. Please try again.", "error")
        save_users({"users": users})
        return redirect(url_for("index"))

    return render_template("evaluation.html", questions=QUESTIONS)


# Pending approval page
@app.route("/pending")
def pending():
    if "username" not in session:
        return redirect(url_for("login"))
    user = users.get(session["username"])
    if user and user.get("status") == "pending_approval":
        return render_template("pending.html")
    return redirect(url_for("index"))


# Admin approval panel
@app.route("/admin/approvals", methods=["GET", "POST"])
def admin_approvals():
    if "username" not in session:
        flash("Please login as admin.", "error")
        return redirect(url_for("login"))
    admin_user = users.get(session["username"])
    if not admin_user or admin_user.get("role") != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("index"))

    pending_users = {
        u: v for u, v in users.items() if v.get("status") == "pending_approval"
    }

    if request.method == "POST":
        target_user = request.form.get("username")
        action = request.form.get("action")
        if target_user in users:
            if action == "approve":
                users[target_user]["status"] = "approved"
                flash(f"User {target_user} approved.", "success")
            elif action == "reject":
                users[target_user]["status"] = "rejected"
                flash(f"User {target_user} rejected.", "info")
            save_users({"users": users})
        return redirect(url_for("admin_approvals"))

    return render_template("admin_approvals.html", pending_users=pending_users)


# Dashboard (protected)
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))
    user = users.get(session["username"])
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("login"))
    if user.get("status") != "approved":
        flash("Your account is not approved yet.", "error")
        return redirect(url_for("pending"))
    if not user.get("paid", False):
        flash("Payment required to access dashboard.", "error")
        return redirect(url_for("payment"))
    return render_template("dashboard.html", username=session["username"])


# Payment placeholder
@app.route("/payment", methods=["GET", "POST"])
def payment():
    if "username" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))
    user = users.get(session["username"])
    if request.method == "POST":
        # Placeholder: mark user as paid
        user["paid"] = True
        save_users({"users": users})
        flash("Payment successful! Access granted.", "success")
        return redirect(url_for("dashboard"))
    return render_template("payment.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
