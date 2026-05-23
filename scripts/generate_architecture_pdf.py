"""
generate_architecture_pdf.py — converts docs/architecture.md to a
professional PDF deliverable using ReportLab.

Usage:
    python scripts/generate_architecture_pdf.py
    # Output: docs/architecture.pdf

Add to PATH or run from project root.
"""
import os
import re
import sys
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    print("ERROR: reportlab not installed. Run: pip install reportlab")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
ARCH_MD = PROJECT_ROOT / "docs" / "architecture.md"
OUTPUT_PDF = PROJECT_ROOT / "docs" / "architecture.pdf"

# ── Styles ─────────────────────────────────────────────────────────────────────

BASE = getSampleStyleSheet()

STYLES = {
    "title": ParagraphStyle(
        "Title",
        parent=BASE["Title"],
        fontSize=24,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=6,
        alignment=TA_CENTER,
    ),
    "subtitle": ParagraphStyle(
        "Subtitle",
        parent=BASE["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#4a5568"),
        spaceAfter=20,
        alignment=TA_CENTER,
    ),
    "h1": ParagraphStyle(
        "H1",
        parent=BASE["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#2c5282"),
        spaceBefore=18,
        spaceAfter=6,
        borderPad=(0, 0, 2, 0),
    ),
    "h2": ParagraphStyle(
        "H2",
        parent=BASE["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#2d3748"),
        spaceBefore=12,
        spaceAfter=4,
    ),
    "h3": ParagraphStyle(
        "H3",
        parent=BASE["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#4a5568"),
        spaceBefore=8,
        spaceAfter=3,
        fontName="Helvetica-Bold",
    ),
    "body": ParagraphStyle(
        "Body",
        parent=BASE["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    ),
    "bullet": ParagraphStyle(
        "Bullet",
        parent=BASE["Normal"],
        fontSize=10,
        leading=14,
        leftIndent=16,
        bulletIndent=6,
        spaceAfter=3,
    ),
    "code": ParagraphStyle(
        "Code",
        parent=BASE["Code"],
        fontSize=8,
        fontName="Courier",
        backColor=colors.HexColor("#f7fafc"),
        borderColor=colors.HexColor("#e2e8f0"),
        borderWidth=0.5,
        borderPad=6,
        leading=11,
        spaceAfter=8,
        spaceBefore=4,
    ),
    "table_header": ParagraphStyle(
        "TableHeader",
        parent=BASE["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    ),
    "table_cell": ParagraphStyle(
        "TableCell",
        parent=BASE["Normal"],
        fontSize=9,
        leading=12,
    ),
}

TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
])


# ── Markdown → ReportLab flowables ─────────────────────────────────────────────

def _escape(text: str) -> str:
    """Escape XML special characters for Paragraph."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_markup(text: str) -> str:
    """Convert inline markdown (bold, code, italic) to ReportLab XML."""
    text = _escape(text)
    # bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # italic: *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
    # inline code: `code`
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="9">\1</font>', text)
    return text


def _parse_table(lines: list[str]) -> Table | None:
    """Parse a GFM table into a ReportLab Table."""
    rows = []
    for line in lines:
        if re.match(r"^\|[-: |]+\|$", line.strip()):
            continue  # separator row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return None

    col_count = max(len(r) for r in rows)
    data = []
    for i, row in enumerate(rows):
        # pad short rows
        row = row + [""] * (col_count - len(row))
        style = STYLES["table_header"] if i == 0 else STYLES["table_cell"]
        data.append([Paragraph(_inline_markup(c), style) for c in row])

    col_width = (A4[0] - 4 * cm) / col_count
    tbl = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    tbl.setStyle(TABLE_STYLE)
    return tbl


def md_to_flowables(md_text: str) -> list:
    """Convert markdown text to a list of ReportLab flowables."""
    flowables = []
    lines = md_text.splitlines()
    i = 0
    in_code_block = False
    code_lines: list[str] = []
    in_table = False
    table_lines: list[str] = []

    while i < len(lines):
        line = lines[i]

        # ── Code blocks ──────────────────────────────────────────────────────
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                in_code_block = False
                code_text = "\n".join(code_lines)
                flowables.append(Preformatted(code_text, STYLES["code"]))
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # ── Tables ───────────────────────────────────────────────────────────
        if line.startswith("|"):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            # Check if next line is still table
            if i < len(lines) and lines[i].startswith("|"):
                continue
            else:
                tbl = _parse_table(table_lines)
                if tbl:
                    flowables.append(Spacer(1, 4))
                    flowables.append(tbl)
                    flowables.append(Spacer(1, 8))
                in_table = False
                table_lines = []
            continue

        # ── Mermaid diagrams: render as styled note block ─────────────────────
        if line.strip() in ("```mermaid",):
            in_code_block = True
            code_lines = ["[Architecture diagram — see docs/architecture.md for Mermaid source]"]
            i += 1
            continue

        # ── Headings ─────────────────────────────────────────────────────────
        if line.startswith("### "):
            flowables.append(Paragraph(_inline_markup(line[4:]), STYLES["h3"]))
            i += 1
            continue
        if line.startswith("## "):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
            flowables.append(Paragraph(_inline_markup(line[3:]), STYLES["h2"]))
            i += 1
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(_inline_markup(line[2:]), STYLES["h1"]))
            i += 1
            continue

        # ── Horizontal rule ──────────────────────────────────────────────────
        if re.match(r"^-{3,}$", line.strip()) or re.match(r"^\*{3,}$", line.strip()):
            flowables.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e0")))
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        # ── Bullet lists ─────────────────────────────────────────────────────
        m = re.match(r"^(\s*)([-*+])\s+(.*)", line)
        if m:
            indent_level = len(m.group(1)) // 2
            bullet_char = "•" if indent_level == 0 else "◦"
            text = _inline_markup(m.group(3))
            style = ParagraphStyle(
                f"Bullet{indent_level}",
                parent=STYLES["bullet"],
                leftIndent=16 + indent_level * 12,
            )
            flowables.append(Paragraph(f"{bullet_char}  {text}", style))
            i += 1
            continue

        # ── Numbered lists ───────────────────────────────────────────────────
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            text = _inline_markup(m.group(1))
            flowables.append(Paragraph(f"&#8226;  {text}", STYLES["bullet"]))
            i += 1
            continue

        # ── Blank lines ──────────────────────────────────────────────────────
        if not line.strip():
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # ── Normal paragraph ─────────────────────────────────────────────────
        flowables.append(Paragraph(_inline_markup(line), STYLES["body"]))
        i += 1

    return flowables


# ── Document assembly ──────────────────────────────────────────────────────────

def generate_pdf(md_path: Path, output_path: Path) -> None:
    print(f"Reading: {md_path}")
    md_text = md_path.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="HumanMaximizer AI Lead Generation — Architecture",
        author="AI Lead Generation System",
        subject="Architecture Document",
    )

    story = []

    # Cover page elements
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("HumanMaximizer AI Lead Generation", STYLES["title"]))
    story.append(Paragraph("Architecture &amp; Design Document", STYLES["subtitle"]))
    story.append(Paragraph("Razor Infotech Pvt Ltd — AI Architect / GenAI Engineer Assignment", STYLES["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2c5282")))
    story.append(Spacer(1, 0.5 * cm))

    # Body
    story.extend(md_to_flowables(md_text))

    doc.build(story)
    print(f"Generated: {output_path}  ({output_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    generate_pdf(ARCH_MD, OUTPUT_PDF)

    # Also generate fine-tuning strategy PDF
    ft_md = PROJECT_ROOT / "docs" / "fine_tuning_strategy.md"
    ft_pdf = PROJECT_ROOT / "docs" / "fine_tuning_strategy.pdf"
    if ft_md.exists():
        generate_pdf(ft_md, ft_pdf)

    # Also generate LLM strategy PDF
    llm_md = PROJECT_ROOT / "docs" / "llm_strategy.md"
    llm_pdf = PROJECT_ROOT / "docs" / "llm_strategy.pdf"
    if llm_md.exists():
        generate_pdf(llm_md, llm_pdf)

    # Also generate prompt examples PDF
    pe_md = PROJECT_ROOT / "docs" / "prompt_examples.md"
    pe_pdf = PROJECT_ROOT / "docs" / "prompt_examples.pdf"
    if pe_md.exists():
        generate_pdf(pe_md, pe_pdf)
