"""RÚV skoðanakannanir (opinion polls) — tag-page aggregator across pollsters.

Two-stage pipeline:
  1. `list`  — plain httpx GET of the tag page, parsed from the embedded
     __NEXT_DATA__ JSON blob (no browser needed; server-rendered).
  2. `fetch` — one article at a time via Playwright. Article bodies are
     client-side rendered (curl/httpx sees an empty shell), and the party
     support numbers live in a Highcharts bar chart whose bars carry a
     real `aria-label="<Party>, <pct>%."` attribute on each SVG <path> —
     that's the extraction target, not OCR or color-matching.

Usage:
    uv run python scripts/skodanakannanir.py list
    uv run python scripts/skodanakannanir.py list --scope reykjavik
    uv run python scripts/skodanakannanir.py fetch 479261
    uv run python scripts/skodanakannanir.py fetch --all --limit 20
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

TAG_URL = "https://www.ruv.is/frettir/tag/skodanakonnun"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "skodanakannanir"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

REYKJAVIK_KEYWORDS = re.compile(r"reykjav[ií]k|borgarst[jó]órn|í borginni", re.IGNORECASE)

# Case-sensitive and stem-based on purpose: "Prósent" is both a pollster's
# proper name and the ordinary Icelandic word for "percent" ("prósent"),
# which appears in nearly every poll subtitle lowercase mid-sentence
# ("...prósentustigi á eftir"). Matching case-sensitively on the
# capitalized stem is what actually distinguishes the two.
_POLLSTER_RE = re.compile(r"\b(Maskín\w*|Prósent\w*|Gallup\w*|Félagsvísindastofnun\w*)\b")
_POLLSTER_CANONICAL = {
    "maskín": "Maskína",
    "prósent": "Prósent",
    "gallup": "Gallup",
    "félagsvísindastofnun": "Félagsvísindastofnun",
}

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)


def _article_url(raw_url: str) -> str:
    """Article listing URLs use the nyr.ruv.is staging host; www.ruv.is serves the same content."""
    return raw_url.replace("nyr.ruv.is", "www.ruv.is").rstrip("/")


def _find_articles(node, out: list[dict]) -> list[dict]:
    if isinstance(node, dict):
        if node.get("__typename") == "Article" and "id" in node and node.get("title"):
            out.append(node)
        for v in node.values():
            _find_articles(v, out)
    elif isinstance(node, list):
        for v in node:
            _find_articles(v, out)
    return out


def _guess_scope(title: str, subtitle: str) -> str:
    text = f"{title} {subtitle or ''}"
    return "reykjavik" if REYKJAVIK_KEYWORDS.search(text) else "national"


def _guess_pollster(title: str, subtitle: str) -> str | None:
    text = f"{title} {subtitle or ''}"
    m = _POLLSTER_RE.search(text)
    if not m:
        return None
    for stem, canonical in _POLLSTER_CANONICAL.items():
        if m.group(1).lower().startswith(stem):
            return canonical
    return None


def fetch_article_list() -> list[dict]:
    resp = httpx.get(TAG_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    resp.raise_for_status()
    m = _NEXT_DATA_RE.search(resp.text)
    if not m:
        raise RuntimeError(f"__NEXT_DATA__ not found on {TAG_URL} — page structure changed")
    data = json.loads(m.group(1))
    articles = _find_articles(data, [])

    seen = {}
    for a in articles:
        seen[a["id"]] = {
            "id": a["id"],
            "title": a["title"],
            "subtitle": a.get("subtitle"),
            "url": _article_url(a["url"]),
            "published_at": a.get("first_published_at"),
            "scope": _guess_scope(a["title"], a.get("subtitle")),
            "pollster": _guess_pollster(a["title"], a.get("subtitle")),
        }
    return sorted(seen.values(), key=lambda r: r["published_at"] or "", reverse=True)


def cmd_list(args):
    articles = fetch_article_list()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RAW_DIR / "articles.json"
    out_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")

    shown = [a for a in articles if not args.scope or a["scope"] == args.scope]
    print(f"{len(shown)} poll articles ({out_file} holds all {len(articles)})")
    for a in shown[: args.limit]:
        pollster = a["pollster"] or "?"
        print(f"  [{a['id']}] {a['published_at'][:10]} ({a['scope']}, {pollster}) {a['title']}")


async def _scrape_article(url: str) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60_000)

        # Chart bars: SVG <path aria-label="Samfylking, 22.2%."> per party
        bars = await page.eval_on_selector_all(
            'path[aria-label*="%"]',
            "els => els.map(e => e.getAttribute('aria-label'))",
        )
        parties = []
        for label in bars:
            m = re.match(r"^(.+?),\s*([\d.,]+)\s*%\.?$", label.strip())
            if m:
                parties.append(
                    {"party": m.group(1).strip(), "pct": float(m.group(2).replace(",", "."))}
                )

        title = await page.title()
        await browser.close()

    return {"url": url, "page_title": title, "parties": parties}


def cmd_fetch(args):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    articles = json.loads((RAW_DIR / "articles.json").read_text(encoding="utf-8")) if (
        RAW_DIR / "articles.json"
    ).exists() else fetch_article_list()
    by_id = {a["id"]: a for a in articles}

    if args.all:
        targets = articles[: args.limit]
    elif args.article_id:
        if args.article_id not in by_id:
            print(f"Unknown article id {args.article_id} — run `list` first", file=sys.stderr)
            sys.exit(1)
        targets = [by_id[args.article_id]]
    else:
        print("Provide an article id or --all", file=sys.stderr)
        sys.exit(1)

    rows = []
    for meta in targets:
        print(f"  fetching [{meta['id']}] {meta['title']} ...")
        result = asyncio.run(_scrape_article(meta["url"]))
        if not result["parties"]:
            print(f"    no chart found (article may not include one)")
            continue
        for p in result["parties"]:
            rows.append(
                {
                    "article_id": meta["id"],
                    "published_at": meta["published_at"],
                    "scope": meta["scope"],
                    "pollster": meta["pollster"],
                    "title": meta["title"],
                    "party": p["party"],
                    "pct": p["pct"],
                }
            )
        (RAW_DIR / f"{meta['id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if not rows:
        print("No poll data extracted.")
        return

    df = pl.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PROCESSED_DIR / "skodanakannanir.csv"
    if out_file.exists():
        existing = pl.read_csv(out_file)
        df = pl.concat([existing, df], how="diagonal_relaxed").unique(
            subset=["article_id", "party"], keep="last"
        )
    df = df.sort(["published_at", "article_id", "party"])
    df.write_csv(out_file)
    print(f"{len(rows)} party-support rows written -> {out_file}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List poll articles from the RÚV tag page")
    p_list.add_argument("--scope", choices=["national", "reykjavik"], default=None)
    p_list.add_argument("--limit", type=int, default=20)
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="Scrape party-support numbers from one or more articles")
    p_fetch.add_argument("article_id", type=int, nargs="?", default=None)
    p_fetch.add_argument("--all", action="store_true", help="Fetch every listed article")
    p_fetch.add_argument("--limit", type=int, default=10)
    p_fetch.set_defaults(func=cmd_fetch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
