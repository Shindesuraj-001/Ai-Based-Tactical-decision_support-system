"""
=============================================================
  AI-Based Tactical Decision Support System
  Indian Army | National Defence Project
  app.py — Main Flask Application Entry Point v2.6.0
  UPDATED: Added battlefield_bp (3D view + satellite map APIs)
=============================================================
"""

from flask import Flask
from flask_session import Session
import os
from database import init_db
from routes.auth       import auth_bp
from routes.simulation import sim_bp
from routes.history    import history_bp
from routes.weather    import weather_bp
from routes.report     import report_bp
from routes.battlefield import battlefield_bp   # ← NEW v2.6.0

# ─────────────────────────────────────────────
#  Flask App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)

app.secret_key = "ARMY_TACTICAL_SECRET_KEY_2024_INDIA"

app.config["SESSION_TYPE"]        = "filesystem"
app.config["SESSION_FILE_DIR"]    = os.path.join(os.getcwd(), "flask_session")
app.config["SESSION_PERMANENT"]   = False
app.config["UPLOAD_FOLDER"]       = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"]  = 16 * 1024 * 1024  # 16 MB

# ── OpenWeatherMap API Key ─────────────────────
app.config["OPENWEATHER_API_KEY"] = os.environ.get(
    "OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE"
)

Session(app)

# ─────────────────────────────────────────────
#  Ensure required folders exist
# ─────────────────────────────────────────────
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("flask_session", exist_ok=True)

# ─────────────────────────────────────────────
#  Register Blueprints
# ─────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(sim_bp)
app.register_blueprint(history_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(report_bp)
app.register_blueprint(battlefield_bp)   # ← NEW v2.6.0

# ─────────────────────────────────────────────
#  Initialize Database on startup
# ─────────────────────────────────────────────
with app.app_context():
    init_db()

# ─────────────────────────────────────────────
#  Run the Application
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  🪖  TACTICAL DECISION SUPPORT SYSTEM v2.6.0 — INDIA")
    print("  🌐  Running at: http://127.0.0.1:5000")
    print("  🆕  v2.6.0 additions:")
    print("       • 3D Battlefield Visualization (Three.js)")
    print("       • Satellite Map + Heatmap + Routes (Leaflet)")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)