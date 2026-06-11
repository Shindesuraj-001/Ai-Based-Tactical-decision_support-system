"""
=============================================================
  routes/battlefield.py — 3D Battlefield + Enhanced Map APIs
  v4.0.0 — UPGRADED:
    • /api/battlefield_data now accepts friendly_count param
    • Cluster-spread enemy positions for noise terrain
    • Paths pinned to terrain-aware waypoints
=============================================================
"""

import random
from flask import (
    Blueprint, jsonify, request,
    render_template, session, redirect, url_for
)
from functools import wraps

battlefield_bp = Blueprint("battlefield", __name__)


# ─── Auth guard ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════
#  PAGE: 3D Battlefield Viewer
# ═══════════════════════════════════════════════════════════
@battlefield_bp.route("/battlefield3d")
@login_required
def battlefield3d():
    """Serve the Three.js 3D battlefield visualization page."""
    return render_template(
        "battlefield3d.html",
        username=session.get("username"),
        rank=session.get("rank"),
    )


# ═══════════════════════════════════════════════════════════
#  API: 3D Scene Data  →  /api/battlefield_data
# ═══════════════════════════════════════════════════════════
@battlefield_bp.route("/api/battlefield_data")
@login_required
def battlefield_data():
    """
    Returns unit positions, paths, and terrain features so
    the Three.js front-end can build the 3D scene.

    Query params:
      terrain          desert | forest | urban | mountain
      enemy_count      int  (capped at 50)
      strategy_type    aggressive | defensive | stealth
      friendly_count   int  (capped at 20, default 8)  ← NEW v4.0
    """
    terrain         = request.args.get("terrain", "desert")
    enemy_count     = min(int(request.args.get("enemy_count", 20)), 50)
    strategy        = request.args.get("strategy_type", "aggressive")
    friendly_count  = min(int(request.args.get("friendly_count", 8)), 20)  # ← NEW

    # ── Enemy clusters ──────────────────────────────────────
    enemies = []
    cluster_origins = [(-30, -20), (0, -45), (30, -25), (-15, -55), (20, -10)]
    for i in range(enemy_count):
        cx, cz = cluster_origins[i % len(cluster_origins)]
        enemies.append({
            "id":     i,
            "x":      round(cx + random.uniform(-22, 22), 2),
            "y":      0,
            "z":      round(cz + random.uniform(-14, 14), 2),
            "type":   random.choice(["infantry", "armor", "artillery"]),
            "health": random.randint(50, 100),
        })

    # ── Friendly units — sized by friendly_count param ──────
    unit_types_pool = [
        "infantry", "armor", "sf", "sniper",
        "infantry", "armor", "sf", "infantry",
        "infantry", "sniper", "armor", "sf",
        "infantry", "infantry", "armor", "sniper",
        "sf", "infantry", "infantry", "armor",
    ]
    friendly = []
    for i in range(friendly_count):
        utype = unit_types_pool[i % len(unit_types_pool)]
        friendly.append({
            "id":   i,
            "x":    round(-40 + i * (80 / max(friendly_count - 1, 1)) + random.uniform(-3, 3), 2),
            "y":    0,
            "z":    round(70 + random.uniform(-8, 8), 2),
            "type": utype,
        })

    # ── Approach paths ──────────────────────────────────────
    paths = _build_paths(strategy, friendly)

    # ── Terrain features ────────────────────────────────────
    features = _build_features(terrain)

    return jsonify({
        "status":           "success",
        "terrain":          terrain,
        "strategy_type":    strategy,
        "enemies":          enemies,
        "friendly":         friendly,
        "paths":            paths,
        "terrain_features": features,
        "objective":        {"x": 0, "y": 0, "z": -40},
        "map_size":         200,
    })


# ──────────────────────────────────────────────────────────
def _build_paths(strategy, friendly):
    """Return movement-path waypoints for each friendly unit."""
    colors = {
        "aggressive": "#ef4444",
        "defensive":  "#4b7ac8",
        "stealth":    "#22c55e",
    }
    color = colors.get(strategy, "#c8a84b")
    paths = []

    for i, unit in enumerate(friendly[:6]):
        sx, sz = unit["x"], unit["z"]

        if strategy == "aggressive":
            pts = [
                {"x": sx,        "z": sz},
                {"x": sx * 0.6,  "z": sz * 0.5},
                {"x": sx * 0.2,  "z": 0},
                {"x": sx * 0.05, "z": -40},
            ]
        elif strategy == "stealth":
            side = 90 if i % 2 == 0 else -90
            pts = [
                {"x": sx,          "z": sz},
                {"x": side,        "z": 30},
                {"x": side * 0.75, "z": -10},
                {"x": side * 0.25, "z": -40},
            ]
        else:  # defensive
            pts = [
                {"x": sx,        "z": sz},
                {"x": sx * 0.9,  "z": 45},
                {"x": sx * 0.7,  "z": 20},
                {"x": sx * 0.5,  "z": 5},
            ]

        paths.append({"unit_id": unit["id"], "points": pts, "color": color})

    return paths


