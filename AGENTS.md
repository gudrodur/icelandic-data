# Icelandic Data Toolkit

Data toolkit for Icelandic public data. Each skill in `.agents/skills/` documents one data source — API endpoints, series codes, encoding quirks, classification changes. Scripts in `scripts/` fetch, clean, and transform the data.

## Architecture

```
/.agents/skills/{source}/SKILL.md   # Data source docs (API, endpoints, caveats)
/scripts/{source}.py                # Fetch + transform scripts (uv project)
/tests/health/test_{source}.py      # Upstream health probe (marker: health)
/data/
  /raw/{source}/                    # Raw downloads (Excel, CSV, JSON)
  /processed/                       # Cleaned datasets
```

Skills follow the [agentskills.io](https://agentskills.io) open standard, so the same
`SKILL.md` files work in both Claude Code and Codex:

- `.agents/skills/` is the real location — read natively by Codex.
- `.claude/skills` is a symlink to it, so Claude Code discovers the same files.
- `CLAUDE.md` is a symlink to `AGENTS.md`, so both agents read these instructions.

Skill names must be lowercase, ASCII, hyphen-separated (no underscores, no `ð`/`æ`).

## Skills

Each skill documents ONE data source:
- API endpoints and authentication
- Available series and their scope
- Tariff codes, variable mappings, classification changes
- Example fetch commands
- Known caveats (encoding, date ranges, schema changes)

There is deliberately no index of skills here. Each `SKILL.md` carries a `description`
in its frontmatter, and that description is what both agents preload and match against —
a table in this file would be a second, staler copy that cannot trigger anything.
Run `ls .agents/skills/` to enumerate them.

Keep each `description` under ~160 characters: Codex truncates when all descriptions
combined exceed 8,000 characters, and with 45 skills that budget is the binding constraint.

**When asked about a new data source:** follow the `new-data-source` skill.

## Write-ups live elsewhere

This repo fetches and queries. Memos, plans and kept reports for Sósíalistaflokkur Íslands
go to `~/Code/xj-accounts/research/` (copy any `reports/*.html` worth keeping there with a
date prefix — `reports/` here is git-ignored).

## HTML Reports

When asked for a report, produce a **single self-contained `.html` file** in `/reports/`:
- Embed data as JSON in `<script>` tags
- Use Chart.js (CDN) — `<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>`
- No build step, no dependencies

Style: system fonts, max-width `960px`, cards with `border-radius: 12px`, Chart.js in `.chart-wrap` at `height: 360px`.

## Adding a New Data Source

Follow the methodology in the `new-data-source` skill — covers discovery, probing, skill authoring, script conventions, health probes, testing, and visualization. Scripts must also follow `docs/python-scripting-gold-standard.md` (CLI, httpx, polars, paths, encoding, probes). Summary:

1. **Discover** — find the API type (REST, WFS, Power BI, scraping), probe endpoints, document schema
2. **Skill** — create `.agents/skills/{source}/SKILL.md` with frontmatter, API, schema, request examples, caveats
3. **Script** — create `scripts/{source}.py` with `list`/`fetch` subcommands (polars + httpx)
4. **Test** — verify output with DuckDB, check Icelandic encoding, spot-check values
5. **Health probe** — add `tests/health/test_{source}.py` so upstream breakage surfaces on its own
6. **Visualize** — HTML report (Chart.js/Leaflet) or static map (geopandas + cached LMI layers — Tier 1, `--group maps`)
7. **Register** — add a Quick Command to `docs/quick-commands.md` (never to this file); the skill's `description` is its own index entry

## Requirement tiers

Every skill belongs to exactly one tier, declared in a `**Requires:**` line
directly under its title. Tier 0 must stay installable with a single `uv sync`
on macOS, Linux and Windows — that is the contract that lets a newcomer with
Claude Desktop or ChatGPT Desktop use the toolkit. Anything heavier is opt-in.

| Tier | Name | Install | What it gates | Rule |
|---|---|---|---|---|
| 0 | core | `uv sync` | polars, httpx, duckdb, openpyxl, iceaddr, playwright (package only) | Pure-Python wheels, no system libraries, no browser download. ~40 skills. |
| 1 | maps | `uv sync --group maps` | geopandas, rasterio, pyproj, shapely, matplotlib, numpy | Wheels exist on all platforms but are large. Map scripts import these lazily or live in map-only scripts. |
| 2 | browser | `uv run playwright install chromium` | Chromium for Playwright | Power BI, Tableau, JS-rendered pages. The Python package is Tier 0; only the ~150 MB browser is opt-in. |
| 3 | pdf | `uv sync --group pdf` | docling, liteparse | Torch-sized. `pdfplumber` (Tier 0) covers native-text PDFs; this tier is for scanned/complex tables. |
| 4 | restricted | none | Icelandic IP (samgongustofa), Sprite/R2 credentials (annual-report-cache), mac-mini ops | Documented so an agent can explain why, never silently required. |

Rules when adding or changing a skill:

- Put `**Requires:** Tier N (name) — one-line reason` as the first body line. Tier 0
  skills say `**Requires:** Tier 0 (core).` so the absence is never ambiguous.
- A Tier 0 script must not import a Tier 1/3 package at module top; import it
  inside the function that needs it, with a clear error naming the group.
- A skill that is mostly Tier 0 with one heavier command (e.g. `hms` + landeignaskrá
  build) stays Tier 0 and names the exception in its `Requires` line.
- Never add a dependency to the core list in `pyproject.toml` that needs a compiler,
  a system library, or a browser. Put it in a group and, if new, add a tier row here.
- `scripts/setup_check.py` reports which tiers are present; keep its module lists in
  step with this table. CI runs the fast suite core-only and with `maps` on all three
  OSes.

## Tools

Everything runs on macOS, Linux and Windows. The only prerequisite is `uv`
(https://docs.astral.sh/uv/) — it downloads Python and every dependency itself.
`./setup.sh` (macOS/Linux) or `.\setup.ps1` (Windows) installs `uv` if missing,
runs `uv sync`, and then `scripts/setup_check.py`, which verifies imports and
repairs the `.claude/skills` link (git on Windows and GitHub ZIP downloads turn
symlinks into plain files; the checker recreates a symlink or a junction). After a
junction repair on Windows, `git status` shows `.claude/skills` as a typechange
permanently — expected; do not `git checkout -- .claude/skills`, that brings the
text file back.

No Homebrew, no system Python, no DuckDB binary. SQL on local files goes through
`scripts/sql.py`, which wraps the `duckdb` Python package:

```bash
uv run python scripts/sql.py "SELECT * FROM 'data/processed/fuel_prices_daily.csv' LIMIT 5"
uv run python scripts/sql.py --csv "SELECT ..." > out.csv
```

`jq` is optional; `uv run python -m json.tool` pretty-prints JSON on every platform.

Windows: use `uv run python scripts/...` exactly as documented (works in
PowerShell). `setup.ps1` sets `PYTHONUTF8=1` so Icelandic characters print
correctly. Always pass `encoding="utf-8"` to `open()` / `read_text()` /
`write_text()` in scripts — Windows defaults to cp1252 otherwise.

Python (managed by `uv`; Tier 0 unless noted):
- `duckdb` - SQL on CSV/Parquet/JSON (via `scripts/sql.py`)
- `polars` - Fast DataFrame library
- `openpyxl` - Excel file reading
- `httpx` - HTTP client
- `playwright` - Headless browser automation (Tier 2 once Chromium is installed)
- `pdfplumber` - PDF text/table extraction
- `docling` - AI-powered PDF extraction with 97.9% table accuracy (IBM) — Tier 3, `--group pdf`
- `iceaddr` - Icelandic address geocoding (bundled SQLite from Staðfangaskrá)

## Quick Commands

Per-source fetch and process commands (one block per dataset) live in [docs/quick-commands.md](docs/quick-commands.md). Read it before running or adding a source command; most skills in `.agents/skills/` also name their own commands.

## Tests and source health

```bash
uv run ruff check . --fix              # lint — every selected rule is a CI error; no warnings
uv run pytest -m "not slow"            # fast, offline — what PR CI runs
uv run pytest -m slow                  # network + Playwright integration tests

# Upstream health probes (tests/health/) — smallest stable contract per source
uv run pytest -m health                        # every probe
uv run pytest -m health -k hagstofan           # one source by name
uv run pytest -m "health and not degraded_ok"   # required lane
uv run pytest -m "health and degraded_ok"      # staleness / known-soft lane
uv run pytest -m health                        # every probe

# Render today's snapshot from both lanes
uv run python scripts/health_summary.py --required health-required.xml \
  --degraded health-degraded.xml --json health-results.json

# Judge over history — this is what gates CI (a lone red is a flake)
uv run python scripts/health_verdict.py --history .history/history.jsonl --window-days 30
```

Health probes run daily in `.github/workflows/source-health.yml`, on the
self-hosted mac-mini (`solberg.club`, labels `self-hosted` + `iceland`) — the
runner exists because GitHub-hosted runners sit in Azure datacenters with no
Iceland region: geo-fenced sources like `bifreidatolur.samgongustofa.is`
answer Icelandic IPs in ~50 ms but `ConnectTimeout` from every GitHub runner,
and Power BI/Tableau bot detection trips on datacenter IPs. There is no
`browser` lane anymore — the one probe that used it (`samgongustofa`, plain
HTTP) was only geo-fence-blocked, and the mini fixed that.

Note that `degraded_ok` is **not** an escape hatch for an unreachable source: a
degraded row is still a non-healthy observation to `health_verdict.py`, so three
in a row still read `dead` and still gate. Only `skipped` rows (and no rows at
all) are excluded from the streak.

To add a probe for a new source, see the `new-data-source` skill.

### Flake vs dead

A single red means almost nothing, so nothing gates on one. Two mechanisms
separate a blip from a corpse:

**The exception class, free and immediate.** A *structural* failure (assertion,
401, 404) means the service answered and answered **wrong** — schema drift, an
expired dashboard id, a revoked key. That essentially never self-heals, so the
skill is already out of date and needs updating. An *infra* failure (connect
timeout, DNS, 5xx) means we could not reach it, which is genuinely ambiguous and
needs history. `scripts/health_summary.py:classify()` makes this split.

**History, for the ambiguous half.** Each run appends one JSONL observation per
source to the orphan `health-history` branch — git scraping, in Simon Willison's
sense: the file is the database, git is the retention policy, DuckDB is the query
engine. `scripts/health_verdict.py` then judges:

| Verdict | Rule | Gates CI |
|---|---|---|
| `broken` | 2+ consecutive **structural** failures — fix the skill | yes |
| `dead` | 3+ consecutive failures | yes |
| `flaky` | failed but recovered | no |
| `healthy` | clean across the window | no |
| `unknown` | fewer than 2 observations | no |

Streaks count **consecutive observations, never calendar days**. GitHub documents
that scheduled runs may be dropped entirely, so a gap in the history means *not
observed*, not *down* — and uptime is `healthy/observed`, never `healthy/elapsed`.

```bash
# Uptime per source, straight off the JSONL — no ingest step
git fetch origin health-history && git show origin/health-history:history.jsonl > /tmp/h.jsonl
uv run python scripts/sql.py "
SELECT source,
       round(100.0 * count(*) FILTER (WHERE status='healthy') / count(*), 1) AS uptime_pct,
       count(*) AS observations,
       max(ts) FILTER (WHERE status='healthy')::date AS last_ok
FROM read_json_auto('/tmp/h.jsonl')
WHERE ts > now() - INTERVAL 30 DAY AND status != 'skipped'
GROUP BY source ORDER BY uptime_pct;"
```

### The blind spot: GitHub cannot alert you that GitHub stopped

Scheduled runs can be dropped silently, and scheduled workflows in public repos
are auto-disabled after 60 days of repository inactivity (GitHub never defines
"activity"). Both fail closed and quiet: no run, no failure, no email. The daily
history commits are genuine activity and plausibly hold that clock off, but
that is inference, not a documented contract — so it is not the safety net.

The safety net is a dead-man's-switch: something *outside* GitHub that notices
the **absence** of observations.

**Live mechanism — pull, from the mac-mini** (`solberg.club`):

| | |
|---|---|
| Script | `~/clawd/bin/icelandic-data-dms.sh` |
| Schedule | `~/Library/LaunchAgents/com.jokull.icelandic-data-dms.plist` (every 6h) |
| Logs | `~/clawd/logs/icelandic-data-dms.log` |
| Alert | Telegram via `openclaw message send` |

It polls the GitHub API for the age of the last commit on `health-history`. Over
36h (two missed runs, allowing for cron drift) → Telegram alert, with a 20h
cooldown so it nags once a day rather than once a run. It sends an all-clear on
recovery, and stays silent when healthy.

It watches **the monitor, not the sources** — "is anyone still watching?" Source
health is already answered, with detail, by the workflow. Keep that separation:
a switch that also opines on source health is a switch that can cry wolf.

Pull beats push here: it needs no inbound ingress and no secret, and it catches
the auto-disable case (where the workflow never runs to push anything) that a
push-ping structurally cannot.

**Keeping the mini's clone current.** The runner checks out its own workspace
per run, so `~/Code/icelandic-data` (used by local/agent sessions on the mini)
has nothing keeping it fresh on its own — it drifted 11 commits behind
`origin/main` at least once. A periodic ff-only pull fixes that:

| | |
|---|---|
| Script | `~/clawd/bin/icelandic-data-pull.sh` |
| Schedule | `~/Library/LaunchAgents/com.jokull.icelandic-data-pull.plist` (every 6h + at load) |
| Logs | `~/clawd/logs/icelandic-data-pull.log` |
| Alert | Telegram via `openclaw message send` — but only on divergence/network failure |

`--ff-only` never clobbers local work; a divergent clone alerts instead of
force-pulling.

Three properties worth preserving if you touch it:

- **Unreachable ≠ stale.** If the API can't be reached after 3 tries it logs
  UNKNOWN and stays silent — the likeliest cause is the mini's own network, and
  alerting on that trains you to ignore it. (This fired on the very first
  launchd run; the retry recovered on attempt 2.)
- **It never stamps the cooldown on a failed send.** Otherwise a deaf switch
  silences itself for 20h while nobody knows anything is wrong.
- **It pins node explicitly.** `node` here is fnm-managed at a per-shell path
  that does not exist under launchd; the `openclaw` shim then resolves a
  different node and dies on a native sqlite ABI mismatch. The script pins the
  same interpreter + entrypoint as `ai.openclaw.gateway.plist`. Keep them in
  step across openclaw upgrades.

**Optional alternative — push.** `source-health.yml` also has an inert ping step
for anyone without the mini; set `HEALTH_PING_URL` (e.g. healthchecks.io) to
enable. It fires when the probes **ran and recorded**, whatever the verdict —
never on job success, or a legitimately dead source would silence the switch.

**Residual blind spot:** the switch depends on the mini and its Gateway being up.
If the mini dies, nothing alerts. That is accepted — you would notice — but it
is where the turtles stop.

## Scripts layout

- `scripts/*.py` — fetchers/cleaners: hit an API or read raw files, write tidy CSVs to `data/processed/`
- `scripts/health_summary.py` — renders health results from pytest JUnit XML (not a fetcher)
- `tests/health/test_{source}.py` — upstream health probes, auto-marked `slow` + `health`
- `reports/*.py` — one-off report scripts (gitignored, local-only, sit next to the `.html` they emit)

Inflation-specific analysis (derivation scripts, research reports, the whodunit blog post) lives in [`~/Code/inflation-whodunit`](../inflation-whodunit). That repo reads processed data from here.
