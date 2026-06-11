"""
=============================================================
  routes/report.py — Auto-Generated PDF Mission Report (NEW)
  Uses ReportLab to create a professional classified PDF
  containing scenario inputs, strategies, risk analysis,
  and the multi-strategy comparison table.
=============================================================
"""

import io
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, session, redirect, url_for,
    flash, send_file, request
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)

from database import get_simulation_by_id, get_strategy_comparisons, get_outcome

report_bp = Blueprint("report", __name__)

# ── Colour palette matching the military theme ──
OLIVE       = colors.HexColor("#1e2d10")
AMBER       = colors.HexColor("#c8a84b")
GREEN_DARK  = colors.HexColor("#2a4a1a")
GREEN_MID   = colors.HexColor("#4a7c59")
TEXT_LIGHT  = colors.HexColor("#f0f4e8")
TEXT_MUTED  = colors.HexColor("#7a9060")
BG_DARK     = colors.HexColor("#0d1208")
BG_CARD     = colors.HexColor("#161e10")
RED         = colors.HexColor("#c84b4b")
YELLOW      = colors.HexColor("#f59e0b")
CYAN        = colors.HexColor("#4b7ac8")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _risk_color(level):
    return {"Low": GREEN_MID, "Medium": YELLOW, "High": RED}.get(level, TEXT_MUTED)


