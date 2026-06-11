"""
=============================================================
  model.py — AI Tactical Strategy Engine v2.5.0
  NEW FEATURES:
    • Multi-Strategy Comparison (Aggressive / Defensive / Stealth)
    • AI Learning System (adjusts predictions from past outcomes)
    • War Simulation Step Generator
=============================================================
"""

import os
import random
import math
from database import get_historical_outcomes

# ─────────────────────────────────────────────
#  OpenCV import (optional — graceful fallback)
# ─────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("[MODEL] OpenCV not found — image analysis will use mock data.")


# ═══════════════════════════════════════════════════════════
#  SECTION 1 — ORIGINAL KNOWLEDGE BASE (unchanged)
# ═══════════════════════════════════════════════════════════

STRATEGY_RULES = [
    {"conditions": {"terrain": "desert",   "weather": "clear", "enemy_min": 1,  "enemy_max": 20},
     "primary": "Swift Cavalry Strike", "alt1": "Armoured Column Advance",
     "alt2": "Artillery Suppression then Advance", "base_prob": 72, "risk": "Medium"},

    {"conditions": {"terrain": "desert",   "weather": "fog",   "enemy_min": 1,  "enemy_max": 50},
     "primary": "Fog-Cover Flanking Manoeuvre", "alt1": "Sniper Overwatch + Infantry Push",
     "alt2": "Delayed Dawn Strike", "base_prob": 68, "risk": "Medium"},

    {"conditions": {"terrain": "desert",   "weather": "clear", "enemy_min": 21, "enemy_max": 999},
     "primary": "Artillery Suppression + Air Strike Coordination",
     "alt1": "Pincer Movement with Armoured Support",
     "alt2": "Draw and Encircle (Trap Formation)", "base_prob": 55, "risk": "High"},

    {"conditions": {"terrain": "urban",    "weather": "night", "enemy_min": 1,  "enemy_max": 15},
     "primary": "Night Stealth Infiltration", "alt1": "Sniper Nest Setup + Precision Strike",
     "alt2": "Building-by-Building Sweep", "base_prob": 78, "risk": "Low"},

    {"conditions": {"terrain": "urban",    "weather": "fog",   "enemy_min": 1,  "enemy_max": 30},
     "primary": "Fog + Smoke Grenade Urban Assault", "alt1": "Rooftop Sniper Network",
     "alt2": "Underground Tunnel Access", "base_prob": 65, "risk": "Medium"},

    {"conditions": {"terrain": "urban",    "weather": "clear", "enemy_min": 1,  "enemy_max": 999},
     "primary": "Tactical Urban Breach & Clear",
     "alt1": "Perimeter Lockdown + Targeted Breach",
     "alt2": "Civilian Evacuation then Area Denial", "base_prob": 60, "risk": "High"},

    {"conditions": {"terrain": "forest",   "weather": "rain",  "enemy_min": 1,  "enemy_max": 25},
     "primary": "Guerrilla Ambush in Rain Cover",
     "alt1": "Camouflage Sniper Units + Forward Push",
     "alt2": "Noise-Suppressed Night Patrol Strike", "base_prob": 80, "risk": "Low"},

    {"conditions": {"terrain": "forest",   "weather": "clear", "enemy_min": 1,  "enemy_max": 999},
     "primary": "Encirclement through Forest Canopy",
     "alt1": "Drone Scout + Infantry Follow",
     "alt2": "Supply Line Disruption Strategy", "base_prob": 70, "risk": "Medium"},

    {"conditions": {"terrain": "forest",   "weather": "night", "enemy_min": 1,  "enemy_max": 999},
     "primary": "Night Vision Assault — Forest Sweep",
     "alt1": "Silent Knife-Point Infiltration",
     "alt2": "Trap-and-Collapse Formation", "base_prob": 74, "risk": "Medium"},

    {"conditions": {"terrain": "mountain", "weather": "clear", "enemy_min": 1,  "enemy_max": 20},
     "primary": "High Ground Seizure + Sniper Dominance",
     "alt1": "Ridge-to-Ridge Leapfrog Advance",
     "alt2": "Heliborne Rapid Insertion", "base_prob": 75, "risk": "Medium"},

    {"conditions": {"terrain": "mountain", "weather": "fog",   "enemy_min": 1,  "enemy_max": 999},
     "primary": "Fog-Covered High Altitude Approach",
     "alt1": "Artillery from Reverse Slope",
     "alt2": "Glacier Route Infiltration", "base_prob": 58, "risk": "High"},

    {"conditions": {"terrain": "mountain", "weather": "rain",  "enemy_min": 1,  "enemy_max": 999},
     "primary": "Rain-Shield Mountain Climb Assault",
     "alt1": "Hold Fortified Ridgeline — Defensive",
     "alt2": "Call Artillery then Advance", "base_prob": 55, "risk": "High"},
]

