#!/usr/bin/env python3
"""Build a company intelligence brief in two matching formats from one JSON file.

Usage:
    python build_brief.py <brief.json> <output_dir>

Produces, inside <output_dir>:
    index.html                          -> self-contained dashboard (feed to create_artifact)
    <Company>-Intelligence-Briefing.pdf -> polished print/share version

Both outputs are generated from the SAME content + theme so they always match.

Requires: reportlab (preinstalled in the sandbox). No network access needed.

See example_brief.json (bundled in assets/) for the expected input schema.
"""
import html
import json
import sys
import os
import re

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, KeepTogether)

LEVEL_COLORS = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#16a34a"}
DEFAULT_THEME = {
    "dark": "#4c1d95",      # header band + section headings + table header
    "accent": "#6d28d9",    # card dates / titles accents
    "light_row": "#f7f4fc", # alternating table rows
    "border": "#e0d4f5",    # borders + heading underline
}


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "company"


# --------------------------------------------------------------------------- #
# HTML dashboard (self-contained, light-mode, no external assets)
# --------------------------------------------------------------------------- #
def build_html(b, theme):
    e = html.escape
    title = b.get("title", f'{b["company"]} Intelligence Briefing')
    desc = b.get("description",
                 f'Daily {b["company"]} intelligence briefing with news, product '
                 f'updates, competitive landscape, and a financial snapshot.')

    fin = "".join(
        f'<div class="fin-item"><div class="label">{e(i["label"])}</div>'
        f'<div class="value">{e(i["value"])}</div>'
        f'<div class="sub">{e(i.get("sub", ""))}</div></div>'
        for i in b.get("financials", [])
    )
    news = "".join(
        f'<div class="card"><div class="date">{e(n["date"])}</div>'
        f'<div class="title">{e(n["title"])}</div>'
        f'<div class="desc">{e(n["desc"])}</div></div>'
        for n in b.get("news", [])
    )
    prod = "".join(
        f'<div class="card"><div class="title">{e(p["title"])}</div>'
        f'<div class="desc">{e(p["desc"])}</div></div>'
        for p in b.get("products", [])
    )
    rows = "".join(
        f'<tr><td>{e(c["name"])}</td><td>{e(c["strength"])}</td>'
        f'<td>{e(c["advantage"])}</td>'
        f'<td><span class="lvl {e(c["level"])}">{e(c["level"])}</span></td></tr>'
        for c in b.get("competitors", [])
    )
    footer = b.get("footer",
                   "Generated from public web sources for internal "
                   "competitive-intelligence use. Private-company financials are "
                   "estimates and vary by source.")

    return f"""<!DOCTYPE html><script type="application/json" id="cowork-artifact-meta">
{{
  "name": {json.dumps(b.get("artifact_name", b["company"] + " Daily Intel"))},
  "schemaVersion": 1,
  "description": {json.dumps(desc)}
}}
</script>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f6f9; color: #1a1a2e; line-height: 1.5; }}
  header {{ background: linear-gradient(135deg, {theme['accent']}, {theme['dark']}); color: white; padding: 24px 32px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }}
  header h1 {{ font-size: 1.6rem; font-weight: 700; letter-spacing: -0.3px; }}
  header .meta {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .badge {{ background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4); border-radius: 6px; padding: 4px 10px; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.5px; }}
  .updated {{ font-size: 0.78rem; opacity: 0.85; }}
  .fin-bar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; padding: 20px 32px; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin: 20px 32px; border-radius: 10px; }}
  .fin-item {{ text-align: center; }}
  .fin-item .label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; margin-bottom: 4px; }}
  .fin-item .value {{ font-size: 1.25rem; font-weight: 700; }}
  .fin-item .sub {{ font-size: 0.72rem; color: #6b7280; }}
  main {{ padding: 0 32px 32px; max-width: 1100px; margin: 0 auto; }}
  section {{ margin-top: 28px; }}
  section h2 {{ font-size: 1.2rem; color: {theme['dark']}; margin-bottom: 14px; border-bottom: 2px solid {theme['border']}; padding-bottom: 6px; }}
  .card {{ background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }}
  .card .date {{ font-size: 0.74rem; color: {theme['accent']}; font-weight: 600; }}
  .card .title {{ font-weight: 700; font-size: 0.98rem; margin: 2px 0 4px; }}
  .card .desc {{ font-size: 0.9rem; color: #374151; }}
  table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 10px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 12px 14px; font-size: 0.88rem; vertical-align: top; }}
  th {{ background: {theme['dark']}; color: white; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  tr:nth-child(even) td {{ background: {theme['light_row']}; }}
  .lvl {{ padding: 3px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; color: white; }}
  .HIGH {{ background: #dc2626; }}
  .MEDIUM {{ background: #d97706; }}
  .LOW {{ background: #16a34a; }}
  footer {{ text-align: center; padding: 24px; font-size: 0.8rem; color: #6b7280; }}
</style>
</head>
<body>
<header>
  <h1>{e(title)}</h1>
  <div class="meta">
    <span class="badge">{e(b.get("badge", ""))}</span>
    <span class="updated">Last updated: {e(b.get("updated", ""))}</span>
  </div>
</header>
<div class="fin-bar">{fin}</div>
<main>
  <section><h2>News &amp; Announcements</h2>{news}</section>
  <section><h2>Product &amp; Technology</h2>{prod}</section>
  <section><h2>Competitive Landscape</h2>
    <table>
      <thead><tr><th>Competitor</th><th>Key Strength vs. {e(b["company"])}</th><th>{e(b["company"])} Advantage</th><th>Threat Level</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</main>
<footer>{e(footer)}</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# PDF (reportlab) — mirrors the dashboard design
# --------------------------------------------------------------------------- #
def build_pdf(b, theme, out_path):
    DARK = colors.HexColor(theme["dark"])
    ACCENT = colors.HexColor(theme["accent"])
    LIGHTROW = colors.HexColor(theme["light_row"])
    BORDER = colors.HexColor(theme["border"])
    GREY = colors.HexColor("#6b7280")
    TEXT = colors.HexColor("#374151")
    INK = colors.HexColor("#1a1a2e")

    styles = getSampleStyleSheet()
    PAGE_W, _ = letter
    LM = RM = 0.6 * inch
    CW = PAGE_W - LM - RM

    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="Helvetica-Bold",
                        fontSize=20, textColor=colors.white, leading=24)
    badge = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=8,
                           textColor=colors.white, alignment=2, leading=12)
    sub_white = ParagraphStyle("sub_white", fontName="Helvetica", fontSize=8,
                               textColor=colors.white, alignment=2, leading=11)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                        textColor=DARK, spaceBefore=14, spaceAfter=8, leading=16)
    fin_label = ParagraphStyle("fl", fontName="Helvetica-Bold", fontSize=6.5,
                               textColor=GREY, alignment=1, leading=9)
    fin_value = ParagraphStyle("fv", fontName="Helvetica-Bold", fontSize=13.5,
                               textColor=INK, alignment=1, leading=16)
    fin_sub = ParagraphStyle("fs", fontName="Helvetica", fontSize=6.5,
                             textColor=GREY, alignment=1, leading=9)
    card_date = ParagraphStyle("cd", fontName="Helvetica-Bold", fontSize=7.5,
                               textColor=ACCENT, leading=10)
    card_title = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=10,
                                textColor=INK, leading=13, spaceBefore=1)
    card_desc = ParagraphStyle("cde", fontName="Helvetica", fontSize=8.5,
                               textColor=TEXT, leading=11, spaceBefore=2)
    th = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8,
                        textColor=colors.white, leading=10)
    td = ParagraphStyle("td", fontName="Helvetica", fontSize=8,
                        textColor=TEXT, leading=10.5)
    td_b = ParagraphStyle("tdb", fontName="Helvetica-Bold", fontSize=8.5,
                          textColor=INK, leading=11)
    lvl_style = ParagraphStyle("lvl", fontName="Helvetica-Bold", fontSize=7.5,
                               textColor=colors.white, alignment=1, leading=11)
    foot = ParagraphStyle("foot", fontName="Helvetica", fontSize=7.5,
                          textColor=GREY, alignment=1, leading=10)

    def P(t, s):
        return Paragraph(html.escape(str(t)).replace("&amp;", "&"), s)

    story = []

    # Header band
    header = Table(
        [[P(b.get("title", b["company"] + " Intelligence Briefing"), h1),
          [P(b.get("badge", ""), badge),
           P("Last updated: " + b.get("updated", ""), sub_white)]]],
        colWidths=[CW * 0.62, CW * 0.38])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
    ]))
    story.append(header)
    story.append(Spacer(1, 14))

    # Financial bar
    fins = b.get("financials", [])
    n = max(len(fins), 1)
    minis = []
    for i in fins:
        t = Table([[P(i["label"], fin_label)], [P(i["value"], fin_value)],
                   [P(i.get("sub", ""), fin_sub)]], colWidths=[CW / n])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        minis.append(t)
    if minis:
        fin_bar = Table([minis], colWidths=[CW / n] * n)
        fin_bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(fin_bar)

    def card(rows_para, pads):
        inner = Table([[p] for p in rows_para], colWidths=[CW])
        style = [("BACKGROUND", (0, 0), (-1, -1), colors.white),
                 ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                 ("LEFTPADDING", (0, 0), (-1, -1), 12),
                 ("RIGHTPADDING", (0, 0), (-1, -1), 12)] + pads
        inner.setStyle(TableStyle(style))
        return KeepTogether([inner, Spacer(1, 8)])

    story.append(P("News & Announcements", h2))
    for nws in b.get("news", []):
        story.append(card(
            [P(nws["date"], card_date), P(nws["title"], card_title),
             P(nws["desc"], card_desc)],
            [("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, 2), (0, 2), 9),
             ("TOPPADDING", (0, 1), (0, 2), 1), ("BOTTOMPADDING", (0, 0), (0, 1), 1)]))

    story.append(P("Product & Technology", h2))
    for p in b.get("products", []):
        story.append(card(
            [P(p["title"], card_title), P(p["desc"], card_desc)],
            [("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, 1), (0, 1), 9),
             ("TOPPADDING", (0, 1), (0, 1), 1), ("BOTTOMPADDING", (0, 0), (0, 0), 1)]))

    story.append(P("Competitive Landscape", h2))
    cw = [CW * 0.18, CW * 0.34, CW * 0.34, CW * 0.14]
    data = [[P("Competitor", th), P(f'Key Strength vs. {b["company"]}', th),
             P(f'{b["company"]} Advantage', th), P("Threat", th)]]
    for c in b.get("competitors", []):
        lvl = c["level"].upper()
        bt = Table([[P(lvl, lvl_style)]], colWidths=[cw[3] - 16])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(LEVEL_COLORS.get(lvl, "#6b7280"))),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        data.append([P(c["name"], td_b), P(c["strength"], td), P(c["advantage"], td), bt])
    tbl = Table(data, colWidths=cw, repeatRows=1)
    ts = [("BACKGROUND", (0, 0), (-1, 0), DARK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("ALIGN", (3, 0), (3, -1), "CENTER"),
          ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
          ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER), ("BOX", (0, 0), (-1, -1), 0.5, BORDER)]
    for i in range(1, len(data)):
        ts.append(("BACKGROUND", (0, i), (-1, i),
                   LIGHTROW if i % 2 == 0 else colors.white))
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)

    story.append(Spacer(1, 14))
    story.append(P(b.get("footer",
                         "Generated from public web sources for internal "
                         "competitive-intelligence use. Private-company financials "
                         "are estimates and vary by source."), foot))

    SimpleDocTemplate(out_path, pagesize=letter, leftMargin=LM, rightMargin=RM,
                      topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                      title=b.get("title", b["company"] + " Intelligence Briefing"),
                      author="Competitive Intelligence").build(story)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    brief_path, out_dir = sys.argv[1], sys.argv[2]
    with open(brief_path) as f:
        b = json.load(f)
    theme = {**DEFAULT_THEME, **b.get("theme", {})}
    os.makedirs(out_dir, exist_ok=True)

    html_path = os.path.join(out_dir, "index.html")
    with open(html_path, "w") as f:
        f.write(build_html(b, theme))

    pdf_name = f'{b["company"].replace(" ", "-")}-Intelligence-Briefing.pdf'
    pdf_path = os.path.join(out_dir, pdf_name)
    build_pdf(b, theme, pdf_path)

    print("HTML:", html_path)
    print("PDF :", pdf_path)


if __name__ == "__main__":
    main()
