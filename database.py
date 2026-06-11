"""
=============================================================
  database.py — SQLite Database Initialization & Helpers
  v2.5.0 — Added: strategy_comparisons, simulation_outcomes
=============================================================
"""

import sqlite3
import os

DB_PATH = "database.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all required tables if they don't already exist."""
    conn = get_db()
    cursor = conn.cursor()

    # ── Users Table ───────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            rank       TEXT    DEFAULT 'Officer',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Simulations Table ─────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id                INTEGER  PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER  NOT NULL,
            mission_name      TEXT     NOT NULL,
            enemy_count       INTEGER  NOT NULL,
            terrain           TEXT     NOT NULL,
            weather           TEXT     NOT NULL,
            resources         TEXT     NOT NULL,
            primary_strategy  TEXT     NOT NULL,
            alt_strategy1     TEXT,
            alt_strategy2     TEXT,
            success_prob      REAL     NOT NULL,
            risk_level        TEXT     NOT NULL,
            risk_score        REAL     NOT NULL,
            analysis_notes    TEXT,
            image_paths       TEXT     DEFAULT '',
            lat               REAL     DEFAULT 28.6139,
            lng               REAL     DEFAULT 77.2090,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ── NEW: Strategy Comparisons Table ───────
    # Stores all 3 strategy types per simulation for comparison
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategy_comparisons (
            id              INTEGER  PRIMARY KEY AUTOINCREMENT,
            sim_id          INTEGER  NOT NULL,
            strategy_type   TEXT     NOT NULL,
            strategy_name   TEXT     NOT NULL,
            success_prob    REAL     NOT NULL,
            risk_level      TEXT     NOT NULL,
            risk_score      REAL     NOT NULL,
            estimated_time  TEXT     NOT NULL,
            resource_usage  TEXT     NOT NULL,
            is_recommended  INTEGER  DEFAULT 0,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sim_id) REFERENCES simulations(id) ON DELETE CASCADE
        )
    """)

    # ── NEW: Simulation Outcomes Table ────────
    # Stores feedback on whether a strategy succeeded (for AI learning)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_outcomes (
            id             INTEGER  PRIMARY KEY AUTOINCREMENT,
            sim_id         INTEGER  NOT NULL,
            outcome        TEXT     NOT NULL,   -- 'success' | 'failure' | 'partial'
            feedback_notes TEXT     DEFAULT '',
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sim_id) REFERENCES simulations(id) ON DELETE CASCADE
        )
    """)

    # ── Default users ──────────────────────────
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, rank)
        VALUES ('admin', 'admin123', 'General')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, rank)
        VALUES ('officer1', 'officer123', 'Colonel')
    """)

    conn.commit()
    conn.close()
    print("[DB] Database v2.5.0 initialized successfully.")


# ─────────────────────────────────────────────
#  Helper: Fetch user by username
# ─────────────────────────────────────────────
def get_user(username):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return user


# ─────────────────────────────────────────────
#  Helper: Save simulation result
# ─────────────────────────────────────────────
def save_simulation(data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO simulations
        (user_id, mission_name, enemy_count, terrain, weather, resources,
         primary_strategy, alt_strategy1, alt_strategy2,
         success_prob, risk_level, risk_score, analysis_notes,
         image_paths, lat, lng)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["user_id"], data["mission_name"], data["enemy_count"],
        data["terrain"], data["weather"], data["resources"],
        data["primary_strategy"], data.get("alt_strategy1", ""),
        data.get("alt_strategy2", ""),
        data["success_prob"], data["risk_level"], data["risk_score"],
        data["analysis_notes"], data.get("image_paths", ""),
        data.get("lat", 28.6139), data.get("lng", 77.2090)
    ))
    sim_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sim_id


# ─────────────────────────────────────────────
#  NEW: Save strategy comparison data
# ─────────────────────────────────────────────
def save_strategy_comparisons(sim_id, comparisons):
    """Save all 3 strategy comparisons for a simulation."""
    conn = get_db()
    cursor = conn.cursor()
    for c in comparisons:
        cursor.execute("""
            INSERT INTO strategy_comparisons
            (sim_id, strategy_type, strategy_name, success_prob, risk_level,
             risk_score, estimated_time, resource_usage, is_recommended)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            sim_id,
            c["strategy_type"], c["strategy_name"],
            c["success_prob"], c["risk_level"], c["risk_score"],
            c["estimated_time"], c["resource_usage"],
            1 if c["is_recommended"] else 0
        ))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  NEW: Fetch strategy comparisons for a sim
# ─────────────────────────────────────────────
def get_strategy_comparisons(sim_id):
    """Get all strategy comparisons for a simulation."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM strategy_comparisons WHERE sim_id = ? ORDER BY success_prob DESC",
        (sim_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  NEW: Save simulation outcome (for learning)
# ─────────────────────────────────────────────
def save_outcome(data):
    """Record whether a mission strategy succeeded or failed."""
    conn = get_db()
    # Only one outcome per simulation
    conn.execute("DELETE FROM simulation_outcomes WHERE sim_id = ?", (data["sim_id"],))
    conn.execute("""
        INSERT INTO simulation_outcomes (sim_id, outcome, feedback_notes)
        VALUES (?, ?, ?)
    """, (data["sim_id"], data["outcome"], data.get("feedback", "")))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  NEW: Get outcome for a simulation
# ─────────────────────────────────────────────
def get_outcome(sim_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM simulation_outcomes WHERE sim_id = ?", (sim_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
#  NEW: Get historical outcomes for learning
# ─────────────────────────────────────────────
def get_historical_outcomes(terrain, weather, limit=20):
    """Fetch past outcomes for similar terrain/weather for AI learning."""
    conn = get_db()
    rows = conn.execute("""
        SELECT so.outcome, s.success_prob, s.enemy_count, s.resources
        FROM simulation_outcomes so
        JOIN simulations s ON so.sim_id = s.id
        WHERE s.terrain = ? AND s.weather = ?
        ORDER BY so.created_at DESC
        LIMIT ?
    """, (terrain.lower(), weather.lower(), limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  Helper: Fetch all simulations for a user
# ─────────────────────────────────────────────
def get_user_simulations(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM simulations WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  Helper: Fetch single simulation by ID
# ─────────────────────────────────────────────
def get_simulation_by_id(sim_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM simulations WHERE id = ? AND user_id = ?",
        (sim_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None