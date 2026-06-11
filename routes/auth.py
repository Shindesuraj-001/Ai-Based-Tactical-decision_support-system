"""
=============================================================
  routes/auth.py — Authentication Routes
  Handles login, logout, and session management.
=============================================================
"""

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from database import get_user

auth_bp = Blueprint("auth", __name__)

# ─────────────────────────────────────────────
#  LOGIN PAGE
# ─────────────────────────────────────────────
@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Show login page; process credentials on POST."""

    # Already logged in → go to dashboard
    if "user_id" in session:
        return redirect(url_for("simulation.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = get_user(username)

        if user and user["password"] == password:
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["rank"]     = user["rank"]
            flash(
                "Login successful. Welcome, " + user["rank"] + " " + user["username"] + "!",
                "success"
            )
            return redirect(url_for("simulation.dashboard"))
        else:
            flash("Invalid credentials. Access denied.", "error")

    return render_template("login.html")


# ─────────────────────────────────────────────
#  LOGOUT
# ─────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))