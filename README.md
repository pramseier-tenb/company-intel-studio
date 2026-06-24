# Company Intel Studio

Generate competitive **company intelligence briefs** — a live HTML dashboard and a
polished, print-ready PDF — for any company, from a single content file. Pick a company,
view its branded dashboard, and download the PDF.

This repo ships two ways to use the same engine:

- **`webapp/`** — a local web app (Python standard library) with a visual company picker,
  inline dashboard viewer, PDF download, and an editor for every field.
- **`skill/`** — a [Claude](https://claude.com) skill (`company-intel-brief`) that researches a
  company from the web and produces a ready-to-render brief. Also bundled as the installable
  `company-intel-brief.skill`.

Both share the same generator, `build_brief.py`, so output is identical everywhere.

**Four briefs ship preloaded: CrowdStrike, Tanium, Vectra AI, Brinqa.**

## Quick start (web app)

```bash
cd webapp
pip install -r ../requirements.txt   # installs reportlab (for PDF)
python3 app.py                       # opens http://127.0.0.1:5050
```

Pick a company from the grid (CrowdStrike, Tanium, Vectra AI, and Brinqa are preloaded),
view its dashboard, and click **Download PDF**. Use **Edit / Regenerate** to change any
field or **+ New company** to add one. On macOS you can double-click `webapp/run.command`.

> The dashboard renders without any dependencies; only the **PDF** export needs `reportlab`.

## The brief format

Each company is one JSON file (see `webapp/data/*.json` or `skill/assets/example_brief.json`):

| Section | Field | Shape |
|---|---|---|
| Header | `company`, `title`, `badge`, `updated` | strings |
| Theme | `theme` | `{dark, accent, light_row, border}` hex colors |
| Financial bar | `financials` | list of `{label, value, sub}` |
| News & Announcements | `news` | list of `{date, title, desc}` |
| Product & Technology | `products` | list of `{title, desc}` |
| Competitive Landscape | `competitors` | list of `{name, strength, advantage, level}` — `level` is `HIGH`/`MEDIUM`/`LOW` |

Render it directly with the generator:

```bash
python3 webapp/build_brief.py path/to/brief.json output_dir/
# writes output_dir/index.html and output_dir/<Company>-Intelligence-Briefing.pdf
```

## The skill

`skill/` is a Claude skill that prompts for a company name, researches current news,
products, financials, and competitors, auto-detects public vs. private to shape the
financial bar, and generates the dashboard + PDF (and can set up a daily refresh).
Install `company-intel-brief.skill` in a Claude client that supports skills, or run the
skill folder directly.

## Repository layout

```
Company-Intel-Studio/
├── README.md
├── LICENSE                       # MIT
├── requirements.txt              # reportlab
├── .gitignore
├── company-intel-brief.skill     # installable skill package
├── webapp/
│   ├── app.py                    # local web server (stdlib only)
│   ├── build_brief.py            # HTML + PDF generator (shared)
│   ├── run.command               # macOS double-click launcher
│   └── data/                     # one <slug>.json per company
└── skill/
    ├── SKILL.md
    ├── scripts/build_brief.py
    └── assets/example_brief.json
```

## License

MIT — see [LICENSE](LICENSE).
