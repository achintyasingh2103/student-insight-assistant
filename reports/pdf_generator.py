"""
reports/pdf_generator.py
ReportLab PDF report builder.
Generates teacher-facing and parent-facing versions of the student report.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Color palette ─────────────────────────────────────────────────────────────
PRIMARY    = colors.HexColor("#1D9E75")   # teal
SECONDARY  = colors.HexColor("#534AB7")  # purple
ACCENT     = colors.HexColor("#EF9F27")  # amber
LIGHT_BG   = colors.HexColor("#F1FFF9")
DARK_TEXT  = colors.HexColor("#1A1A2E")
MID_GRAY   = colors.HexColor("#6B7280")

PAGE_W, PAGE_H = A4


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20,
                                 textColor=PRIMARY, spaceAfter=4, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11,
                                    textColor=MID_GRAY, spaceAfter=12, alignment=TA_CENTER),
        "section_head": ParagraphStyle("section_head", fontName="Helvetica-Bold", fontSize=13,
                                        textColor=SECONDARY, spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                                textColor=DARK_TEXT, spaceAfter=6, leading=15,
                                alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=10,
                                  textColor=DARK_TEXT, leftIndent=16, spaceAfter=3,
                                  bulletIndent=6, leading=14),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=10,
                                 textColor=DARK_TEXT, spaceAfter=2),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                                 textColor=MID_GRAY, alignment=TA_CENTER),
    }


def _header_table(student_data: dict, insight: dict) -> Table:
    name = student_data.get("name", "—")
    cls = f"Class {student_data.get('class', '—')}{student_data.get('section', '')}"
    att = f"{student_data.get('attendance_percent', '—')}%"
    archetype = insight.get("behavioral_pattern", "—")
    engagement = insight.get("engagement_score", "—")
    confidence = insight.get("confidence_level", "—")
    if isinstance(confidence, dict):
        confidence = confidence.get("level", str(confidence))

    data = [
        [Paragraph(f"<b>{name}</b>", ParagraphStyle("h", fontName="Helvetica-Bold",
                   fontSize=14, textColor=colors.white)),
         Paragraph(f"<b>Archetype:</b> {archetype}", ParagraphStyle("h", fontName="Helvetica",
                   fontSize=10, textColor=colors.white))],
        [Paragraph(f"{cls}  |  Attendance: {att}", ParagraphStyle("h", fontName="Helvetica",
                   fontSize=10, textColor=colors.HexColor("#D1FAE5"))),
         Paragraph(f"<b>Engagement:</b> {engagement}/10  |  <b>Confidence:</b> {confidence}",
                   ParagraphStyle("h", fontName="Helvetica", fontSize=10,
                                  textColor=colors.HexColor("#D1FAE5")))],
    ]
    t = Table(data, colWidths=[10 * cm, 8.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PRIMARY, PRIMARY]),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    return t


def _score_table(subjects: dict) -> Table:
    headers = [Paragraph("<b>Subject</b>", ParagraphStyle("th", fontName="Helvetica-Bold",
               fontSize=9, textColor=colors.white))]
    scores  = [Paragraph("<b>Score</b>", ParagraphStyle("th", fontName="Helvetica-Bold",
               fontSize=9, textColor=colors.white))]
    grades  = [Paragraph("<b>Grade</b>", ParagraphStyle("th", fontName="Helvetica-Bold",
               fontSize=9, textColor=colors.white))]

    def grade(s):
        if s >= 90: return "A+"
        if s >= 80: return "A"
        if s >= 70: return "B+"
        if s >= 60: return "B"
        if s >= 50: return "C"
        return "D"

    rows = [[Paragraph("<b>Subject</b>", ParagraphStyle("x", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
             Paragraph("<b>Score /100</b>", ParagraphStyle("x", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
             Paragraph("<b>Grade</b>", ParagraphStyle("x", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white))]]

    for subj, score in subjects.items():
        rows.append([
            Paragraph(subj.replace("_", " "), ParagraphStyle("td", fontName="Helvetica", fontSize=9)),
            Paragraph(str(int(score)), ParagraphStyle("td", fontName="Helvetica", fontSize=9)),
            Paragraph(grade(score), ParagraphStyle("td", fontName="Helvetica-Bold", fontSize=9,
                      textColor=PRIMARY if score >= 70 else (ACCENT if score >= 50 else colors.red))),
        ])

    avg = sum(subjects.values()) / len(subjects)
    rows.append([
        Paragraph("<b>Average</b>", ParagraphStyle("td", fontName="Helvetica-Bold", fontSize=9)),
        Paragraph(f"<b>{avg:.1f}</b>", ParagraphStyle("td", fontName="Helvetica-Bold", fontSize=9)),
        Paragraph(f"<b>{grade(avg)}</b>", ParagraphStyle("td", fontName="Helvetica-Bold", fontSize=9, textColor=PRIMARY)),
    ])

    t = Table(rows, colWidths=[8 * cm, 4 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BG),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def generate_pdf(
    student_data: dict,
    insight: dict,
    career: dict,
    report: dict,
    audience: str = "teacher",  # "teacher" or "parent"
) -> bytes:
    """
    Generate a PDF report and return as bytes.
    audience: "teacher" includes counselor notes; "parent" uses simpler language.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    S = _styles()
    story = []

    # ── Title ──
    story.append(Paragraph("Student Intelligence Report", S["title"]))
    audience_label = "Teacher & Counselor Edition" if audience == "teacher" else "Family Edition"
    story.append(Paragraph(audience_label, S["subtitle"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y')} | Ekaakshar Education",
        S["small"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── Student header ──
    story.append(_header_table(student_data, insight))
    story.append(Spacer(1, 0.4 * cm))

    # ── Executive Summary ──
    story.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY))
    story.append(Paragraph("Executive Summary", S["section_head"]))
    story.append(Paragraph(report.get("executive_summary", "—"), S["body"]))

    # ── Academic Performance ──
    story.append(Paragraph("Academic Performance", S["section_head"]))
    story.append(_score_table(student_data.get("subjects", {})))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(report.get("academic_analysis", "—"), S["body"]))

    # ── Strengths & Improvement Areas ──
    story.append(Paragraph("Key Strengths", S["section_head"]))
    for s in insight.get("top_strengths", []):
        story.append(Paragraph(f"• {s}", S["bullet"]))

    story.append(Paragraph("Growth Opportunities", S["section_head"]))
    for a in insight.get("improvement_areas", []):
        story.append(Paragraph(f"• {a}", S["bullet"]))

    # ── Personal Development ──
    story.append(Paragraph("Personal Development", S["section_head"]))
    story.append(Paragraph(report.get("personal_development", "—"), S["body"]))

    # ── Career Pathways ──
    story.append(Paragraph("Career Pathways", S["section_head"]))
    for rec in career.get("career_recommendations", []):
        story.append(Paragraph(f"<b>{rec.get('career_path', '—')}</b>", S["label"]))
        story.append(Paragraph(rec.get("why_suited", ""), S["body"]))
        exams = rec.get("entrance_exams", [])
        if exams:
            story.append(Paragraph(f"Relevant exams: {', '.join(exams)}", S["small"]))
        story.append(Spacer(1, 0.2 * cm))

    # ── Teacher/Counselor section ──
    if audience == "teacher":
        story.append(Paragraph("Counselor Notes", S["section_head"]))
        story.append(Paragraph(report.get("counselor_notes", "—"), S["body"]))

    # ── Parent message ──
    story.append(Paragraph(
        "A Message for Parents" if audience == "parent" else "Parent Communication",
        S["section_head"]
    ))
    story.append(Paragraph(report.get("parent_message", "—"), S["body"]))

    # ── Action Plan ──
    story.append(Paragraph("Recommended Action Plan", S["section_head"]))
    for i, action in enumerate(report.get("action_plan", []), 1):
        story.append(Paragraph(f"{i}. {action}", S["bullet"]))

    # ── Footer ──
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Paragraph(
        "This report is generated by the Ekaakshar AI Student Insight System and is intended "
        "for educational guidance purposes only.",
        S["small"]
    ))

    doc.build(story)
    return buf.getvalue()