def match_strategy(terrain, weather, enemy_count):
    terrain = terrain.lower().strip()
    weather = weather.lower().strip()
    enemy   = int(enemy_count)
    best_match = None
    for rule in STRATEGY_RULES:
        c = rule["conditions"]
        if c["terrain"] == terrain and c["weather"] == weather and c["enemy_min"] <= enemy <= c["enemy_max"]:
            best_match = rule; break
    if not best_match:
        for rule in STRATEGY_RULES:
            c = rule["conditions"]
            if c["terrain"] == terrain and c["enemy_min"] <= enemy <= c["enemy_max"]:
                best_match = rule; break
    if not best_match:
        best_match = {"primary": "Defensive Hold — Gather Intelligence",
                      "alt1": "Reconnaissance in Force",
                      "alt2": "Delay and Request Reinforcements",
                      "base_prob": 50, "risk": "Medium"}
    return best_match


# ═══════════════════════════════════════════════════════════
#  SECTION 2 — MULTI-STRATEGY COMPARISON ENGINE (NEW)
# ═══════════════════════════════════════════════════════════

# Strategy name templates per type / terrain / weather
_STRAT_NAMES = {
    "aggressive": {
        "desert":   {"clear": "Full Armoured Blitzkrieg",        "fog":   "Fog-Cover Armoured Rush",
                     "rain":  "All-Weather Armoured Advance",     "night": "Night Armoured Strike"},
        "forest":   {"clear": "Mass Infantry Forest Assault",     "fog":   "Fog-Covered Infantry Blitz",
                     "rain":  "Rain-Masked Forest Charge",         "night": "Night Mass Forest Assault"},
        "urban":    {"clear": "Full Urban Breach and Clear",       "fog":   "Fog-Assisted Urban Blitz",
                     "rain":  "Rain-Cover Urban Assault",          "night": "Night Urban Full Assault"},
        "mountain": {"clear": "Direct Mountain Summit Assault",   "fog":   "Fog-Cover Mountain Charge",
                     "rain":  "Rain-Shield Mountain Push",         "night": "Night Mountain Assault"},
    },
    "defensive": {
        "desert":   {"clear": "Desert Fortified Hold + Counter",  "fog":   "Fog-Screen Defensive Perimeter",
                     "rain":  "Rain-Screen Defensive Hold",        "night": "NVG Perimeter + Hold"},
        "forest":   {"clear": "Forest Bunker Network Hold",       "fog":   "Fog-Cover Forest Grid",
                     "rain":  "Rain-Fortified Forest Hold",        "night": "Night Forest Defensive Screen"},
        "urban":    {"clear": "Urban Perimeter Lock + Snipers",   "fog":   "Fog Perimeter Hold",
                     "rain":  "Rain-Cover Urban Grid",             "night": "Night Urban Perimeter Defence"},
        "mountain": {"clear": "Ridgeline Fortification Hold",     "fog":   "Fog-Cover Mountain Line",
                     "rain":  "Rain-Shield Bunker Hold",           "night": "Night Mountain Perimeter"},
    },
    "stealth": {
        "desert":   {"clear": "Night Desert Infiltration + Sabotage", "fog": "Fog Desert Ghost Op",
                     "rain":  "Rain-Masked Stealth Strike",           "night": "Silent Night Desert Infil"},
        "forest":   {"clear": "Forest Canopy Stealth Ambush",     "fog":   "Fog Forest Ghost Team",
                     "rain":  "Rain-Cover Silent Forest Strike",   "night": "NVG Forest Stealth Assault"},
        "urban":    {"clear": "Urban Rooftop Sniper Network",     "fog":   "Fog Urban Ghost Infil",
                     "rain":  "Rain-Cover Urban Stealth Entry",    "night": "Night Vision Urban Strike"},
        "mountain": {"clear": "High-Altitude Sniper Overwatch",   "fog":   "Fog Mountain Infiltration",
                     "rain":  "Rain-Cover Mountain Ghost Team",    "night": "Night Mountain Silent Infil"},
    },
}

