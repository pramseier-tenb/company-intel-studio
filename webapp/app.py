#!/usr/bin/env python3
"""Company Intelligence Brief — local web front-end.

A tiny, dependency-light web app for picking a company and (re)generating its
intelligence brief as a live dashboard + downloadable PDF. Built on Python's
standard library, so the ONLY external dependency is `reportlab` (for the PDF).

    pip install reportlab        # one-time; HTML works even without it
    python3 app.py               # then open http://127.0.0.1:5050

Companies live as JSON files in ./data/ (see any of the preloaded ones for the
schema). Generated output goes to ./generated/<slug>/. Editing a company in the
UI rewrites its data file and rebuilds both formats via build_brief.py.
"""
import html
import json
import os
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import build_brief  # bundled alongside this file

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
GEN_DIR = os.path.join(HERE, "generated")
PORT = int(os.environ.get("PORT", "5050"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(GEN_DIR, exist_ok=True)

REPORTLAB_OK = True
try:
    import reportlab  # noqa: F401
except Exception:
    REPORTLAB_OK = False

NEW_TEMPLATE = {
    "company": "", "title": "", "artifact_name": "", "badge": "PRIVATE",
    "updated": "", "description": "",
    "theme": dict(build_brief.DEFAULT_THEME),
    "financials": [{"label": "Ownership", "value": "Private", "sub": ""}],
    "news": [{"date": "", "title": "", "desc": ""}],
    "products": [{"title": "", "desc": ""}],
    "competitors": [{"name": "", "strength": "", "advantage": "", "level": "MEDIUM"}],
    "footer": "Generated from public web sources. Financials are estimates and vary by source.",
}


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "company"


def list_companies():
    out = []
    for fn in sorted(os.listdir(DATA_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(DATA_DIR, fn)) as f:
                b = json.load(f)
            out.append({"slug": fn[:-5], "company": b.get("company", fn[:-5]),
                        "badge": b.get("badge", ""),
                        "theme": {**build_brief.DEFAULT_THEME, **b.get("theme", {})}})
        except Exception:
            continue
    out.sort(key=lambda c: c["company"].lower())
    return out


def load_brief(slug):
    with open(os.path.join(DATA_DIR, slug + ".json")) as f:
        return json.load(f)


def save_brief(slug, b):
    with open(os.path.join(DATA_DIR, slug + ".json"), "w") as f:
        json.dump(b, f, indent=2)


def generate(slug):
    """Build HTML (always) and PDF (if reportlab present) into generated/<slug>/."""
    b = load_brief(slug)
    theme = {**build_brief.DEFAULT_THEME, **b.get("theme", {})}
    out = os.path.join(GEN_DIR, slug)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(build_brief.build_html(b, theme))
    pdf_name = b["company"].replace(" ", "-") + "-Intelligence-Briefing.pdf"
    pdf_path = os.path.join(out, pdf_name)
    if REPORTLAB_OK:
        try:
            build_brief.build_pdf(b, theme, pdf_path)
        except Exception as e:
            print("PDF generation failed:", e)
            pdf_name = None
    else:
        pdf_name = None
    return pdf_name


def ensure_generated(slug):
    """Regenerate if output is missing or older than its data file."""
    data_path = os.path.join(DATA_DIR, slug + ".json")
    idx = os.path.join(GEN_DIR, slug, "index.html")
    if (not os.path.exists(idx)) or os.path.getmtime(idx) < os.path.getmtime(data_path):
        return generate(slug)
    for fn in os.listdir(os.path.join(GEN_DIR, slug)):
        if fn.endswith(".pdf"):
            return fn
    return None


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #
def page(title, body, accent="#1d4ed8"):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: light; --accent: {accent}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f4f6f9; color: #1a1a2e; }}
  a {{ color: var(--accent); text-decoration: none; }}
  .topbar {{ background: #11182a; color: #fff; padding: 14px 22px; display: flex;
            align-items: center; gap: 14px; }}
  .topbar .brand {{ font-weight: 700; font-size: 1.05rem; letter-spacing: -0.2px; }}
  .topbar .brand span {{ color: #8fb4ff; }}
  .topbar .spacer {{ flex: 1; }}
  .btn {{ display: inline-block; background: var(--accent); color: #fff; border: none;
         border-radius: 8px; padding: 9px 16px; font-size: 0.9rem; font-weight: 600;
         cursor: pointer; text-decoration: none; }}
  .btn.secondary {{ background: #e5e9f2; color: #1a1a2e; }}
  .btn.ghost {{ background: transparent; color: #fff; border: 1px solid rgba(255,255,255,0.35); }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 28px 22px 48px; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 6px; }}
  .muted {{ color: #6b7280; font-size: 0.92rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 16px; margin-top: 22px; }}
  .card {{ background: #fff; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
          padding: 0; overflow: hidden; display: flex; flex-direction: column;
          border: 1px solid #eef0f5; transition: transform .08s ease, box-shadow .08s ease; }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.12); }}
  .card .bar {{ height: 8px; }}
  .card .body {{ padding: 16px 18px; }}
  .card .name {{ font-weight: 700; font-size: 1.05rem; }}
  .card .badge {{ display: inline-block; margin-top: 8px; font-size: 0.7rem; font-weight: 700;
                 letter-spacing: 0.4px; color: #fff; padding: 3px 9px; border-radius: 20px; }}
  .card.new {{ align-items: center; justify-content: center; border: 2px dashed #c3cbe0;
              background: #fbfcff; color: var(--accent); font-weight: 700; min-height: 120px;
              cursor: pointer; }}
  .toolbar {{ background: #fff; border-bottom: 1px solid #e7eaf1; padding: 10px 22px;
             display: flex; align-items: center; gap: 10px; }}
  iframe {{ width: 100%; height: calc(100vh - 116px); border: 0; background: #fff; }}
  form.editor {{ background: #fff; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
                padding: 22px; margin-top: 18px; }}
  label {{ display: block; font-weight: 600; font-size: 0.85rem; margin: 14px 0 5px; }}
  input[type=text], textarea, select {{ width: 100%; padding: 9px 11px; border: 1px solid #cfd6e4;
         border-radius: 8px; font-size: 0.9rem; font-family: inherit; }}
  textarea {{ min-height: 120px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
             font-size: 0.82rem; line-height: 1.45; }}
  .row {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .row > div {{ flex: 1; min-width: 200px; }}
  .colorrow {{ display: flex; gap: 16px; flex-wrap: wrap; align-items: end; }}
  .colorrow > div {{ flex: 1; min-width: 120px; }}
  input[type=color] {{ width: 100%; height: 40px; border: 1px solid #cfd6e4; border-radius: 8px;
         background: #fff; padding: 2px; }}
  .hint {{ color: #6b7280; font-size: 0.78rem; margin-top: 3px; }}
  .err {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 8px;
         padding: 10px 14px; margin: 14px 0; font-size: 0.9rem; }}
  .warn {{ background: #fffbeb; color: #92400e; border: 1px solid #fde68a; border-radius: 8px;
          padding: 10px 14px; margin: 14px 0; font-size: 0.88rem; }}
  .actions {{ margin-top: 22px; display: flex; gap: 10px; }}
</style></head><body>
<div class="topbar">
  <div class="brand">Company Intel <span>Studio</span></div>
  <div class="spacer"></div>
  <a class="btn ghost" href="/">All companies</a>
</div>
{body}
</body></html>"""


def home_page():
    cards = ""
    for c in list_companies():
        accent = c["theme"]["accent"]
        dark = c["theme"]["dark"]
        badge = (f'<span class="badge" style="background:{html.escape(dark)}">'
                 f'{html.escape(c["badge"])}</span>' if c["badge"] else "")
        cards += f"""<a class="card" href="/company/{c['slug']}">
          <div class="bar" style="background:linear-gradient(90deg,{html.escape(accent)},{html.escape(dark)})"></div>
          <div class="body"><div class="name">{html.escape(c['company'])}</div>{badge}</div></a>"""
    cards += ('<div class="card new" onclick="location.href=\'/new\'">'
              '<div>+ New company</div></div>')
    warn = ("" if REPORTLAB_OK else
            '<div class="warn">Note: <code>reportlab</code> isn\'t installed, so PDF export is '
            'disabled — the dashboard still works. Run <code>pip install reportlab</code> to enable PDFs.</div>')
    body = f"""<div class="wrap">
      <h1>Pick a company</h1>
      <div class="muted">Choose a company to view its intelligence brief, or add a new one.</div>
      {warn}
      <div class="grid">{cards}</div>
    </div>"""
    return page("Company Intel Studio", body)


def viewer_page(slug):
    b = load_brief(slug)
    pdf_name = ensure_generated(slug)
    accent = {**build_brief.DEFAULT_THEME, **b.get("theme", {})}["accent"]
    pdf_btn = (f'<a class="btn" href="/pdf/{slug}">⬇ Download PDF</a>' if pdf_name
               else '<span class="muted">PDF export needs reportlab</span>')
    body = f"""<div class="toolbar" style="--accent:{html.escape(accent)}">
      <a class="btn secondary" href="/">← Back</a>
      <strong>{html.escape(b.get('company',''))}</strong>
      <span class="muted">Intelligence Briefing</span>
      <div style="flex:1"></div>
      {pdf_btn}
      <a class="btn secondary" href="/regenerate/{slug}">⟳ Regenerate</a>
      <a class="btn secondary" href="/edit/{slug}">✎ Edit</a>
    </div>
    <iframe src="/dashboard/{slug}" title="dashboard"></iframe>"""
    return page(b.get("company", "Brief") + " — Brief", body, accent)


def editor_page(slug=None, b=None, error=None):
    is_new = slug is None
    if b is None:
        b = load_brief(slug) if slug else json.loads(json.dumps(NEW_TEMPLATE))
    theme = {**build_brief.DEFAULT_THEME, **b.get("theme", {})}
    e = html.escape

    def ta(name, value):
        return (f'<textarea name="{name}">'
                f'{e(json.dumps(value, indent=2))}</textarea>')

    err = f'<div class="err">{e(error)}</div>' if error else ""
    action = "/save" + ("" if is_new else f"?slug={slug}")
    body = f"""<div class="wrap"><h1>{'New company' if is_new else 'Edit ' + e(b.get('company',''))}</h1>
    <div class="muted">Fill in the fields. The list sections are JSON — match the examples shown.</div>
    {err}
    <form class="editor" method="POST" action="{action}">
      <div class="row">
        <div><label>Company name</label>
          <input type="text" name="company" value="{e(b.get('company',''))}" required></div>
        <div><label>Badge</label>
          <input type="text" name="badge" value="{e(b.get('badge',''))}">
          <div class="hint">Public: e.g. "NASDAQ: CRWD". Private: "PRIVATE" or "PRIVATE · CATEGORY".</div></div>
      </div>
      <div class="row">
        <div><label>Last updated</label>
          <input type="text" name="updated" value="{e(b.get('updated',''))}">
          <div class="hint">e.g. "June 22, 2026". Leave blank to use today.</div></div>
        <div><label>Footer</label>
          <input type="text" name="footer" value="{e(b.get('footer',''))}"></div>
      </div>
      <label>Theme colors</label>
      <div class="colorrow">
        <div><div class="hint">Header / headings</div>
          <input type="color" name="theme_dark" value="{e(theme['dark'])}"></div>
        <div><div class="hint">Accent</div>
          <input type="color" name="theme_accent" value="{e(theme['accent'])}"></div>
        <div><div class="hint">Row tint</div>
          <input type="color" name="theme_light_row" value="{e(theme['light_row'])}"></div>
        <div><div class="hint">Borders</div>
          <input type="color" name="theme_border" value="{e(theme['border'])}"></div>
      </div>
      <label>Financial snapshot &nbsp;<span class="hint">list of {{label, value, sub}}</span></label>
      {ta('financials', b.get('financials', []))}
      <label>News &amp; Announcements &nbsp;<span class="hint">list of {{date, title, desc}}</span></label>
      {ta('news', b.get('news', []))}
      <label>Product &amp; Technology &nbsp;<span class="hint">list of {{title, desc}}</span></label>
      {ta('products', b.get('products', []))}
      <label>Competitive Landscape &nbsp;<span class="hint">list of {{name, strength, advantage, level}} — level: HIGH/MEDIUM/LOW</span></label>
      {ta('competitors', b.get('competitors', []))}
      <div class="actions">
        <button class="btn" type="submit">Save &amp; Generate</button>
        <a class="btn secondary" href="/">Cancel</a>
      </div>
    </form></div>"""
    return page(("New company" if is_new else "Edit") + " — Intel Studio", body, theme["accent"])


def build_from_form(form, slug):
    def one(k, default=""):
        return form.get(k, [default])[0]

    company = one("company").strip()
    if not company:
        raise ValueError("Company name is required.")
    b = {
        "company": company,
        "title": f"{company} Intelligence Briefing",
        "artifact_name": f"{company} Daily Intel",
        "badge": one("badge").strip(),
        "updated": one("updated").strip(),
        "description": f"Daily {company} intelligence briefing with news, product updates, "
                       f"competitive landscape, and a financial snapshot.",
        "theme": {
            "dark": one("theme_dark", build_brief.DEFAULT_THEME["dark"]),
            "accent": one("theme_accent", build_brief.DEFAULT_THEME["accent"]),
            "light_row": one("theme_light_row", build_brief.DEFAULT_THEME["light_row"]),
            "border": one("theme_border", build_brief.DEFAULT_THEME["border"]),
        },
        "footer": one("footer").strip() or NEW_TEMPLATE["footer"],
    }
    if not b["updated"]:
        import datetime
        b["updated"] = datetime.date.today().strftime("%B %-d, %Y") \
            if sys.platform != "win32" else datetime.date.today().strftime("%B %d, %Y")
    for key in ("financials", "news", "products", "competitors"):
        raw = one(key, "[]")
        try:
            val = json.loads(raw)
            assert isinstance(val, list)
        except Exception as ex:
            raise ValueError(f"The '{key}' section isn't valid JSON: {ex}")
        b[key] = val
    return b


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    def _send(self, body, status=200, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # quiet

    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        try:
            if not parts:
                return self._send(home_page())
            head = parts[0]
            if head == "new":
                return self._send(editor_page())
            if head == "company" and len(parts) == 2:
                return self._send(viewer_page(parts[1]))
            if head == "edit" and len(parts) == 2:
                return self._send(editor_page(slug=parts[1]))
            if head == "regenerate" and len(parts) == 2:
                generate(parts[1])
                return self._redirect(f"/company/{parts[1]}")
            if head == "dashboard" and len(parts) == 2:
                ensure_generated(parts[1])
                path = os.path.join(GEN_DIR, parts[1], "index.html")
                with open(path, "rb") as f:
                    return self._send(f.read(), ctype="text/html; charset=utf-8")
            if head == "pdf" and len(parts) == 2:
                slug = parts[1]
                pdf_name = ensure_generated(slug)
                if not pdf_name:
                    return self._send(page("No PDF", '<div class="wrap"><div class="err">'
                                           'PDF export needs reportlab. Run '
                                           '<code>pip install reportlab</code>.</div></div>'), 503)
                path = os.path.join(GEN_DIR, slug, pdf_name)
                with open(path, "rb") as f:
                    return self._send(f.read(), ctype="application/pdf",
                                      headers={"Content-Disposition":
                                               f'attachment; filename="{pdf_name}"'})
            return self._send(page("Not found", '<div class="wrap"><h1>404</h1>'
                                   '<p><a href="/">Back to companies</a></p></div>'), 404)
        except FileNotFoundError:
            return self._send(page("Not found", '<div class="wrap"><h1>Not found</h1>'
                                   '<p><a href="/">Back to companies</a></p></div>'), 404)
        except Exception as ex:
            return self._send(page("Error", f'<div class="wrap"><div class="err">{html.escape(str(ex))}'
                                   '</div><p><a href="/">Back</a></p></div>'), 500)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/save":
            return self._send("Not found", 404, "text/plain")
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        existing = parse_qs(u.query).get("slug", [None])[0]
        try:
            b = build_from_form(form, existing)
        except ValueError as ex:
            # re-render editor with the error and the submitted values
            draft = {k: (form.get(k, [""])[0]) for k in ("company", "badge", "updated", "footer")}
            draft["theme"] = {"dark": form.get("theme_dark", ["#4c1d95"])[0],
                              "accent": form.get("theme_accent", ["#6d28d9"])[0],
                              "light_row": form.get("theme_light_row", ["#f7f4fc"])[0],
                              "border": form.get("theme_border", ["#e0d4f5"])[0]}
            for k in ("financials", "news", "products", "competitors"):
                try:
                    draft[k] = json.loads(form.get(k, ["[]"])[0])
                except Exception:
                    draft[k] = []
            return self._send(editor_page(slug=existing, b=draft, error=str(ex)), 400)
        slug = existing or slugify(b["company"])
        save_brief(slug, b)
        generate(slug)
        return self._redirect(f"/company/{slug}")


def main():
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\n  Company Intel Studio running at {url}")
    print(f"  Data:      {DATA_DIR}")
    print(f"  Generated: {GEN_DIR}")
    if not REPORTLAB_OK:
        print("  (PDF export disabled — run 'pip install reportlab' to enable)")
    print("  Press Ctrl+C to stop.\n")
    try:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
