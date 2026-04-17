"""
Generates a clean, ATS-friendly resume PDF from a tailored resume dict.
Matches the style of Ishani's original resume: single column, clean header, bold section titles.
"""

import logging
import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

# ── Colours & fonts ───────────────────────────────────────────────────────────
BLACK = colors.black
DARK_GREY = colors.HexColor("#333333")
LINK_COLOR = colors.HexColor("#1a0dab")

MARGIN = 0.55 * inch


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "name",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "contact": ParagraphStyle(
            "contact",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=DARK_GREY,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=1,
            textColor=BLACK,
        ),
        "role_header": ParagraphStyle(
            "role_header",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=BLACK,
        ),
        "role_sub": ParagraphStyle(
            "role_sub",
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=DARK_GREY,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            leftIndent=10,
            textColor=BLACK,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=BLACK,
        ),
        "skills_line": ParagraphStyle(
            "skills_line",
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=BLACK,
        ),
    }


def _safe(text: str) -> str:
    """Normalize unicode chars that ReportLab's built-in fonts can't encode."""
    return re.sub(r"[\u2013\u2014]", "-", str(text))


def generate_resume_pdf(tailored: dict, output_path: Path) -> Path:
    """
    Render tailored resume dict to a PDF at output_path.
    Returns the path on success.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        encoding="utf-8",
    )

    s = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(_safe(tailored.get("name", "")), s["name"]))

    contact_parts = [
        _safe(tailored.get("phone", "")),
        f'<a href="mailto:{tailored.get("email", "")}" color="{LINK_COLOR}">{tailored.get("email", "")}</a>',
        f'<a href="{tailored.get("linkedin", "")}" color="{LINK_COLOR}">LinkedIn</a>',
        f'<a href="{tailored.get("github", "")}" color="{LINK_COLOR}">GitHub</a>',
        f'<a href="{tailored.get("portfolio", "")}" color="{LINK_COLOR}">Portfolio</a>',
    ]
    story.append(Paragraph(" | ".join(p for p in contact_parts if p), s["contact"]))
    story.append(Spacer(1, 4))

    # ── Summary ───────────────────────────────────────────────────────────────
    if tailored.get("summary"):
        _section(story, s, "SUMMARY")
        story.append(Paragraph(_safe(tailored["summary"]), s["body"]))
        story.append(Spacer(1, 3))

    # ── Education ─────────────────────────────────────────────────────────────
    _section(story, s, "EDUCATION")
    for edu in tailored.get("education", []):
        story.append(_two_col(
            f"<b>{_safe(edu['school'])}</b>",
            f"{_safe(edu['start'])} - {_safe(edu['end'])}",
            s,
        ))
        story.append(Paragraph(
            f"{_safe(edu['degree'])} (GPA: {_safe(edu['gpa'])}) &nbsp; <i>{_safe(edu['location'])}</i>",
            s["role_sub"],
        ))
    story.append(Spacer(1, 3))

    # ── Experience ────────────────────────────────────────────────────────────
    _section(story, s, "EXPERIENCE")
    for exp in tailored.get("experience", []):
        story.append(_two_col(
            f"<b>{_safe(exp['company'])}</b>",
            f"{_safe(exp['start'])} - {_safe(exp['end'])}",
            s,
        ))
        story.append(Paragraph(f"<i>{_safe(exp['title'])}</i>", s["role_sub"]))
        for bullet in exp.get("bullets", []):
            story.append(Paragraph(f"• {_safe(bullet)}", s["bullet"]))
        story.append(Spacer(1, 3))

    # ── Projects ──────────────────────────────────────────────────────────────
    if tailored.get("projects"):
        _section(story, s, "PROJECTS")
        for proj in tailored["projects"]:
            story.append(Paragraph(f"<b>{_safe(proj['name'])}</b>", s["role_header"]))
            for bullet in proj.get("bullets", []):
                story.append(Paragraph(f"• {_safe(bullet)}", s["bullet"]))
        story.append(Spacer(1, 3))

    # ── Skills ────────────────────────────────────────────────────────────────
    if tailored.get("skills"):
        _section(story, s, "SKILLS & CERTIFICATIONS")
        for cat, items in tailored["skills"].items():
            cat_label = cat.replace("_", " ").title()
            story.append(Paragraph(
                f"<b>{cat_label}:</b> {_safe(', '.join(items))}",
                s["skills_line"],
            ))
        if tailored.get("certifications"):
            story.append(Paragraph(
                f"<b>Certifications:</b> {_safe(', '.join(tailored['certifications']))}",
                s["skills_line"],
            ))
        story.append(Spacer(1, 3))

    # ── Publications ──────────────────────────────────────────────────────────
    if tailored.get("publications"):
        _section(story, s, "PUBLICATIONS")
        story.append(Paragraph(_safe(" | ".join(tailored["publications"])), s["body"]))

    doc.build(story)
    logger.info(f"Resume PDF saved: {output_path}")
    return output_path


def generate_cover_letter_pdf(letter_text: str, job: dict, output_path: Path) -> Path:
    """Render plain-text cover letter to a simple PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=MARGIN * 1.5,
        rightMargin=MARGIN * 1.5,
        topMargin=MARGIN * 1.5,
        bottomMargin=MARGIN * 1.5,
    )

    s = _styles()
    story = []

    story.append(Paragraph("Ishani Kathuria", s["name"]))
    story.append(Paragraph(
        "ishani@kathuria.net | +12193680435 | Hammond, IN",
        s["contact"],
    ))
    story.append(Spacer(1, 16))

    story.append(Paragraph(
        f"Re: {job.get('title', 'Internship')} at {job.get('company', '')}",
        ParagraphStyle("subject", fontName="Helvetica-Bold", fontSize=10, leading=14),
    ))
    story.append(Spacer(1, 10))

    for para in letter_text.split("\n\n"):
        para = para.strip()
        if para:
            story.append(Paragraph(para, s["body"]))
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Sincerely,", s["body"]))
    story.append(Paragraph("Ishani Kathuria", s["body"]))

    doc.build(story)
    logger.info(f"Cover letter PDF saved: {output_path}")
    return output_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(story: list, s: dict, title: str) -> None:
    story.append(Paragraph(title, s["section_title"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BLACK, spaceAfter=3))


def _two_col(left: str, right: str, s: dict) -> Table:
    """True two-column row: bold left text, right-aligned date."""
    right_style = ParagraphStyle(
        "_right",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=TA_RIGHT,
        textColor=DARK_GREY,
    )
    t = Table(
        [[Paragraph(left, s["role_header"]), Paragraph(right, right_style)]],
        colWidths=["75%", "25%"],
        hAlign="LEFT",
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t