_STRAT_TIMES = {
    "aggressive": {"desert": "2–4 h", "forest": "3–5 h", "urban": "6–10 h", "mountain": "8–14 h"},
    "defensive":  {"desert": "12–24 h","forest": "12–24 h","urban": "24–48 h","mountain": "24–48 h"},
    "stealth":    {"desert": "6–10 h", "forest": "8–14 h", "urban": "10–18 h","mountain": "14–22 h"},
}
_STRAT_RESOURCES = {
    "aggressive": "Very High",
    "defensive":  "Medium",
    "stealth":    "Low",
}


def _get_strat_name(stype, terrain, weather):
    t = terrain.lower()
    w = weather.lower()
    return (_STRAT_NAMES.get(stype, {}).get(t, {}).get(w)
            or f"{stype.title()} Tactical Operation")


def _calc_prob_aggressive(terrain, weather, enemy_count, resources, base_prob):
    adj = 0
    res = resources.lower()
    if "artillery" in res: adj += 15
    if "tank"      in res: adj += 12
    if "air"       in res: adj += 14
    if "helicopter"in res: adj += 10
    if "bomb"      in res: adj += 12
    if "drone"     in res: adj +=  5
    if "sniper"    in res: adj +=  3
    if "rifle"     in res: adj +=  2
    e = int(enemy_count)
    if   e <=  5: adj += 20
    elif e <= 15: adj += 10
    elif e <= 30: adj +=  0
    elif e <= 60: adj -= 15
    elif e <=100: adj -= 25
    else:         adj -= 40
    adj += {"clear": 8, "fog": -8, "rain": -10, "night": -5}.get(weather.lower(), 0)
    adj += {"desert": 5, "forest": -2, "urban": -10, "mountain": -15}.get(terrain.lower(), 0)
    return min(95, max(5, base_prob + adj))


def _calc_prob_defensive(terrain, weather, enemy_count, resources, base_prob):
    adj = 5   # base bonus for conservative approach
    res = resources.lower()
    if "artillery"   in res: adj +=  8
    if "sniper"      in res: adj += 10
    if "radio"       in res: adj +=  5
    if "drone"       in res: adj +=  7
    if "tank"        in res: adj +=  5
    if "night vision"in res: adj +=  6
    e = int(enemy_count)
    if   e <=  5: adj += 15
    elif e <= 15: adj += 10
    elif e <= 30: adj +=  5
    elif e <= 60: adj -=  5
    elif e <=100: adj -= 12
    else:         adj -= 20
    adj += {"clear": 3, "fog": 5, "rain": 5, "night": 8}.get(weather.lower(), 0)
    adj += {"desert": 3, "forest": 8, "urban": 5, "mountain": 10}.get(terrain.lower(), 0)
    return min(95, max(5, base_prob + adj))


def _calc_prob_stealth(terrain, weather, enemy_count, resources, base_prob):
    adj = 0
    res = resources.lower()
    if "sniper"      in res: adj += 12
    if "night vision"in res: adj += 15
    if "drone"       in res: adj += 10
    if "radio"       in res: adj +=  5
    if "rifle"       in res: adj +=  3
    if "artillery"   in res: adj -=  5   # noise penalty
    if "tank"        in res: adj -=  8   # noise penalty
    e = int(enemy_count)
    if   e <=  5: adj += 25
    elif e <= 15: adj += 15
    elif e <= 30: adj +=  5
    elif e <= 60: adj -= 10
    elif e <=100: adj -= 20
    else:         adj -= 35
    adj += {"clear": -10, "fog": 20, "rain": 15, "night": 20}.get(weather.lower(), 0)
    adj += {"desert": -5, "forest": 15, "urban": 5, "mountain": 10}.get(terrain.lower(), 0)
    return min(95, max(5, base_prob + adj))


