---
name: skodanakannanir
description: RÚV opinion-poll aggregator (skoðanakannanir) — national Alþingi and Reykjavík city party support across pollsters (Maskína, Prósent, Gallup).
---

# Skoðanakannanir — RÚV Opinion-Poll Aggregator

RÚV's `skodanakonnun` tag page aggregates news coverage of opinion polls from
every major Icelandic pollster — not just one firm's own dashboard. Use this
skill for "what's the latest party support / fylgi flokka" questions, at
either national (Alþingi) or Reykjavík city (borgarstjórn) level.

**Related but different scope:** the [`maskina`](../maskina/SKILL.md) skill
covers Maskína's own structured Tableau dashboard directly — one pollster,
always current. This skill covers the RÚV-reported layer across *all*
pollsters (Maskína, Prósent, Gallup, Félagsvísindastofnun), including polls
those firms only ever published as one-off RÚV stories.

## Two-Stage Pipeline

1. **`list`** — plain HTTP GET of the tag page, no browser needed. The page
   is server-rendered: `https://www.ruv.is/frettir/tag/skodanakonnun`
   embeds a full `__NEXT_DATA__` JSON blob containing every listed article
   (id, title, subtitle, url, `first_published_at`) as GraphQL `Article`
   objects. Walk the JSON tree for `"__typename": "Article"` nodes — do not
   regex the raw HTML, the JSON is already there and clean.

2. **`fetch <id>`** — one article's party-support numbers, via Playwright.
   **Article bodies are client-side rendered** — `httpx`/`curl` sees only
   the page chrome (nav, footer, ~0 chars of article text); the real content
   only exists in the DOM after JS hydration. Confirmed by comparing a raw
   `curl` fetch (empty `<main>`) against a Chrome DevTools MCP snapshot of
   the same URL (full prose + chart).

## Where the Numbers Actually Live

Poll articles that include a chart render it as **Highcharts**, and each bar
is an SVG `<path>` with a real `aria-label` attribute:

```html
<path aria-label="Samfylking, 22.2%." ...>
```

This is the extraction target — not OCR, not Highcharts internals, not
color-matching against Iceland's standard party colors (which the chart also
uses consistently, but the aria-labels are simpler and don't require a color
lookup table). In Playwright:

```python
bars = await page.eval_on_selector_all(
    'path[aria-label*="%"]',
    "els => els.map(e => e.getAttribute('aria-label'))",
)
# ["Samfylking, 22.2%.", "Sjálfstæðisflokkur, 19.3%.", ...]
```

Parse with `r"^(.+?),\s*([\d.,]+)\s*%\.?$"`.

## Article JSON Shape (from `__NEXT_DATA__`)

```json
{
  "__typename": "Article",
  "id": 479261,
  "title": "Samfylkingin stærst en Sjálfstæðisflokkur vinnur á",
  "subtitle": "Samfylkingin mælist með mest fylgi í könnun Maskínu en Sjálfstæðisflokkurinn er tveimur og hálfu prósentustigi á eftir. ...",
  "url": "https://nyr.ruv.is/frettir/innlent/2026-06-24-samfylkingin-staerst-en-sjalfstaedisflokkur-vinnur-a-479261/",
  "first_published_at": "2026-06-24T08:04:27.617332Z",
  "topic": {"category": {"slug": "innlent", "title": "Innlendar fréttir"}}
}
```

- `url` uses the `nyr.ruv.is` staging host in the embedded JSON — swap for
  `www.ruv.is`, both serve the same content but the public site is the
  documented one.
- `topic.category.slug` is always `innlent` for both national and Reykjavík
  polls — it does **not** distinguish scope. Guess scope from
  title/subtitle keywords instead (`reykjavík`, `borgarstjórn`, `í borginni`).
- `tags` is `null` in the listing query (per-article tags like `maskína`,
  `Skoðanakönnun`, party names only appear on the rendered article page,
  not in this JSON).

## Pollster Detection — the "Prósent" Trap

**"Prósent" is both a pollster's proper name and the ordinary Icelandic word
for "percent."** A case-insensitive substring match on `prósent` false-fires
on nearly every poll subtitle, because generic phrases like
`"...prósentustigi á eftir"` contain the substring. The fix verified against
real data: match case-sensitively on the **capitalized stem**
(`\bPrósent\w*\b`), since the common noun is lowercase mid-sentence in
practice and the company name is not:

```python
_POLLSTER_RE = re.compile(r"\b(Maskín\w*|Prósent\w*|Gallup\w*|Félagsvísindastofnun\w*)\b")
```

`Maskína`/`Gallup`/`Félagsvísindastofnun` have no ordinary-word collision and
would work case-insensitively too, but the shared regex is simpler to keep
one way.

## Scope Detection

`national` vs `reykjavik`, guessed from title+subtitle:
`r"reykjav[ií]k|borgarst[jó]órn|í borginni"` (case-insensitive). This is a
geography classifier, not a topic classifier — a Reykjavík-scope poll about
airport siting (`Reykjavíkurflugvöllur`) will be tagged `reykjavik` even
though it isn't a party-support question. That's expected: the skill scopes
by *where*, not *what*.

## Script Usage

```bash
uv run python scripts/skodanakannanir.py list                      # all articles -> data/raw/skodanakannanir/articles.json
uv run python scripts/skodanakannanir.py list --scope reykjavik    # filter the printed view (cache always holds all)
uv run python scripts/skodanakannanir.py fetch 479261              # one article's chart -> data/processed/skodanakannanir.csv
uv run python scripts/skodanakannanir.py fetch --all --limit 20    # batch (slow: one browser launch per article)
```

## Data Files

| Path | Format | Description |
|------|--------|-------------|
| `data/raw/skodanakannanir/articles.json` | JSON | Full article listing from the tag page (id, title, subtitle, url, published_at, scope, pollster) |
| `data/raw/skodanakannanir/{id}.json` | JSON | Raw scrape result for one article (page title + party/pct pairs) |
| `data/processed/skodanakannanir.csv` | CSV | Long-format party support: article_id, published_at, scope, pollster, title, party, pct |

## Caveats

1. **Not every poll article has a chart.** Some report numbers in prose only
   (verified: article 428434, a Reykjavík poll, has 0 chart `<path>`
   elements despite being a real ~5,900-character article). `fetch` prints
   "no chart found" and skips cleanly rather than guessing from text —
   there is no prose-number extraction here, by design; read those
   manually.
2. **`list`'s cache file always holds the full unfiltered set.** `--scope`
   only filters what's printed to the terminal, not what's written to
   `articles.json` — so `fetch` can resolve any article id regardless of
   which `--scope` you last listed with.
3. **Percentages don't always sum to exactly 100** — verified example
   (article 479261) summed to 99.9 due to per-party rounding in the source
   chart. Treat as expected, not a parsing bug.
4. **`nyr.ruv.is` vs `www.ruv.is`** — the embedded JSON's `url` field points
   at the `nyr.` staging host; `_article_url()` rewrites it to `www.` before
   fetching. Same content either way, but `www.` is the citable public URL.
5. **`--all` launches one headless Chromium per article** — no batching
   inside a single browser session. Fine for a handful of articles; expect
   several seconds each for 20+.

## Related Skills

- [maskina](../maskina/SKILL.md) — Maskína's own structured Tableau dashboard, one pollster, always current
- [ruv](../ruv/SKILL.md) — general RÚV news/TV search and download (tag-page pattern, yt-dlp)
- [reykjavik](../reykjavik/SKILL.md) — Reykjavík city open data (not polls, but same municipal-politics domain)
