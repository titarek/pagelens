import io
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


def generate_pdf_report(report_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a structured, professional PDF audit report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Code"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
    )

    elements = []

    # Title & Metadata
    url = report_data.get("url", "")
    fetched_at = report_data.get("fetched_at", "")
    mode = report_data.get("mode", "static").upper()
    job_id = report_data.get("job_id", "")

    elements.append(Paragraph("PageLens Performance & Security Report", title_style))
    elements.append(Paragraph(f"URL: {url} | Mode: {mode} | Date: {fetched_at}", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 10))

    # Score Cards
    score_data = report_data.get("score", {})
    total_score = score_data.get("total", 0)
    struct_score = score_data.get("structure", 0)
    timing_score = score_data.get("timing", 0)
    short_score = score_data.get("shortcomings", 0)
    sec_score = score_data.get("security", 0)

    score_color = colors.HexColor("#22c55e") if total_score >= 80 else (colors.HexColor("#f59e0b") if total_score >= 50 else colors.HexColor("#ef4444"))

    score_table_data = [
        [
            Paragraph(f"<b>Overall Score</b><br/><font size='16' color='{score_color.hexval()}'><b>{total_score}/100</b></font>", body_style),
            Paragraph(f"<b>Structure & Size</b><br/><font size='12'><b>{struct_score}/25</b></font>", body_style),
            Paragraph(f"<b>Timing & Vitals</b><br/><font size='12'><b>{timing_score}/35</b></font>", body_style),
            Paragraph(f"<b>Shortcomings</b><br/><font size='12'><b>{short_score}/25</b></font>", body_style),
            Paragraph(f"<b>Security Audit</b><br/><font size='12'><b>{sec_score}/15</b></font>", body_style),
        ]
    ]
    score_table = Table(score_table_data, colWidths=[120, 105, 105, 105, 105])
    score_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(score_table)
    elements.append(Spacer(1, 12))

    # Structural Metrics Summary
    elements.append(Paragraph("Structural & Delivery Metrics", section_style))
    struct = report_data.get("structural", {})
    total_kb = round(struct.get("total_bytes", 0) / 1024, 1)
    html_kb = round(struct.get("html_bytes", 0) / 1024, 1)
    css_kb = round(struct.get("css_bytes", 0) / 1024, 1)
    js_kb = round(struct.get("js_bytes", 0) / 1024, 1)

    metrics_table_data = [
        ["Total Weight", f"{total_kb} KB", "Requests", str(struct.get("num_requests", 0))],
        ["HTML Weight", f"{html_kb} KB", "DOM Elements", str(struct.get("num_dom_elements", 0))],
        ["CSS Weight", f"{css_kb} KB", "Blocking Scripts", str(struct.get("num_blocking_scripts", 0))],
        ["JavaScript Weight", f"{js_kb} KB", "Compression", struct.get("compression_used", "none").upper()],
    ]
    m_table = Table(metrics_table_data, colWidths=[135, 135, 135, 135])
    m_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elements.append(m_table)
    elements.append(Spacer(1, 12))

    # Shortcomings
    shortcomings = report_data.get("shortcomings", [])
    elements.append(Paragraph(f"Identified Shortcomings ({len(shortcomings)})", section_style))
    if shortcomings:
        s_rows = [["Sev", "Issue & Cause", "Remediation"]]
        for s in shortcomings[:8]:
            sev = s.get("severity", "low").upper()
            title = s.get("title", "")
            cause = s.get("cause", "")
            fix = s.get("fix", "")

            issue_p = Paragraph(f"<b>{title}</b><br/><font size='7' color='#64748b'>{cause}</font>", body_style)
            fix_p = Paragraph(f"<font size='8'>{fix}</font>", body_style)
            s_rows.append([sev, issue_p, fix_p])

        s_table = Table(s_rows, colWidths=[45, 250, 245])
        s_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(s_table)
    else:
        elements.append(Paragraph("No critical architectural shortcomings detected.", body_style))

    elements.append(Spacer(1, 12))

    # Security Audit
    sec = report_data.get("security", {})
    checks = sec.get("checks", [])
    elements.append(Paragraph(f"Security Posture Audit ({sec.get('passed', 0)} Passed, {sec.get('warnings', 0)} Warnings, {sec.get('failures', 0)} Failures)", section_style))
    if checks:
        c_rows = [["Status", "Security Check", "Finding"]]
        for c in checks[:8]:
            c_rows.append([
                c.get("status", "").upper(),
                Paragraph(f"<b>{c.get('title', '')}</b>", body_style),
                Paragraph(c.get("detail", ""), body_style),
            ])
        c_table = Table(c_rows, colWidths=[55, 185, 300])
        c_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(c_table)

    # Footer note
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Generated by PageLens (https://pagelens.dev) — Continuous Web Performance & Security Intelligence", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