def _strategy_risk(prob, enemy_count, stype):
    """Calculate risk score and label for a specific strategy type."""
    e = int(enemy_count)
    enemy_factor = min(40, e * 0.4)
    type_mod = {"aggressive": 15, "defensive": -10, "stealth": 0}.get(stype, 0)
    risk_score = min(100, max(0, (100 - prob) * 0.6 + enemy_factor + type_mod))
    label = "Low" if risk_score < 33 else "Medium" if risk_score < 66 else "High"
    return round(risk_score, 1), label


# ─────────────────────────────────────────────
#  AI LEARNING: adjust probability from history
# ─────────────────────────────────────────────
def adjust_with_history(terrain, weather, base_prob):
    """
    Pulls past simulation outcomes for the same terrain/weather
    and nudges the probability prediction by up to ±15 points.
    This is the 'self-improving' learning mechanism.
    """
    try:
        outcomes = get_historical_outcomes(terrain, weather, limit=20)
        if len(outcomes) < 3:
            return base_prob   # not enough data yet
        total   = len(outcomes)
        success = sum(1 for o in outcomes if o["outcome"] == "success")
        partial = sum(1 for o in outcomes if o["outcome"] == "partial")
        # Weighted historical success rate
        hist_rate = (success + partial * 0.5) / total * 100
        # Blend: 70% computed + 30% historical
        blended   = base_prob * 0.7 + hist_rate * 0.3
        adjustment = max(-15, min(15, blended - base_prob))
        return round(base_prob + adjustment, 1)
    except Exception:
        return base_prob


# ─────────────────────────────────────────────
#  MAIN: compare all 3 strategies
# ─────────────────────────────────────────────
def compare_strategies(terrain, weather, enemy_count, resources):
    """
    Generate Aggressive / Defensive / Stealth strategies with
    individual metrics and pick the recommended one.
    """
    rule      = match_strategy(terrain, weather, enemy_count)
    base_prob = rule["base_prob"]
    t, w      = terrain.lower(), weather.lower()

    results = []
    for stype in ["aggressive", "defensive", "stealth"]:
        if stype == "aggressive":
            raw_prob = _calc_prob_aggressive(terrain, weather, enemy_count, resources, base_prob)
        elif stype == "defensive":
            raw_prob = _calc_prob_defensive(terrain, weather, enemy_count, resources, base_prob)
        else:
            raw_prob = _calc_prob_stealth(terrain, weather, enemy_count, resources, base_prob)

        # Apply AI learning adjustment
        prob = adjust_with_history(terrain, weather, raw_prob)
        risk_score, risk_label = _strategy_risk(prob, enemy_count, stype)

        results.append({
            "strategy_type":  stype.title(),
            "strategy_name":  _get_strat_name(stype, terrain, weather),
            "success_prob":   round(prob, 1),
            "risk_level":     risk_label,
            "risk_score":     risk_score,
            "estimated_time": _STRAT_TIMES.get(stype, {}).get(t, "6–12 h"),
            "resource_usage": _STRAT_RESOURCES.get(stype, "Medium"),
            "is_recommended": False,
        })

    # Score = probability × 0.6 − risk × 0.4  →  pick best
    scored = [(s["success_prob"] * 0.6 - s["risk_score"] * 0.4, s) for s in results]
    scored.sort(key=lambda x: x[0], reverse=True)
    scored[0][1]["is_recommended"] = True

    return results


# ═══════════════════════════════════════════════════════════
#  SECTION 3 — WAR SIMULATION STEP GENERATOR (NEW)
# ═══════════════════════════════════════════════════════════

