"""Vinnumálastofnun (Directorate of Labour) — mælaborð + Excel fetcher.

Two sources combined:
  1. Power BI dashboard "Gagnvirk tölfræði Vinnumálastofnunar"
  2. Excel workbook "Helstu talnagögn um atvinnuleysi"

Usage:
    uv run python scripts/vinnumalastofnun.py fetch     # both
    uv run python scripts/vinnumalastofnun.py excel     # Excel only
    uv run python scripts/vinnumalastofnun.py powerbi   # Power BI only
"""
import argparse
import asyncio
import base64
import json
import re
import sys
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "vinnumalastofnun"

POWERBI_TENANT = "764a306d-0a68-45ad-9f07-6f1804447cd4"
POWERBI_REPORT_KEY = "e74521bb-e501-4b02-8aa2-08a8bb84d087"
POWERBI_PAGE = "ReportSection7e7dca64570c18a74eb9"

# Contentful serves each upload at a fresh, content-addressed asset URL — the
# old one keeps working forever, so a stale constant here silently pins us to an
# old workbook rather than 404ing. The workbook is published monthly, so the URL
# rotates monthly: EXCEL_URL is only the fallback for when LANDING cannot be
# reached or links no workbook. cmd_excel resolves the current link from LANDING
# at run time; tests/health/test_vinnumalastofnun.py compares the fallback
# against the live page and reports degraded when they drift apart.
LANDING = "https://island.is/s/vinnumalastofnun/maelabord-og-toelulegar-upplysingar"
EXCEL_URL = (
    "https://assets.ctfassets.net/8k0h54kbe6bj/7BrzfSxUGzwSYipW36rSwK/"
    "f52da59cd4da46e37008a705a386b7fc/Talnagogn_atvinnuleysi.xlsm"
)

_ASSET_RE = re.compile(r"https://assets\.ctfassets\.net/[\w/-]+\.xlsm")


def discover_workbook_urls(page_html: str) -> set[str]:
    """Contentful .xlsm workbook links in a landing page body (shared with the health probe)."""
    return set(_ASSET_RE.findall(page_html))


def resolve_excel_url(client: httpx.Client | None = None) -> str:
    """Current workbook URL from LANDING, EXCEL_URL when undiscoverable.

    Prefers EXCEL_URL while the page still links it, so a reordered page does
    not flip the download to a different workbook unannounced.
    """
    try:
        if client is None:
            with httpx.Client(timeout=60, follow_redirects=True) as c:
                r = c.get(LANDING)
                r.raise_for_status()
                linked = discover_workbook_urls(r.text)
        else:
            r = client.get(LANDING)
            r.raise_for_status()
            linked = discover_workbook_urls(r.text)
    except Exception as e:
        print(f"could not resolve current workbook from {LANDING} ({e}); using fallback", file=sys.stderr)
        return EXCEL_URL
    if not linked:
        print(f"no workbook link on {LANDING}; using fallback", file=sys.stderr)
        return EXCEL_URL
    if EXCEL_URL in linked:
        return EXCEL_URL
    return sorted(linked)[0]


def _embed_url() -> str:
    payload = {"k": POWERBI_REPORT_KEY, "t": POWERBI_TENANT, "c": 8}
    token = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"https://app.powerbi.com/view?r={token}&pageName={POWERBI_PAGE}"


def cmd_excel(args=None):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "Talnagogn_atvinnuleysi.xlsm"
    url = resolve_excel_url()
    print(f"Downloading {url}", file=sys.stderr)
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        out.write_bytes(r.content)
    print(f"  → {out} ({len(r.content):,} bytes)", file=sys.stderr)


async def _scrape_powerbi() -> list[dict]:
    from playwright.async_api import async_playwright

    url = _embed_url()
    results: list[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()

            async def on_response(r):
                u = r.url.lower()
                if ("querydata" in u or "executequeries" in u) and r.status == 200:
                    try:
                        results.append(await r.json())
                    except Exception:
                        pass

            page.on("response", on_response)
            print(f"Loading {url}", file=sys.stderr)
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await asyncio.sleep(15)
        finally:
            await browser.close()
    return results


def cmd_powerbi(args=None):
    results = asyncio.run(_scrape_powerbi())
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "powerbi.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  captured {len(results)} query responses → {out}", file=sys.stderr)


def cmd_fetch(args=None):
    cmd_excel()
    cmd_powerbi()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", cmd_fetch), ("excel", cmd_excel), ("powerbi", cmd_powerbi)]:
        p = sub.add_parser(name)
        p.set_defaults(func=fn)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
