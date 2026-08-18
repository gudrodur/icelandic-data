"""Health probe — Samgöngustofa bifreiðatölur (Transport Authority).

There is no scripts/samgongustofa.py — the skill documents a Playwright recipe
against `https://bifreidatolur.samgongustofa.is/` and nothing more. That page
is worth probing anyway, because the whole recipe rests on a chain that is
plain HTTP end to end:

    index.html -> js/script.js  (client-side router)
                -> partial/tolfraedi.html  (carries the <iframe> embed token)
                -> app.powerbi.com/view?r=<base64>  -> report key

The skill hardcodes none of those IDs, so the *constants* cannot drift — but
the chain can, and if it does the documented recipe silently scrapes an empty
page. Probing the site root alone would be worthless: it returns 200 with a
static shell even if every route below it is gone.

Lightweight: resolving the token and asking Power BI whether that report still
exists needs no browser. Only the DAX capture does, and that is manual-only.

**This probe cannot run from a GitHub-hosted runner, and its verdict is wrong.**
The 30-day window records `dead`, uptime 0.0, `last_ok: null` — 29 consecutive
ConnectTimeouts — while the host answers 200 in 50 ms from an Icelandic
connection. Measured from a runner on 2026-08-18 (egress 4.154.117.245, Azure):

    island.is                          200  connect 0.21s
    www.samgongustofa.is               302  connect 0.36s
    bifreidatolur.samgongustofa.is     connect timeout after 25s

DNS resolves correctly to 157.157.42.211 from both networks, so this is not
split-horizon DNS, not Iceland-wide filtering, and not even Samgöngustofa-wide:
the organisation's own main site answers. Something on this one host drops SYN
from that network.

So the source is healthy and the monitor is measuring its own reachability.
Until the probe runs from somewhere that can reach the host, read `dead` here as
"not observed", never as "withdrawn".
"""
from __future__ import annotations

import base64
import json
import re

import pytest

BASE = "https://bifreidatolur.samgongustofa.is"
ROUTER = f"{BASE}/js/script.js?v=2"
# The default route — "Tölfræði", the vehicles-by-make/fuel-type view the skill
# samples. Discovered from the router rather than assumed; see the fixture.
DEFAULT_PARTIAL = "partial/tolfraedi.html"

_TEMPLATE_RE = re.compile(r"templateUrl:\s*'([^']+)'")
_EMBED_RE = re.compile(r"app\.powerbi\.com/view\?r=([A-Za-z0-9_-]+)")


@pytest.fixture(scope="module")
def partials(http):
    """Routes the SPA declares. These are what the dashboard actually is."""
    r = http.get(ROUTER)
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code}"

    found = _TEMPLATE_RE.findall(r.text)
    assert found, (
        f"no templateUrl routes in {ROUTER} — the site was rewritten and the "
        f"samgongustofa skill's scrape recipe needs re-deriving"
    )
    return found


@pytest.fixture(scope="module")
def embed(http, partials):
    """The Power BI token embedded in the default route's partial."""
    assert DEFAULT_PARTIAL in partials, (
        f"{DEFAULT_PARTIAL} is no longer a declared route; routes are {partials}"
    )
    url = f"{BASE}/{DEFAULT_PARTIAL}"
    r = http.get(url)
    assert r.status_code == 200, f"{url} -> {r.status_code}"

    tokens = _EMBED_RE.findall(r.text)
    assert tokens, f"{url} -> 200 but carries no app.powerbi.com/view?r= iframe"

    token = tokens[0]
    payload = json.loads(base64.b64decode(token + "=" * (-len(token) % 4)))
    assert "k" in payload, f"embed token has no report key; got {sorted(payload)}"
    return f"https://app.powerbi.com/view?r={token}", payload["k"]


def test_dashboard_embeds_a_live_report(embed, powerbi):
    """Follows the token through to Power BI: an unpublished report answers 401
    here while the site itself still serves a perfectly healthy-looking page."""
    view_url, report_key = embed
    model = powerbi.model(view_url, report_key)
    assert powerbi.sections(model), "report resolved but exposes no pages"
