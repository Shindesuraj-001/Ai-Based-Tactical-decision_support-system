"""
=============================================================
  routes/simulation.py — Simulation & Dashboard Routes v2.5.0
  NEW ENDPOINTS:
    • POST /api/run_simulation  — now includes strategy_comparison
    • GET  /api/simulation_steps — returns war animation data
    • POST /api/record_outcome   — saves mission outcome for AI
=============================================================
"""

import os
import uuid
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash,
    jsonify, current_app
)
from database import (
    save_simulation, get_simulation_by_id, get_user_simulations,
    save_strategy_comparisons, save_outcome, get_outcome,
    get_strategy_comparisons
)
from model import run_analysis, analyze_image, generate_simulation_steps
from functools import wraps

sim_bp = Blueprint("simulation", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this system.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────
@sim_bp.route("/dashboard")
@login_required
def dashboard():
    sims      = get_user_simulations(session["user_id"])
    total     = len(sims)
    high_risk = sum(1 for s in sims if s["risk_level"] == "High")
    avg_prob  = round(sum(s["success_prob"] for s in sims) / total, 1) if total else 0
    recent    = sims[:5]
    return render_template("dashboard.html",
        total=total, high_risk=high_risk,
        avg_prob=avg_prob, recent=recent,
        username=session.get("username"),
        rank=session.get("rank")
    )


# ─────────────────────────────────────────────
#  NEW SIMULATION FORM PAGE
# ─────────────────────────────────────────────
@sim_bp.route("/simulation")
@login_required
def simulation():
    return render_template("simulation.html",
        username=session.get("username"),
        rank=session.get("rank")
    )


# ─────────────────────────────────────────────
#  RUN SIMULATION — POST API
# ─────────────────────────────────────────────
@sim_bp.route("/api/run_simulation", methods=["POST"])
@login_required
def run_simulation():
    """
    Runs full AI analysis including multi-strategy comparison.
    Returns JSON with primary result + all 3 strategy comparisons.
    """
    try:
        mission_name = request.form.get("mission_name", "Operation Unknown")
        enemy_count  = int(request.form.get("enemy_count", 10))
        terrain      = request.form.get("terrain", "desert")
        weather      = request.form.get("weather", "clear")
        resources    = request.form.get("resources", "rifles")
        lat          = float(request.form.get("lat", 28.6139))
        lng          = float(request.form.get("lng", 77.2090))

        # ── Handle image uploads ──────────────
        upload_dir  = current_app.config["UPLOAD_FOLDER"]
        image_paths = []
        image_urls  = []

        if "images" in request.files:
            for f in request.files.getlist("images"):
                if f and f.filename:
                    ext   = os.path.splitext(f.filename)[1].lower()
                    fname = f"img_{uuid.uuid4().hex[:8]}{ext}"
                    fpath = os.path.join(upload_dir, fname)
                    f.save(fpath)
                    image_paths.append(fpath)
                    image_urls.append(f"/static/uploads/{fname}")

        # ── Run AI analysis (includes comparison) ──
        result = run_analysis(
            mission_name=mission_name,
            enemy_count=enemy_count,
            terrain=terrain,
            weather=weather,
            resources=resources,
            image_paths=image_paths
        )

        # ── Save primary simulation to database ──
        sim_id = save_simulation({
            "user_id":          session["user_id"],
            "mission_name":     mission_name,
            "enemy_count":      enemy_count,
            "terrain":          terrain,
            "weather":          weather,
            "resources":        resources,
            "primary_strategy": result["primary_strategy"],
            "alt_strategy1":    result["alt_strategy1"],
            "alt_strategy2":    result["alt_strategy2"],
            "success_prob":     result["success_prob"],
            "risk_level":       result["risk_level"],
            "risk_score":       result["risk_score"],
            "analysis_notes":   result["analysis_notes"],
            "image_paths":      ",".join(image_urls),
            "lat": lat, "lng": lng,
        })

        # ── NEW: Save strategy comparison data ──
        if result.get("strategy_comparison"):
            save_strategy_comparisons(sim_id, result["strategy_comparison"])

        result["sim_id"]     = sim_id
        result["image_urls"] = image_urls

        return jsonify({"status": "success", "result": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  NEW: WAR SIMULATION STEPS API
# ─────────────────────────────────────────────
@sim_bp.route("/api/simulation_steps")
@login_required
def simulation_steps():
    """
    Returns step-by-step animation data for the war simulation map.
    Parameters: lat, lng, terrain, weather, enemy_count, strategy_type
    """
    try:
        lat           = float(request.args.get("lat", 28.6139))
        lng           = float(request.args.get("lng", 77.2090))
        terrain       = request.args.get("terrain", "desert")
        weather       = request.args.get("weather", "clear")
        enemy_count   = int(request.args.get("enemy_count", 10))
        strategy_type = request.args.get("strategy_type", "aggressive")

        steps = generate_simulation_steps(
            terrain=terrain, weather=weather, enemy_count=enemy_count,
            lat=lat, lng=lng, strategy_type=strategy_type
        )
        return jsonify({"status": "success", "data": steps})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  NEW: RECORD OUTCOME (AI Learning Feed)
# ─────────────────────────────────────────────
@sim_bp.route("/api/record_outcome", methods=["POST"])
@login_required
def record_outcome():
    """
    Records whether a deployed strategy succeeded or failed.
    This data is used by the AI learning system to improve
    future probability predictions for similar scenarios.
    """
    try:
        data    = request.json
        sim_id  = data.get("sim_id")
        outcome = data.get("outcome")   # 'success' | 'failure' | 'partial'
        feedback= data.get("feedback", "")

        if outcome not in ("success", "failure", "partial"):
            return jsonify({"status": "error", "message": "Invalid outcome"}), 400

        # Verify this simulation belongs to the current user
        sim = get_simulation_by_id(sim_id, session["user_id"])
        if not sim:
            return jsonify({"status": "error", "message": "Not found"}), 404

        save_outcome({"sim_id": sim_id, "outcome": outcome, "feedback": feedback})
        return jsonify({"status": "saved", "message": "Outcome recorded. AI model will adapt."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────
#  VIEW SINGLE SIMULATION RESULT PAGE
# ─────────────────────────────────────────────
@sim_bp.route("/result/<int:sim_id>")
@login_required
def result(sim_id):
    sim = get_simulation_by_id(sim_id, session["user_id"])
    if not sim:
        flash("Simulation not found.", "error")
        return redirect(url_for("simulation.dashboard"))

    sim["images"]              = [p for p in sim.get("image_paths", "").split(",") if p]
    sim["strategy_comparison"] = get_strategy_comparisons(sim_id)   # NEW
    sim["outcome"]             = get_outcome(sim_id)                  # NEW

    return render_template("result.html", sim=sim,
        username=session.get("username"),
        rank=session.get("rank")
    )


# ─────────────────────────────────────────────
#  API: Get simulation data (for JS fetch)
# ─────────────────────────────────────────────
@sim_bp.route("/api/simulation/<int:sim_id>")
@login_required
def api_simulation(sim_id):
    sim = get_simulation_by_id(sim_id, session["user_id"])
    if not sim:
        return jsonify({"error": "Not found"}), 404
    return jsonify(sim)