---
name: skodanakannanir
description: RÚV + Vísir opinion-poll aggregators (skoðanakannanir) — national Alþingi and Reykjavík city party support across pollsters (Maskína, Prósent, Gallup).
---

# Skoðanakannanir — RÚV + Vísir Opinion-Poll Aggregators

Two outlets' tag pages, each aggregating news coverage of opinion polls from
every major Icelandic pollster — not just one firm's own dashboard. Use this
skill for "what's the latest party support / fylgi flokka" questions, at
either national (Alþingi) or Reykjavík city (borgarstjórn) level.

**Use Vísir for discovery, RÚV for numbers.** Verified: RÚV's tag page holds
only ~51 recent items with no working pagination (see Caveat 7), while
Vísir's is genuinely paginated back to at least September 2021. `list
--source visir --since 2025 --scope reykjavik` alone found 40 Reykjavík polls
against RÚV's 4 — including the entire Feb–May 2026 city-election polling
season RÚV's own tag had already dropped. But only RÚV articles are wired
into `fetch`'s chart/prose number-extraction so far (see Vísir Discovery
below) — Vísir is list/discovery-only for now.

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

### Prose Fallback — When There's No Chart

Verified: articles 451831 and 428434 (both real Reykjavík polls, ~5,900+
chars each) have **zero** chart `<path>` elements. The numbers only exist in
prose, and extracting them correctly needs three Icelandic-grammar signals,
not proximity alone — verified against two full real articles end-to-end
(hand-traced, then run through Playwright, then cross-checked against a
manual reading of the rendered page):

1. **Verb mood distinguishes a current poll figure from a historical
   election result.** `mælist`/`mælast`/`fengi`/`fengju`/`stæði`/`stæðu`/
   `stendur` (conditional/present — "if the election were held now") mark a
   poll number; `fékk`/`fengu` (simple past) mark a result from an actual
   past election mentioned for comparison. These are genuinely distinct word
   forms in Icelandic, not a fuzzy heuristic.
2. **"nú" (now) beats verb-cue proximity when both appear in one sentence.**
   Historical baselines get phrased too many ways to enumerate as a verb
   list — `"fékk þá 19 prósent"`, `"tæp tólf í síðasta mánuði"`, `"hafa
   verið stöðugir í tæplega tólf prósent frá kosningum"` — but the *current*
   number is consistently marked `nú` whenever a sentence states both. When
   `nú` is present with 2+ percent numbers, it wins outright over the
   verb-proximity check.