def generate_simulation_steps(terrain, weather, enemy_count, lat, lng, strategy_type="aggressive"):
    """
    Returns a list of tactical phases for map animation.
    Each phase has: friendly positions, enemy positions,
    which enemies are still active, and descriptive text.
    """
    lat, lng = float(lat), float(lng)
    enemy    = int(enemy_count)

    # Friendly forces start offset SW of objective
    f_lat = round(lat - random.uniform(0.12, 0.22), 4)
    f_lng = round(lng - random.uniform(0.12, 0.22), 4)

    # Scatter enemy clusters around objective
    num_clusters = min(5, max(1, enemy // 8))
    enemy_positions = []
    for _ in range(num_clusters):
        e_lat = round(lat + random.uniform(-0.06, 0.06), 4)
        e_lng = round(lng + random.uniform(-0.06, 0.06), 4)
        enemy_positions.append({
            "lat": e_lat, "lng": e_lng,
            "count": max(1, enemy // num_clusters)
        })

    active_all  = list(range(len(enemy_positions)))
    active_some = active_all[len(active_all)//2:]
    active_last = active_all[:1]

    def mid(a, b): return round((a + b) / 2, 4)

    if strategy_type == "aggressive":
        phases = [
            {"phase": 1, "name": "STAGING",   "time": "T+00:00",
             "desc": "Armoured units massing at forward assembly area. Artillery unlimbering.",
             "friendly_lat": f_lat, "friendly_lng": f_lng,
             "friendly_type": "armor", "active": active_all},

            {"phase": 2, "name": "ADVANCE",   "time": "T+01:30",
             "desc": "Artillery pre-assault barrage begins. Armour pushes forward at full speed.",
             "friendly_lat": mid(f_lat, lat), "friendly_lng": mid(f_lng, lng),
             "friendly_type": "armor", "active": active_all},

            {"phase": 3, "name": "CONTACT",   "time": "T+02:45",
             "desc": "Lead tanks make contact with enemy outer perimeter. Fire superiority achieved.",
             "friendly_lat": round(lat + 0.03, 4), "friendly_lng": round(lng + 0.03, 4),
             "friendly_type": "armor", "active": active_some},

            {"phase": 4, "name": "ASSAULT",   "time": "T+04:00",
             "desc": "Full assault underway. Enemy perimeter breached. Infantry following armour.",
             "friendly_lat": lat, "friendly_lng": lng,
             "friendly_type": "armor", "active": active_last},

            {"phase": 5, "name": "SECURE",    "time": "T+05:30",
             "desc": "Objective secured. Area sweep in progress. Enemy routed.",
             "friendly_lat": lat, "friendly_lng": lng,
             "friendly_type": "infantry", "active": []},
        ]

    elif strategy_type == "stealth":
        phases = [
            {"phase": 1, "name": "INFIL",     "time": "T+00:00",
             "desc": "Special forces team begins silent approach under cover of darkness.",
             "friendly_lat": f_lat, "friendly_lng": f_lng,
             "friendly_type": "sf", "active": active_all},

            {"phase": 2, "name": "RECON",     "time": "T+02:00",
             "desc": "Drone feed confirms enemy disposition. Snipers take overwatch positions.",
             "friendly_lat": round(lat - 0.05, 4), "friendly_lng": round(lng - 0.05, 4),
             "friendly_type": "sf", "active": active_all},

            {"phase": 3, "name": "NEUTRALISE","time": "T+04:30",
             "desc": "Silenced snipers neutralise sentries. Entry corridor cleared.",
             "friendly_lat": round(lat - 0.02, 4), "friendly_lng": round(lng - 0.02, 4),
             "friendly_type": "sf", "active": active_some},

            {"phase": 4, "name": "STRIKE",    "time": "T+06:00",
             "desc": "Primary objective targeted. Sabotage executed. No alarm raised.",
             "friendly_lat": lat, "friendly_lng": lng,
             "friendly_type": "sf", "active": []},

            {"phase": 5, "name": "EXFIL",     "time": "T+08:00",
             "desc": "Team exfiltrating via secondary route. Mission accomplished.",
             "friendly_lat": f_lat, "friendly_lng": f_lng,
             "friendly_type": "sf", "active": []},
        ]

    else:  # defensive
        phases = [
            {"phase": 1, "name": "FORTIFY",   "time": "T+00:00",
             "desc": "Defensive positions established. Perimeter wire and mines laid.",
             "friendly_lat": f_lat, "friendly_lng": f_lng,
             "friendly_type": "infantry", "active": active_all},

            {"phase": 2, "name": "OBSERVE",   "time": "T+04:00",
             "desc": "Drone surveillance active. Sniper nests covering all approach routes.",
             "friendly_lat": round(f_lat + 0.03, 4), "friendly_lng": round(f_lng + 0.03, 4),
             "friendly_type": "sniper", "active": active_all},

            {"phase": 3, "name": "CONTAIN",   "time": "T+10:00",
             "desc": "Enemy advance halted at perimeter. Flanks holding. Artillery on call.",
             "friendly_lat": mid(f_lat, lat), "friendly_lng": mid(f_lng, lng),
             "friendly_type": "infantry", "active": active_some},

            {"phase": 4, "name": "COUNTER",   "time": "T+18:00",
             "desc": "Enemy weakened. Counter-attack launched. Artillery support firing.",
             "friendly_lat": round(lat + 0.04, 4), "friendly_lng": round(lng + 0.04, 4),
             "friendly_type": "armor", "active": active_last},

            {"phase": 5, "name": "VICTORY",   "time": "T+24:00",
             "desc": "Enemy routed and withdrawing. Objective secure. Casualties light.",
             "friendly_lat": lat, "friendly_lng": lng,
             "friendly_type": "infantry", "active": []},
        ]

    return {
        "terrain":        terrain,
        "weather":        weather,
        "enemy_count":    enemy,
        "strategy_type":  strategy_type,
        "objective":      {"lat": lat, "lng": lng},
        "friendly_start": {"lat": f_lat, "lng": f_lng},
        "enemy_positions": enemy_positions,
        "phases":         phases,
        "total_phases":   len(phases),
    }


# ═══════════════════════════════════════════════════════════
#  SECTION 4 — ORIGINAL SCORING & ANALYSIS (unchanged)
# ═══════════════════════════════════════════════════════════

def calculate_probability(terrain, weather, enemy_count, resources, base_prob):
    adjustment = 0
    res_lower  = resources.lower()
    for kw, bonus in {"artillery": 10, "drone": 8, "tank": 7, "sniper": 6,
                      "air": 9, "helicopter": 9, "night vision": 5,
                      "radio": 3, "rifle": 2, "bomb": 8}.items():
        if kw in res_lower: adjustment += bonus
    e = int(enemy_count)
    if   e <=  5: adjustment += 15
    elif e <= 15: adjustment +=  8
    elif e <= 30: adjustment +=  0
    elif e <= 60: adjustment -= 10
    elif e <=100: adjustment -= 20
    else:         adjustment -= 30
    adjustment += {"clear": 5, "fog": -5, "rain": -3, "night": 3}.get(weather.lower(), 0)
    adjustment += {"desert": 2, "forest": 4, "urban": -5, "mountain": -8}.get(terrain.lower(), 0)
    return round(min(95, max(5, base_prob + adjustment)), 1)


def evaluate_risk(enemy_count, terrain, weather, success_prob):
    risk_score = 0
    e = int(enemy_count)
    if   e <=  10: risk_score += 10
    elif e <=  25: risk_score += 25
    elif e <=  50: risk_score += 40
    elif e <= 100: risk_score += 60
    else:          risk_score += 80
    risk_score += {"desert": 15, "urban": 30, "forest": 20, "mountain": 35}.get(terrain.lower(), 20)
    risk_score += {"clear": 5, "fog": 20, "rain": 15, "night": 10}.get(weather.lower(), 10)
    risk_score += (100 - success_prob) * 0.3
    risk_score  = min(100, risk_score)
    label = "Low" if risk_score < 33 else "Medium" if risk_score < 66 else "High"
    return round(risk_score, 1), label


def generate_analysis_notes(terrain, weather, enemy_count, resources, strategy):
    enemy = int(enemy_count)
    notes = []
    notes.append(f"TACTICAL ASSESSMENT — {terrain.upper()} TERRAIN / {weather.upper()} CONDITIONS")
    notes.append(f"Enemy Force Strength: {enemy} units")
    if   enemy > 50: notes.append("⚠ WARNING: High enemy concentration. Consider requesting reinforcements.")
    elif enemy > 20: notes.append("CAUTION: Moderate enemy force. Coordination essential.")
    else:            notes.append("INFO: Small enemy unit. Quick decisive action advised.")
    for k, v in {"urban": "Urban terrain limits armoured mobility. Sniper nests critical.",
                 "forest": "Forest canopy provides concealment. Drone surveillance recommended.",
                 "desert": "Open desert terrain exposes movement. Night operations improve survivability.",
                 "mountain": "High altitude reduces stamina. Secure ridge lines first."}.items():
        if k == terrain.lower(): notes.append(v)
    for k, v in {"fog": "Fog reduces enemy visibility. Use GPS and radio triangulation.",
                 "rain": "Rain suppresses sound — favours silent approach.",
                 "night": "Night ops require NVG equipment. Radio coordination essential.",
                 "clear": "Clear conditions allow max fire accuracy but enemy can spot movements."}.items():
        if k == weather.lower(): notes.append(v)
    if "artillery" in resources.lower(): notes.append("✅ Artillery available — use for pre-assault suppression fire.")
    if "drone"     in resources.lower(): notes.append("✅ Drone assets available — deploy for real-time mapping.")
    if "sniper"    in resources.lower(): notes.append("✅ Sniper teams available — position on elevated ground.")
    notes.append(f"RECOMMENDED STRATEGY: {strategy}")
    return "\n".join(notes)


# ─────────────────────────────────────────────
#  Image analysis (unchanged)
# ─────────────────────────────────────────────
def analyze_image(image_path):
    if not OPENCV_AVAILABLE: return _mock_image_analysis()
    try:
        img  = cv2.imread(image_path)
        if img is None: return _mock_image_analysis()
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = round(float(np.mean(edges)) / 255 * 100, 2)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_c = [c for c in contours if cv2.contourArea(c) > 500]
        brightness = round(float(np.mean(gray)), 2)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        green_pct = round(float(np.sum(cv2.inRange(hsv,(35,40,40),(85,255,255))>0))/gray.size*100,1)
        brown_pct = round(float(np.sum(cv2.inRange(hsv,(10,40,40),(20,200,200))>0))/gray.size*100,1)
        if   green_pct > 20:      inferred = "Forest/Vegetation Area"
        elif brown_pct > 20:      inferred = "Desert/Rocky Terrain"
        elif edge_density > 15:   inferred = "Urban/Structured Area"
        else:                     inferred = "Open Ground"
        return {"status": "success", "edge_density": edge_density,
                "objects_detected": len(large_c), "brightness": brightness,
                "green_percent": green_pct, "brown_percent": brown_pct,
                "inferred_type": inferred, "threat_estimate": min(len(large_c)*2, 30)}
    except Exception as e:
        print(f"[IMAGE] Error: {e}"); return _mock_image_analysis()

def _mock_image_analysis():
    return {"status": "mock",
            "edge_density": round(random.uniform(5,25),2),
            "objects_detected": random.randint(2,15),
            "brightness": round(random.uniform(80,180),2),
            "green_percent": round(random.uniform(5,40),1),
            "brown_percent": round(random.uniform(5,30),1),
            "inferred_type": random.choice(["Forest Area","Desert Terrain","Urban Zone","Mountain Region"]),
            "threat_estimate": random.randint(3,25)}


# ═══════════════════════════════════════════════════════════
#  MASTER ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════
def run_analysis(mission_name, enemy_count, terrain, weather, resources, image_paths=None):
    """
    Orchestrates all AI analysis:
      1. Strategy matching
      2. Probability calculation (with AI learning applied)
      3. Risk evaluation
      4. Notes generation
      5. Multi-strategy comparison (NEW)
      6. Image analysis (if images provided)
    """
    rule         = match_strategy(terrain, weather, enemy_count)
    raw_prob     = calculate_probability(terrain, weather, enemy_count, resources, rule["base_prob"])

    # Apply AI learning — nudge based on historical outcomes
    success_prob = adjust_with_history(terrain, weather, raw_prob)

    risk_score, risk_label = evaluate_risk(enemy_count, terrain, weather, success_prob)
    notes = generate_analysis_notes(terrain, weather, enemy_count, resources, rule["primary"])

    # ── NEW: Strategy comparison ──────────────
    strategy_comparison = compare_strategies(terrain, weather, enemy_count, resources)

    # ── Image analysis ────────────────────────
    image_analyses = []
    if image_paths:
        for path in image_paths:
            if os.path.exists(path):
                res = analyze_image(path)
                res["path"] = path
                image_analyses.append(res)

    return {
        "mission_name":        mission_name,
        "terrain":             terrain,
        "weather":             weather,
        "enemy_count":         enemy_count,
        "resources":           resources,
        "primary_strategy":    rule["primary"],
        "alt_strategy1":       rule["alt1"],
        "alt_strategy2":       rule["alt2"],
        "success_prob":        success_prob,
        "risk_level":          risk_label,
        "risk_score":          risk_score,
        "analysis_notes":      notes,
        "strategy_comparison": strategy_comparison,   # NEW
        "image_analyses":      image_analyses,
    }