# ─────────────────────────────────────────────
#  PDF REPORT GENERATION
# ─────────────────────────────────────────────
@report_bp.route("/api/generate_report/<int:sim_id>")
@login_required
def generate_report(sim_id):
    """
    GET /api/generate_report/<sim_id>
    Generates and streams a PDF report for the given simulation.
    """
    sim = get_simulation_by_id(sim_id, session["user_id"])
    if not sim:
        flash("Simulation not found.", "error")
        return redirect(url_for("simulation.dashboard"))

    comparisons = get_strategy_comparisons(sim_id)
    outcome     = get_outcome(sim_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
        title=f"ATDSS Report — {sim['mission_name']}"
    )

    styles = getSampleStyleSheet()

    # ── Custom styles ─────────────────────────
    title_s = ParagraphStyle("Title", parent=styles["Normal"],
        fontSize=20, fontName="Helvetica-Bold",
        textColor=AMBER, alignment=1, spaceAfter=2*mm)

    sub_s = ParagraphStyle("Sub", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        textColor=TEXT_LIGHT, alignment=1, spaceAfter=1*mm)

    section_s = ParagraphStyle("Section", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        textColor=AMBER, spaceBefore=4*mm, spaceAfter=2*mm)

    body_s = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica",
        textColor=colors.HexColor("#333333"), spaceAfter=1.5*mm, leading=13)

    mono_s = ParagraphStyle("Mono", parent=styles["Normal"],
        fontSize=8, fontName="Courier",
        textColor=colors.HexColor("#2a4a1a"), spaceAfter=1*mm, leading=12)

    footer_s = ParagraphStyle("Footer", parent=styles["Normal"],
        fontSize=7, fontName="Helvetica",
        textColor=TEXT_MUTED, alignment=1)

    story = []

    # ════════════════════════════════════════
    #  PAGE HEADER
    # ════════════════════════════════════════
    story.append(Paragraph("INDIAN ARMY", title_s))
    story.append(Paragraph("AI TACTICAL DECISION SUPPORT SYSTEM", sub_s))
    story.append(Paragraph("CLASSIFIED MISSION INTELLIGENCE REPORT", sub_s))
    story.append(HRFlowable(width="100%", thickness=3, color=AMBER, spaceAfter=3*mm))

    # ── Classification banner ─────────────────
    banner_data = [["⬛ TOP SECRET  |  CLEARANCE LEVEL ALPHA  |  AUTHORISED PERSONNEL ONLY"]]
    banner_t = Table(banner_data, colWidths=[180*mm])
    banner_t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), OLIVE),
        ("TEXTCOLOR",   (0,0), (-1,-1), RED),
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("PADDING",     (0,0), (-1,-1), 4),
    ]))
    story.append(banner_t)
    story.append(Spacer(1, 5*mm))

    # ════════════════════════════════════════
    #  MISSION PARAMETERS TABLE
    # ════════════════════════════════════════
    story.append(Paragraph("MISSION PARAMETERS", section_s))

    mission_data = [
        ["Mission Code Name", sim["mission_name"]],
        ["Terrain Type",      sim["terrain"].title()],
        ["Weather Conditions",sim["weather"].title()],
        ["Enemy Force Strength", f"{sim['enemy_count']} units"],
        ["Available Resources",  sim["resources"]],
        ["Mission Coordinates",  f"Lat {sim['lat']:.4f}  |  Lng {sim['lng']:.4f}"],
        ["Date / Time",          sim["created_at"][:16]],
        ["Reporting Officer",    session.get("rank","—") + " " + session.get("username","—")],
    ]
    if outcome:
        mission_data.append(["Recorded Outcome", outcome["outcome"].upper()])

    mt = Table(mission_data, colWidths=[60*mm, 120*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), OLIVE),
        ("TEXTCOLOR",  (0,0), (0,-1), AMBER),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#f0f4e8")),
        ("TEXTCOLOR",  (1,0), (1,-1), colors.HexColor("#1a2412")),
        ("FONTNAME",   (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING",    (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS", (0,0), (-1,-1),
            [colors.HexColor("#f0f4e8"), colors.white] * 10),
    ]))
    story.append(mt)
    story.append(Spacer(1, 4*mm))

    # ════════════════════════════════════════
    #  ANALYSIS RESULT
    # ════════════════════════════════════════
    story.append(Paragraph("AI ANALYSIS RESULT", section_s))

    result_data = [
        ["Success Probability", f"{sim['success_prob']}%",
         "Risk Level",          sim["risk_level"]],
        ["Risk Score",          f"{sim['risk_score']} / 100",
         "Strategy Engine",     "AI Rule-Based + ML Learning"],
    ]
    rt = Table(result_data, colWidths=[45*mm, 45*mm, 45*mm, 45*mm])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), OLIVE),
        ("BACKGROUND", (2,0), (2,-1), OLIVE),
        ("TEXTCOLOR",  (0,0), (0,-1), AMBER),
        ("TEXTCOLOR",  (2,0), (2,-1), AMBER),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING",    (0,0), (-1,-1), 5),
        ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#e8f4e8")),
        ("BACKGROUND", (3,0), (3,-1), colors.HexColor("#f4f4e8")),
        ("TEXTCOLOR",  (1,0), (1,-1), _risk_color(sim["risk_level"])),
    ]))
    story.append(rt)
    story.append(Spacer(1, 4*mm))

    # ── Strategies ────────────────────────────
    story.append(Paragraph("BATTLE PLANS", section_s))
    for label, key in [("PLAN A — PRIMARY", "primary_strategy"),
                       ("PLAN B — ALTERNATIVE", "alt_strategy1"),
                       ("PLAN C — CONTINGENCY", "alt_strategy2")]:
        story.append(Paragraph(f"<b>{label}:</b>  {sim[key]}", body_s))

    story.append(Spacer(1, 4*mm))

    # ════════════════════════════════════════
    #  STRATEGY COMPARISON TABLE (NEW FEATURE)
    # ════════════════════════════════════════
    if comparisons:
        story.append(KeepTogether([
            Paragraph("MULTI-STRATEGY COMPARISON ANALYSIS", section_s),
            Paragraph(
                "The AI engine evaluated three strategic approaches. "
                "The recommended strategy is highlighted.",
                body_s
            ),
            Spacer(1, 2*mm),
        ]))

        comp_header = [["Type", "Strategy Name", "Success %", "Risk", "Est. Time", "Resources", "★"]]
        comp_rows   = []
        for c in comparisons:
            row = [
                c["strategy_type"],
                c["strategy_name"][:32] + ("…" if len(c["strategy_name"]) > 32 else ""),
                f"{c['success_prob']}%",
                c["risk_level"],
                c["estimated_time"],
                c["resource_usage"],
                "★ BEST" if c["is_recommended"] else "—",
            ]
            comp_rows.append(row)

        comp_data = comp_header + comp_rows
        col_w = [22*mm, 55*mm, 20*mm, 18*mm, 22*mm, 20*mm, 18*mm]
        ct = Table(comp_data, colWidths=col_w)

        ct_style = [
            # Header row
            ("BACKGROUND", (0,0), (-1,0), BG_DARK),
            ("TEXTCOLOR",  (0,0), (-1,0), AMBER),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("PADDING",    (0,0), (-1,-1), 4),
            ("ALIGN",      (2,0), (6,-1), "CENTER"),
        ]
        # Highlight recommended row
        for i, c in enumerate(comparisons, start=1):
            if c["is_recommended"]:
                ct_style.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#e8f4e0")))
                ct_style.append(("FONTNAME",   (0,i), (-1,i), "Helvetica-Bold"))
            else:
                ct_style.append(("BACKGROUND", (0,i), (-1,i),
                    colors.white if i % 2 == 0 else colors.HexColor("#f8f8f5")))

        ct.setStyle(TableStyle(ct_style))
        story.append(ct)
        story.append(Spacer(1, 4*mm))

    # ════════════════════════════════════════
    #  TACTICAL ASSESSMENT NOTES
    # ════════════════════════════════════════
    story.append(Paragraph("TACTICAL ASSESSMENT REPORT", section_s))
    for line in (sim.get("analysis_notes") or "").split("\n"):
        if line.strip():
            story.append(Paragraph(line, mono_s))

    story.append(Spacer(1, 8*mm))

    # ── Footer ────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=AMBER, spaceAfter=2*mm))
    story.append(Paragraph(
        f"ATDSS v2.5.0  |  Indian Army AI Division  |  "
        f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')} IST  |  "
        f"CLASSIFICATION: TOP SECRET",
        footer_s
    ))

    doc.build(story)
    buffer.seek(0)

    filename = sim["mission_name"].replace(" ", "_").replace("/", "-") + "_Report.pdf"
    return send_file(
        buffer,
        download_name=filename,
        mimetype="application/pdf",
        as_attachment=True
    )