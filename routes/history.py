"""
=============================================================
  routes/history.py — Simulation History Routes v2.5.0
  View all past simulations, delete, export to PDF (JS side).
  No changes from v1 except minor import update.
=============================================================
"""

from flask import (
    Blueprint, render_template, session,
    redirect, url_for, flash, jsonify
)
from database import get_user_simulations, get_simulation_by_id, get_db
from functools import wraps

history_bp = Blueprint("history", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  HISTORY PAGE
# ─────────────────────────────────────────────
@history_bp.route("/history")
@login_required
def history():
    """Show all past simulations for logged-in user."""
    sims = get_user_simulations(session["user_id"])
    return render_template(
        "history.html", sims=sims,
        username=session.get("username"),
        rank=session.get("rank")
    )


# ─────────────────────────────────────────────
#  API: Delete a simulation
# ─────────────────────────────────────────────
@history_bp.route("/api/delete_simulation/<int:sim_id>", methods=["DELETE"])
@login_required
def delete_simulation(sim_id):
    """Delete a simulation record (only if owned by session user)."""
    conn = get_db()
    conn.execute(
        "DELETE FROM simulations WHERE id = ? AND user_id = ?",
        (sim_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})


# ─────────────────────────────────────────────
#  API: All simulations as JSON (for charts)
# ─────────────────────────────────────────────
@history_bp.route("/api/history_data")
@login_required
def history_data():
    """Return all simulations as JSON for chart rendering."""
    sims = get_user_simulations(session["user_id"])
    return jsonify(sims)