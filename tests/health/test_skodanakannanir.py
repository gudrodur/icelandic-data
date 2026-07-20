"""Health probe — Skoðanakannanir (RÚV opinion-poll tag-page aggregator).

Contract: scripts/skodanakannanir.py's `list` subcommand depends on the tag
page still being server-rendered with a `__NEXT_DATA__` JSON blob containing
GraphQL `Article` objects (id/title/url/first_published_at). That is plain
HTTP and is what actually breaks if RÚV changes their Next.js build or their
GraphQL schema.

Lightweight, not `browser`: `fetch`'s Playwright scrape of individual article
pages (chart `aria-label` extraction) is not probed here, for the same reason
as `landlaeknir`/`vernd` — a failure from a datacenter IP says more about bot
detection than about the source being down. The precondition it depends on
(the tag page still listing articles at all) is what this probe covers.
"""
from __future__ import annotations

import pytest

from scripts.skodanakannanir import TAG_URL, _find_articles, _NEXT_DATA_RE
import json


def test_tag_page_serves_article_list(http):
    r = http.get(TAG_URL)
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"

    m = _NEXT_DATA_RE.search(r.text)
    assert m, f"{r.request.url} -> __NEXT_DATA__ script tag not found (page structure changed)"

    data = json.loads(m.group(1))
    articles = _find_articles(data, [])
    assert articles, f"{r.request.url} -> __NEXT_DATA__ parsed but no Article objects found"

    sample = articles[0]
    for key in ("id", "title", "url", "first_published_at"):
        assert key in sample, f"Article object missing expected key {key!r}: {sorted(sample)}"
