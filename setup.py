#!/usr/bin/env python3
"""
=============================================================
  ATDSS v2.5.0 — Quick Setup Script
  Run once to prepare the project environment.
  Usage: python setup.py
=============================================================
"""

import os
import sys
import subprocess

print("=" * 60)
print("  🪖  ATDSS v2.5.0 — TACTICAL DECISION SUPPORT SYSTEM")
print("  Setup Script")
print("=" * 60)

# ── Check Python version ──────────────────────────────────────
if sys.version_info < (3, 8):
    print("❌ Python 3.8+ required. Please upgrade Python.")
    sys.exit(1)
print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

# ── Create directories ────────────────────────────────────────
dirs = [
    "static/uploads",
    "static/css",
    "static/js",
    "flask_session",
    "routes",
    "templates",
]
for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"✅ Directory ready: {d}")

# ── Install dependencies ──────────────────────────────────────
print("\n📦 Installing Python packages...")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
    capture_output=False
)
if result.returncode != 0:
    print("⚠ Some packages failed. Trying core packages only...")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "flask", "flask-session", "requests", "reportlab"
    ])

# ── Initialize database ───────────────────────────────────────
print("\n🗄  Initializing database v2.5.0...")
try:
    from database import init_db
    init_db()
    print("✅ Database created successfully (includes new tables)")
except Exception as e:
    print(f"⚠ Database init error: {e}")

# ── Check optional weather API ────────────────────────────────
print("\n🌦  Weather API Status:")
api_key = os.environ.get("OPENWEATHER_API_KEY", "")
if api_key and api_key != "YOUR_API_KEY_HERE":
    print(f"✅ OPENWEATHER_API_KEY found in environment.")
else:
    print("⚠  No OPENWEATHER_API_KEY set — weather will run in demo mode.")
    print("   To enable live weather:")
    print("   1. Get free key: https://openweathermap.org/api")
    print("   2. Set: export OPENWEATHER_API_KEY='your_key'")
    print("      OR edit app.py → app.config['OPENWEATHER_API_KEY']")

print("\n" + "=" * 60)
print("  ✅ SETUP COMPLETE — ATDSS v2.5.0")
print()
print("  🚀 Start server:   python app.py")
print("  🌐 Open browser:   http://127.0.0.1:5000")
print("  👤 Login:          admin / admin123")
print()
print("  🆕 New features:")
print("     • Multi-Strategy Comparison Table")
print("     • War Simulation Map Animation")
print("     • AI Learning from Mission Outcomes")
print("     • Real-Time Weather Auto-Detection")
print("     • Professional PDF Report Download")
print("=" * 60)