3. **Nearest-party-to-number pairing, not first-party-in-sentence.**
   Comparison sentences ("Sjálfstæðisflokkurinn er langstærstur austan
   Elliðaáa með 39%, ... Samfylkingin mælist með 19%") name two parties —
   pairing every number in the sentence with whichever party is named first
   silently reattributes the second party's number to the first. Distance
   must be measured edge-to-edge (`min` over the four start/end
   combinations), not start-to-start — start-to-start systematically
   penalizes a long party name immediately before the number in favor of a
   short one further away.
4. **First mention per party wins; later re-mentions are ignored, not
   merged.** A party's topline citywide number is always stated once, early.
   Later re-mentions in the same article are sub-group breakdowns — verified
   example: article 451831 restates "Sjálfstæðisflokkurinn ... 39%" in a
   district-level paragraph ("east of Elliðaá") *after* already stating the
   citywide 29% earlier. Overwriting on second mention would silently
   replace the correct citywide topline with a geographic subset.

`extract_prose_poll_figures()` implements all four and returns
`(results, skipped)` — every sentence it declines to use is logged with a
reason (`no poll cue`, `historical, no poll cue`, `<party> already recorded,
later mention ignored`, `no party in context`, `unparsed number`), printed
via `fetch`'s `prose_skipped` count and saved in the raw `{id}.json`. Nothing
is silently dropped or guessed — a skip means "read this one by hand."

**Known residual gap:** constructions with no recognized poll-cue verb at
all — e.g. `"Fylgi Sósíalistaflokksins er farið úr 7,8 í 10,4 prósent"`
("went from X to Y") — are correctly skipped rather than mis-parsed, but
that also means they're **not extracted**. Verified on article 428434: 7 of
9 parties resolved automatically, 2 (Sósíalistaflokkur, Vinstri græn) needed
manual reading of the skipped-sentence log. Extending the cue-verb list is
possible but each new construction is a real (if small) NLP-scope increase
— weigh against just reading the skip log for the rare case.

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

## Vísir Discovery

`https://www.visir.is/t/2296/skodanakannanir/{page}` — server-rendered HTML
(no JSON blob), `<article class="article-item">` cards, genuinely paginated:
verified by fetching pages 1/5/10/20/40 and finding distinct,
chronologically-descending content from July 2026 (page 1) back through
September 2021 (page 20), with page 40 empty (end of history reached).
`fetch_visir_article_list()` walks pages until an empty page, or — with
`--since <year>` — until a whole page's articles are all older than the
cutoff (pages are date-descending, so that's a safe stopping point without
walking all ~35+ pages every time).

```html
<article class="article-item ...">
  <h2 class="article-item__title"><a href="/g/20262904348d/fylgi-...">Fylgi Sjálfstæðis­flokks ekki meira í sex ár</a></h2>
  <p class="article-item__text">Sjálfstæðisflokkurinn mælist með 24,9 prósenta fylgi í nýjum þjóðarpúlsi Gallups. ...</p>
  <time class="article-item__time">1.7.2026 19:45</time>
</article>
```

- **The listing subtitle (`article-item__text`) often states the headline
  number directly** — unlike RÚV's subtitles, which are usually pure prose
  summary. For a quick "what's the latest" answer, `list`'s output alone may
  already be enough; no need to visit the article page.
- Titles/subtitles carry HTML entities (`&#xF6;` = ö) and literal soft
  hyphens (`\xad`, rendered as `­`) mid-word from the source markup — both
  must be stripped/unescaped (`html.unescape` + `.replace("\xad", "")`) or
  matching against `_PARTY_RE`/`_POLLSTER_RE` silently fails on words that
  are visually identical but byte-different.
- Dates are Icelandic `D.M.YYYY HH:MM` (`"1.7.2026 19:45"`), converted to
  ISO 8601 by `_visir_date_to_iso()`.
- IDs are the numeric prefix of the `/g/<id>d/<slug>` URL path, stored as
  `visir-<id>` (RÚV ids are stored as `ruv-<id>` for the same reason —
  disambiguating which source's numbering a bare id belongs to once both
  are combined in one cache file).
- **Recurring feature to know about:** "Kosningaspá Vísis" (Vísir's own
  election-forecast/projection series) — not a raw poll report, an
  aggregated model. Shows up correctly under this skill's scope/pollster
  guessing as `pollster: null` (no known-pollster name in the text) since
  it isn't a single firm's poll.
- The same underlying poll is frequently reported by **both** RÚV and Vísir
  (and sometimes with a distinct Vísir angle, e.g. "Kosningaspá Vísis: ...").
  There is currently **no cross-source dedup/merge** — `list --source all`
  returns both as separate rows. Reconciling them (same pollster + adjacent
  dates + matching headline number → likely the same poll) is a known gap,
  not yet built.

## Script Usage

```bash
uv run python scripts/skodanakannanir.py list                                  # RÚV only (default) -> data/raw/skodanakannanir/articles.json
uv run python scripts/skodanakannanir.py list --source visir --since 2025      # Vísir only, paginated back to a year cutoff
uv run python scripts/skodanakannanir.py list --source all --since 2025 --scope reykjavik --limit 30
uv run python scripts/skodanakannanir.py fetch 479261                          # bare int = RÚV, backward-compatible
uv run python scripts/skodanakannanir.py fetch ruv-479261                      # equivalent, explicit
uv run python scripts/skodanakannanir.py fetch visir-20262904348               # errors clearly: not implemented yet, prints the URL to read by hand
uv run python scripts/skodanakannanir.py fetch --all --limit 20                # batch over cached RÚV articles only
```

## Data Files

| Path | Format | Description |
|------|--------|-------------|
| `data/raw/skodanakannanir/articles.json` | JSON | Article listing from whichever `--source` was last run (id prefixed `ruv-`/`visir-`, title, subtitle, url, published_at, scope, pollster, source) |
| `data/raw/skodanakannanir/{id}.json` | JSON | Raw scrape result for one RÚV article (page title + party/pct pairs) |
| `data/processed/skodanakannanir.csv` | CSV | Long-format party support, RÚV only so far: article_id, published_at, scope, pollster, title, party, pct |

## Caveats

1. **Not every poll article has a chart** — see Prose Fallback above.
   `fetch` tries the chart first, falls back to prose, and reports which
   source it used (`chart`/`prose`/`none`).
2. **`list`'s cache file always holds the full unfiltered set for whatever
   `--source` was requested** — `--scope` only filters what's printed to the
   terminal, not what's written to `articles.json`. But `--source` *does*
   determine what's in the cache: `list` (RÚV only) followed by `fetch
   visir-...` fails with "unknown article id" until you re-run `list
   --source all` (or `--source visir`) to populate the cache with Vísir rows
   too — verified, this is the actual failure mode, not a hypothetical.
3. **Percentages don't always sum to exactly 100** — verified example
   (article 479261) summed to 99.9 due to per-party rounding in the source
   chart. Treat as expected, not a parsing bug.
4. **`nyr.ruv.is` vs `www.ruv.is`** — the embedded JSON's `url` field points
   at the `nyr.` staging host; `_article_url()` rewrites it to `www.` before
   fetching. Same content either way, but `www.` is the citable public URL
   and still current as of the most recent articles checked (June 2026).
5. **`--all` launches one headless Chromium per article** — no batching
   inside a single browser session. Fine for a handful of articles; expect
   several seconds each for 20+.
6. **The prose fallback is scoped to `.article-body`, not all of `<main>`.**
   RÚV embeds "related article" teaser cards inline as `<aside>` elements
   between an article's own paragraphs — the `<aside>` itself only holds the
   kicker+title link, but the *excerpt paragraph* that follows it sits in a
   sibling `<div>` styled identically to the article's own paragraphs (same
   `.article-body .maincontent` class), so there is no DOM-level way to tell
   them apart by selector alone. That's exactly what item 4 of the Prose
   Fallback section (first-mention-per-party-wins) guards against — a
   teaser's re-mention of a party already recorded from the real article
   text is ignored rather than overwriting the correct number. `.article-body`
   only trims unrelated page chrome (nav, "most read," footer); it does not
   and cannot exclude the embedded teasers by itself.
7. **RÚV's own topic tagging is inconsistent — the `skodanakonnun` tag is
   not a complete index of poll articles.** Verified: a February 2026
   Reykjavík poll article (id 468121, found via a general web search) is
   tagged with every party name plus `Reykjavíkurborg`, but carries **no**
   `Skoðanakönnun` tag at all — most likely because party-name/location tags
   are auto-applied (entity detection over the content) while the topical
   `Skoðanakönnun` tag is set by a human editor and gets missed. Compounding
   this: **every RÚV tag page — `skodanakonnun`, `borgarstjorn`, and
   `reykjavikurborg` were all checked — caps at the ~51 most recent tagged
   items, with no working pagination** (`?page=2`/`?page=3` return byte-
   identical content to page 1). During a high-volume period (city-election
   season, Feb–May 2026 in this case) that window can be as short as a few
   weeks, silently dropping older-but-still-recent articles regardless of
   which tag you use. `list` surfaces only what's inside that live window —
   there is no way to page back further via any `frettir/tag/*` endpoint
   found so far. **Use `--source visir` (or `all`) instead of chasing this
   with `WebSearch`** — Vísir's tag page has none of these gaps (see Vísir
   Discovery above) and is the better default for anything historical.
   `WebSearch site:ruv.is` (the same fallback the [`ruv`](../ruv/SKILL.md)
   skill documents for `/sok`) remains a fine one-off check, just not the
   first move anymore.

8. **VB (Viðskiptablaðið) was checked and has no equivalent tag page** —
   spot-checked one poll article there (`vb.is/frettir/stal-i-stal-i-borginni-/`)
   with no `skodanakonnun`/`skoðanakönnun` tag found in the page. It does
   serve a `sitemap.xml` (200 OK), which could be a discovery path if VB
   coverage turns out to matter for a specific gap, but that's unexplored —
   not built, not verified beyond confirming the sitemap responds.

## Related Skills

- [maskina](../maskina/SKILL.md) — Maskína's own structured Tableau dashboard, one pollster, always current
- [ruv](../ruv/SKILL.md) — general RÚV news/TV search and download (tag-page pattern, yt-dlp)
- [reykjavik](../reykjavik/SKILL.md) — Reykjavík city open data (not polls, but same municipal-politics domain)
