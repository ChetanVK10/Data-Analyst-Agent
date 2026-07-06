"""
pdf_generator.py — Generates a structured PDF report from an AnalysisResponse-shaped dict.

Signature changed from (session_id, question, narrative_summary, data_preview, scratch_dir)
to (session_id, question, report_data, tables, scratch_dir) so the PDF receives typed,
structured data — no markdown string parsing.
"""

import os
import logging
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

logger = logging.getLogger(__name__)


def generate_pdf_report(
    session_id: str,
    question: str,
    report_data: Dict[str, Any],
    tables: List[Dict[str, Any]],
    scratch_dir: str,
) -> str:
    """
    Generates a premium structured PDF report.

    Args:
        session_id:  Session identifier (used in header).
        question:    Original user question.
        report_data: Dict with keys:
                       executive_summary: {headline, summary, confidence}
                       insights:          [{title, body}, ...]
                       recommendations:   [{title, body}, ...]
        tables:      List of {title, columns, rows} dicts.
        scratch_dir: Absolute path to the scratch directory for this session.

    Returns:
        Absolute path to the generated PDF.
    """
    os.makedirs(scratch_dir, exist_ok=True)
    pdf_path = os.path.join(scratch_dir, "report.pdf")
    logger.info(f"Generating structured PDF report → {pdf_path}")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=44, leftMargin=44, topMargin=44, bottomMargin=44,
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=20,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=18,
        spaceAfter=8,
    )
    subsection_heading = ParagraphStyle(
        "SubsectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#94A3B8"),
        spaceAfter=4,
    )
    headline_style = ParagraphStyle(
        "Headline",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#7C3AED"),
        spaceAfter=8,
    )

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph("Autonomous Data Analyst — Analysis Report", title_style))
    story.append(Paragraph(f"Session: {session_id}", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=16))

    # ── Question ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Question Analyzed", section_heading))
    story.append(Paragraph(f"&ldquo;{question}&rdquo;", body_style))
    story.append(Spacer(1, 10))

    # ── Executive Summary ────────────────────────────────────────────────────
    exec_sum = report_data.get("executive_summary", {})
    if exec_sum:
        story.append(Paragraph("Executive Summary", section_heading))

        headline = exec_sum.get("headline", "")
        if headline:
            story.append(Paragraph(headline, headline_style))

        summary_text = exec_sum.get("summary", "")
        if summary_text:
            # Split paragraphs on double newlines
            for para in summary_text.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para.replace("\n", " "), body_style))

        confidence = exec_sum.get("confidence", "")
        if confidence:
            story.append(Paragraph(f"Confidence: {confidence}", meta_style))

        story.append(Spacer(1, 12))

    # ── Results Tables ───────────────────────────────────────────────────────
    for tbl in tables:
        col_headers = tbl.get("columns", [])
        rows = tbl.get("rows", [])
        tbl_title = tbl.get("title", "Query Results")

        if not col_headers or not rows:
            continue

        story.append(Paragraph(tbl_title, section_heading))

        # Build table data (header + up to 20 rows for PDF layout)
        display_rows = rows[:20]
        table_data = [col_headers] + [
            [str(cell) if cell is not None else "" for cell in row]
            for row in display_rows
        ]

        col_width = doc.width / max(len(col_headers), 1)
        pdf_table = Table(table_data, colWidths=[col_width] * len(col_headers))
        pdf_table.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#F1F5F9")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.HexColor("#0F172A")),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            # Body rows
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            # Grid
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(pdf_table)

        if len(rows) > 20:
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"* Table shows 20 of {len(rows)} rows.", meta_style
            ))
        story.append(Spacer(1, 14))

    # ── Key Insights ─────────────────────────────────────────────────────────
    insights = report_data.get("insights", [])
    if insights:
        story.append(Paragraph("Key Insights", section_heading))
        for ins in insights:
            story.append(Paragraph(ins.get("title", ""), subsection_heading))
            body = ins.get("body", "").replace("\n", " ")
            if body:
                story.append(Paragraph(body, body_style))
        story.append(Spacer(1, 10))

    # ── Recommendations ──────────────────────────────────────────────────────
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        story.append(Paragraph("Recommendations", section_heading))
        for rec in recommendations:
            story.append(Paragraph(rec.get("title", ""), subsection_heading))
            body = rec.get("body", "").replace("\n", " ")
            if body:
                story.append(Paragraph(body, body_style))
        story.append(Spacer(1, 10))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceBefore=16))
    story.append(Paragraph("Generated by Autonomous Data Analyst Agent", meta_style))

    # ── Build ────────────────────────────────────────────────────────────────
    try:
        doc.build(story)
        logger.info(f"PDF built successfully: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"ReportLab build failed: {e}")
        raise