# ──────────────────────────────────────────────────────────
def _build_features(terrain):
    """Generate scenery objects appropriate for the terrain type."""
    obj_type = {
        "desert":   "rock",
        "forest":   "tree",
        "urban":    "building",
        "mountain": "cliff",
    }.get(terrain, "rock")

    features = []
    for _ in range(6):
        features.append({
            "type":  "hill",
            "x":     round(random.uniform(-80, 80), 2),
            "z":     round(random.uniform(-80, 80), 2),
            "scale": round(random.uniform(0.6, 1.8), 2),
        })
    for _ in range(14):
        x = random.uniform(-88, 88)
        z = random.uniform(-88, 88)
        if abs(x) < 14 and abs(z) < 14:
            continue
        features.append({
            "type":  obj_type,
            "x":     round(x, 2),
            "z":     round(z, 2),
            "scale": round(random.uniform(0.5, 1.6), 2),
        })

    return features


# ═══════════════════════════════════════════════════════════
#  API: Enhanced Map Data  →  /api/map_data
# ═══════════════════════════════════════════════════════════
@battlefield_bp.route("/api/map_data")
@login_required
def map_data():
    """
    Returns geo-referenced data for the satellite/enhanced Leaflet map.
    Includes enemy positions, approach routes, danger zones, heatmap.
    """
    lat         = float(request.args.get("lat", 28.6139))
    lng         = float(request.args.get("lng", 77.2090))
    enemy_count = min(int(request.args.get("enemy_count", 20)), 30)
    terrain     = request.args.get("terrain", "desert")

    # ── Enemy scatter ──────────────────────────────────────
    enemies = []
    for i in range(enemy_count):
        enemies.append({
            "id":       i,
            "lat":      round(lat + random.uniform(-0.10, 0.10), 6),
            "lng":      round(lng + random.uniform(-0.10, 0.10), 6),
            "type":     random.choice(["infantry", "armor", "artillery"]),
            "strength": random.randint(4, 25),
        })

    # ── Three approach routes ──────────────────────────────
    routes = [
        {
            "name":   "ALPHA — Direct Assault",
            "color":  "#22c55e",
            "weight": 4,
            "dash":   "8, 5",
            "points": [
                {"lat": lat + 0.20, "lng": lng - 0.04},
                {"lat": lat + 0.12, "lng": lng - 0.01},
                {"lat": lat + 0.03, "lng": lng},
                {"lat": lat,        "lng": lng},
            ],
        },
        {
            "name":   "BRAVO — Eastern Flank",
            "color":  "#4b7ac8",
            "weight": 3,
            "dash":   "6, 4",
            "points": [
                {"lat": lat + 0.22, "lng": lng + 0.16},
                {"lat": lat + 0.14, "lng": lng + 0.11},
                {"lat": lat + 0.05, "lng": lng + 0.05},
                {"lat": lat,        "lng": lng},
            ],
        },
        {
            "name":   "CHARLIE — Stealth Western",
            "color":  "#c8a84b",
            "weight": 2,
            "dash":   "4, 8",
            "points": [
                {"lat": lat + 0.24, "lng": lng - 0.20},
                {"lat": lat + 0.16, "lng": lng - 0.15},
                {"lat": lat + 0.07, "lng": lng - 0.09},
                {"lat": lat + 0.01, "lng": lng - 0.02},
                {"lat": lat,        "lng": lng},
            ],
        },
    ]

    # ── Danger zones ───────────────────────────────────────
    zone_types = ["artillery_range", "patrol_zone", "minefield",
                  "sniper_nest", "ambush_point"]
    danger_zones = []
    for _ in range(min(6, enemy_count // 4 + 2)):
        danger_zones.append({
            "lat":       round(lat + random.uniform(-0.08, 0.08), 6),
            "lng":       round(lng + random.uniform(-0.08, 0.08), 6),
            "radius":    random.randint(1200, 4800),
            "intensity": random.choice(["Low", "Medium", "High"]),
            "type":      random.choice(zone_types),
        })

    # ── Heatmap points ─────────────────────────────────────
    heatmap_points = []
    for e in enemies:
        intensity = e["strength"] / 25.0
        for _ in range(random.randint(4, 10)):
            heatmap_points.append([
                round(e["lat"] + random.uniform(-0.025, 0.025), 6),
                round(e["lng"] + random.uniform(-0.025, 0.025), 6),
                round(intensity * random.uniform(0.3, 1.0), 3),
            ])

    return jsonify({
        "status":          "success",
        "location":        {"lat": lat, "lng": lng},
        "terrain":         terrain,
        "enemies":         enemies,
        "routes":          routes,
        "danger_zones":    danger_zones,
        "heatmap_points":  heatmap_points,
    })