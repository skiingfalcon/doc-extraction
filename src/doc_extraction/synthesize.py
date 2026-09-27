"""Build fictional multi-page investment-memo PDFs and ground-truth sidecars."""

import json
from pathlib import Path

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from doc_extraction.paths import MEMO_DIR

_NAVY = colors.HexColor("#1f4e79")


def memo_catalog() -> list[dict]:
    """Three fictional memos. Every scored string is printed in the PDF."""
    return [
        {
            "slug": "northwind-harbor",
            "firm": "Northwind Harbor Capital",
            "title": "Northwind Harbor Confidential Memorandum",
            "date": "March 12, 2026",
            "thesis": (
                "Northwind Harbor Capital proposes a concentrated allocation to "
                "cash-generating industrial and real-estate operators around "
                "the Great Lakes. The thesis is that contracted logistics sites "
                "and self-storage can fund distributions while the portfolio "
                "waits for a slower rate environment."
            ),
            "rows": [
                ["Harborline Logistics", "Industrials", "18.4%", "$42.10"],
                ["Pebble Reef Storage", "Real Estate", "12.7%", "$31.50"],
                ["Quarry Light Transit", "Industrials", "9.2%", "$18.75"],
                ["Southglass Clinics", "Healthcare", "7.8%", "$27.40"],
                ["Kestrel Grid Partners", "Utilities", "6.1%", "$15.20"],
            ],
            "bars": [
                ("Industrials", 32),
                ("Real Estate", 21),
                ("Healthcare", 14),
                ("Utilities", 11),
            ],
            "risks": [
                "Lease rollover at Harborline Logistics could reduce contracted revenue.",
                "Higher storage vacancy would pressure the Pebble Reef Storage yield.",
                "Utility regulation can delay earnings at Kestrel Grid Partners.",
            ],
            "footnote": (
                "Illustrative only: Northwind Harbor Capital is fictional and "
                "this memorandum is not an offer to sell securities."
            ),
        },
        {
            "slug": "cedar-pine",
            "firm": "Cedar and Pine Partners",
            "title": "Cedar and Pine Allocation Memorandum",
            "date": "June 3, 2026",
            "thesis": (
                "Cedar and Pine Partners is reviewing a four-holding sleeve of "
                "timber, packaging, and regional retail names. The sleeve is "
                "meant to add income that is less tied to coastal housing, and "
                "position sizes are capped so no issuer exceeds one fifth of "
                "the sleeve."
            ),
            "rows": [
                ["Silver Birch Timber", "Materials", "16.5%", "$54.00"],
                ["Lumen Carton Co", "Materials", "11.3%", "$22.80"],
                ["Marigold Market", "Retail", "8.9%", "$14.60"],
                ["Ironbrook Packaging", "Materials", "7.4%", "$19.25"],
            ],
            "bars": [
                ("Materials", 35),
                ("Retail", 18),
                ("Cash", 12),
            ],
            "risks": [
                "Timber prices can fall faster than Silver Birch Timber can cut harvests.",
                "A packaging surplus would narrow margins at Lumen Carton Co.",
                "Same-store traffic at Marigold Market is sensitive to fuel costs.",
            ],
            "footnote": (
                "Illustrative only: Cedar and Pine Partners is fictional and "
                "this memorandum is not an offer to sell securities."
            ),
        },
        {
            "slug": "lakefront",
            "firm": "Lakefront Allocation Group",
            "title": "Lakefront Municipal Credit Memorandum",
            "date": "September 1, 2026",
            "thesis": (
                "Lakefront Allocation Group outlines a short list of essential "
                "service credits for a taxable account. The target is steady "
                "coupons from water, power, and toll facilities, with each "
                "position small enough that a single downgrade does not "
                "dominate the sleeve."
            ),
            "rows": [
                ["Bluewater Authority", "Water", "14.2%", "$101.25"],
                ["Cinder Power District", "Power", "10.6%", "$98.40"],
                ["Red Maple Tollway", "Transportation", "8.1%", "$103.10"],
                ["Harborside Waterworks", "Water", "6.4%", "$99.75"],
            ],
            "bars": [
                ("Water", 28),
                ("Power", 19),
                ("Transportation", 15),
            ],
            "risks": [
                "Rate cases can freeze coupons at Bluewater Authority for several years.",
                "Fuel switching could reduce load served by Cinder Power District.",
                "Traffic shortfalls would weaken coverage at Red Maple Tollway.",
            ],
            "footnote": (
                "Illustrative only: Lakefront Allocation Group is fictional and "
                "this memorandum is not an offer to sell securities."
            ),
        },
    ]


def synthesize(output_dir: Path = MEMO_DIR) -> list[Path]:
    """Write each memo PDF and a JSON sidecar of strings printed in it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for memo in memo_catalog():
        pdf_path = output_dir / f"{memo['slug']}.pdf"
        _write_pdf(pdf_path, memo)
        sidecar = output_dir / f"{memo['slug']}.truth.json"
        sidecar.write_text(json.dumps(_truth(memo), indent=2) + "\n", encoding="utf-8")
        written.append(pdf_path)
    return written


def _truth(memo: dict) -> dict:
    cells = [cell for row in memo["rows"] for cell in row]
    return {
        "slug": memo["slug"],
        "headings": [
            memo["title"],
            "Investment Thesis",
            "Portfolio Holdings",
            "Sector Weights",
            "Principal Risks",
        ],
        "table_cells": cells,
        "footnotes": [memo["footnote"]],
    }


def _write_pdf(path: Path, memo: dict) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MemoTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=16,
        leading=20,
        textColor=_NAVY,
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "MemoHeading",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=13,
        leading=16,
        textColor=_NAVY,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "MemoBody",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15,
        spaceAfter=8,
    )

    def draw_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(_NAVY)
        canvas.rect(0, letter[1] - 28, letter[0], 28, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Times-Bold", 9)
        canvas.drawString(doc.leftMargin, letter[1] - 18, f"{memo['firm']}  |  Private Memorandum")
        canvas.setFillColor(colors.black)
        canvas.setFont("Times-Italic", 8)
        canvas.drawString(doc.leftMargin, 36, memo["footnote"])
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=memo["title"],
    )
    story = [
        Paragraph(memo["title"], title_style),
        Paragraph(memo["date"], body_style),
        Paragraph("Investment Thesis", heading_style),
        Paragraph(memo["thesis"], body_style),
        Paragraph("Portfolio Holdings", heading_style),
        _holdings_table(memo["rows"]),
        PageBreak(),
        Paragraph("Sector Weights", heading_style),
        _bar_chart(memo["bars"]),
        Paragraph("Principal Risks", heading_style),
    ]
    for risk in memo["risks"]:
        story.append(Paragraph(f"- {risk}", body_style))
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)


def _holdings_table(rows: list[list[str]]) -> Table:
    header = ["Issuer", "Sector", "Weight", "Cost Basis"]
    table = Table([header, *rows], colWidths=[2.3 * inch, 1.5 * inch, 0.9 * inch, 1.1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.Color(0.93, 0.95, 0.97)),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.7, 0.75, 0.8)),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _bar_chart(bars: list[tuple[str, int]]) -> Drawing:
    names = [name for name, _value in bars]
    values = [value for _name, value in bars]
    drawing = Drawing(460, 200)
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 40
    chart.height = 140
    chart.width = 390
    chart.data = [values]
    chart.categoryAxis.categoryNames = names
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values) + 10
    chart.bars[0].fillColor = _NAVY
    chart.barLabelFormat = "%d"
    chart.barLabels.nudge = 8
    drawing.add(chart)
    return drawing
