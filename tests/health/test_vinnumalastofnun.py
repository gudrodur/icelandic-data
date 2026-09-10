"""Health probe — Vinnumalastofnun (Directorate of Labour).

scripts/vinnumalastofnun.py has two upstreams, and only one of them can fail
loudly on its own:

  1. **The Excel workbook on Contentful.** Contentful is content-addressed: each
     monthly upload lands on a *new* asset URL and the old one keeps serving
     200 forever. So a dead constant never 404s — it just quietly pins us to an
     old workbook. The script resolves the current link from the landing page
     at run time (EXCEL_URL is only the fallback), so the probe checks two
     different things: that the resolved URL still serves a workbook (hard),
     and that the fallback is still the URL island.is links (degraded — the
     download works, it just leans on a fallback that is now behind).
  2. **The Power BI embed.** Report key still published, and the default page
     the script deep-links to (POWERBI_PAGE) still exists in the report.

All plain HTTP. The Playwright scrape itself is manual-only by policy; what
this asserts is its precondition.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from scripts.vinnumalastofnun import (
    EXCEL_URL,
    LANDING,
    POWERBI_PAGE,
    POWERBI_REPORT_KEY,
    _embed_url,
    discover_workbook_urls,
    resolve_excel_url,
)
from tests.health.conftest import assert_fresh

XLSM_TYPE = "application/vnd.ms-excel.sheet.macroenabled.12"


def test_excel_workbook_is_served(http):
    """HEAD only — a health probe never pulls the half-megabyte workbook."""
    url = resolve_excel_url(http)
    r = http.head(url)
    assert r.status_code == 200, f"{url} -> {r.status_code}"
    assert r.headers["content-type"].startswith(XLSM_TYPE), r.headers["content-type"]
    assert int(r.headers["content-length"]) > 10_000, (
        f"{url} -> suspiciously small workbook: {r.headers['content-length']} bytes"
    )


@pytest.mark.degraded_ok
def test_hardcoded_excel_url_is_the_current_upload(http):
    """Degraded, not failed: the script resolves the workbook at run time and
    only falls back to EXCEL_URL, so a stale fallback changes nothing today.
    This is the only signal that a new workbook was published and the fallback
    constant should follow it."""
    r = http.get(LANDING)
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"

    linked = discover_workbook_urls(r.text)
    assert linked, (
        f"no .xlsm workbook link on {LANDING} — the page was "
        f"restructured, or the workbook was removed"
    )
    assert EXCEL_URL in linked, (
        f"EXCEL_URL in scripts/vinnumalastofnun.py is behind: {LANDING} now "
        f"links {sorted(linked)} — Contentful rotated the asset URL, update the constant"
    )


@pytest.fixture(scope="module")
def model(powerbi):
    return powerbi.model(_embed_url(), POWERBI_REPORT_KEY)


def test_powerbi_default_page_still_exists(model, powerbi):
    """The script deep-links `&pageName=`; a renamed page means it lands on a
    report page that never fires the DAX queries the scrape is waiting for."""
    sections = powerbi.sections(model)
    assert POWERBI_PAGE in sections, (
        f"page {POWERBI_PAGE} absent from the report; pages are now "
        f"{sorted(sections.values())}"
    )


@pytest.mark.degraded_ok
def test_powerbi_data_is_recent(model, powerbi):
    """Monthly publication, second week of the following month."""
    assert_fresh(
        powerbi.last_refresh(model),
        timedelta(days=45),
        label="vinnumalastofnun dashboard dataset refresh",
    )
