---
name: company-intel-brief
description: >-
  Build a competitive company intelligence brief for any company, vendor, or competitor.
  Prompts for a company name, researches current news, product/technology updates, financials,
  and the competitive landscape, then produces BOTH a live HTML dashboard artifact AND a polished
  PDF — and sets up a daily 7 AM auto-refresh. Use this whenever the user wants an "intel brief",
  "intelligence briefing", "company brief", "competitor brief", "daily intel", or a "dashboard" on
  a company — e.g. "make me a brief on Wiz", "create a daily intel dashboard for Zscaler", "build a
  competitive briefing on Palo Alto", or just "intel on Acme Corp" — even if they don't name the
  exact output format. Also trigger when they ask to copy/clone an existing intel dashboard for a
  new company.
---

# Company Intelligence Brief

Generates a recurring competitive-intelligence briefing for a single company in two matching
formats from one content file: a live dashboard artifact (refreshes from the web) and a polished
PDF for sharing. A bundled script does all the rendering, so you only gather facts and assemble a
small JSON — you never hand-write HTML or PDF code.

The output has four parts, in this order: a header, a financial snapshot bar, a **News &
Announcements** section, a **Product & Technology** section, and a **Competitive Landscape** table.

## Step 1 — Get the company name

If the user already named a company, use it. Otherwise ask them: "Which company should I build the
intelligence brief for?" Wait for the answer before doing anything else — the whole brief is built
around that one company.

## Step 2 — Research (always current)

First check today's date (`date` in bash) so "recent" means recent. Run four web searches in
parallel, substituting the company name and current year:

1. `"<Company> news announcements press releases <month year>"`
2. `"<Company> product platform updates new features <year>"`
3. Financials — **public company:** `"<Company> <ticker> stock earnings analyst forecast <year>"`;
   **private company:** `"<Company> valuation funding revenue ARR investors <year>"`
4. `"<Company> competitors vs <known rivals> <year>"`

Determine whether the company is **public or private** — it changes the financial bar (Step 3).
Favor primary sources (the company newsroom, press releases, reputable outlets). Note that
private-company financials vary by source; treat them as estimates and say so in the footer.

## Step 3 — Assemble the brief JSON

Build a JSON file (see `assets/example_brief.json` for a complete, valid example) with these keys:

- `company`, `title` (usually "<Company> Intelligence Briefing"), `artifact_name`
  (e.g. "<Company> Daily Intel"), `badge`, `updated` (today, e.g. "June 22, 2026"), `description`.
- `badge`: for public companies use the exchange + ticker, e.g. `"NASDAQ: CRWD"`; for private use
  `"PRIVATE"` or `"PRIVATE · PRE-IPO"` (optionally append a category like `· NDR / XDR`).
- `theme`: four hex colors — `dark` (header + headings + table header), `accent` (card dates/titles),
  `light_row` (alternating rows), `border`. Pick a palette that nods to the company's brand but stays
  readable with white header text. Defaults to a violet scheme if you omit it. Suggested starting
  points: red `#8b0000`/`#c1121f`, green `#064d2c`/`#0b8f4e`, violet `#4c1d95`/`#6d28d9`,
  blue `#0b3d91`/`#1d4ed8`, teal `#0f766e`/`#14b8a6`. Use a distinct color per company so briefs
  are easy to tell apart at a glance.
- `financials`: 4–5 items, each `{label, value, sub}`.
  - **Public:** Analyst Consensus (Buy/Hold/Sell), Avg Price Target (+ % upside), ARR or Revenue
    (+ YoY), Revenue Guidance, Net New ARR — whatever is available and current.
  - **Private:** Ownership (+ key investors), Est. Valuation (+ round/date), Annual Recurring Revenue,
    Total Raised (+ # rounds), Headcount. Do NOT invent a stock price for a private company.
- `news`: the 5–7 most recent items, each `{date, title, desc}` with a one-sentence description.
- `products`: the 4–6 most notable recent launches/updates, each `{title, desc}`.
- `competitors`: 4 rows, each `{name, strength, advantage, level}` where `level` is `HIGH`,
  `MEDIUM`, or `LOW`. `strength` = the rival's edge over this company; `advantage` = where this
  company wins. Rate `level` by how much pressure the rival puts on this company in its core market.
- `footer`: one line; for private companies include that financials are estimates.

Save it as `brief.json` in your working directory.

## Step 4 — Render both outputs

Run the bundled generator (it needs only `reportlab`, which is preinstalled — no network):

```bash
python3 <skill-dir>/scripts/build_brief.py brief.json <output-dir>
```

It writes `<output-dir>/index.html` (self-contained dashboard) and
`<output-dir>/<Company>-Intelligence-Briefing.pdf`. Both come from the same JSON, so they always
match. If the company name has spaces the PDF filename uses hyphens.

## Step 5 — Create the live artifact

Call `mcp__cowork__create_artifact` with id `<company-slug>-daily-intel` (lowercase, hyphenated)
and `html_path` pointing at the generated `index.html`. If an artifact with that id already exists
(check `mcp__cowork__list_artifacts`), use `mcp__cowork__update_artifact` instead.

## Step 6 — Set up the daily auto-refresh (always)

Create a recurring task with `mcp__scheduled-tasks__create_scheduled_task`:
`taskId` = `<company-slug>-daily-intel`, `cronExpression` = `0 7 * * *`. The prompt MUST be fully
self-contained (scheduled runs start fresh with no memory of this conversation) — embed the company
name, its public/private status, the chosen theme colors, and these instructions: re-run the four
web searches for the latest info, rebuild `brief.json`, run `scripts/build_brief.py`, then update
the artifact `<company-slug>-daily-intel` via `mcp__cowork__update_artifact` and save a refreshed
PDF. Tell the user the task runs at 7 AM daily, that scheduled tasks only run while the app is open
(a missed run fires on next launch), and suggest they click "Run now" once to pre-approve the
web-search and artifact tools so future runs don't pause on permissions.

## Step 7 — Deliver

Present the PDF with `present_files`, then give a 2–3 sentence summary of the most important
developments you found. Mention the live dashboard is in the sidebar and refreshes daily.

## Notes

- Keep descriptions tight and factual — one sentence each. The value is current, well-sourced signal,
  not volume.
- Include a "Sources:" list of the URLs you used at the end of your chat reply.
- The threat-level colors are fixed (HIGH red, MEDIUM amber, LOW green) so briefs read consistently;
  only the `theme` colors change per company.
