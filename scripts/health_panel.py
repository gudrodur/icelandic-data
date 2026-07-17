"""Render the source-health light panel as an SVG.

Deanchored from the codebase on purpose. The SVG is written to the
`health-history` branch next to `history.jsonl` and `badge.json`, and the README
just points an <img> at its raw URL. So the panel refreshes daily without a
single commit to main — no bot noise in the history of the actual project, and
nothing to review. Same trick as the shields badge above it.

    uv run python scripts/health_panel.py --history health/history.jsonl -o panel.svg

The badge is the headline (one light, 7-day bar, for a stranger deciding whether
to trust the repo). This is the detail view: the current verdict per source, for
someone checking the one source they actually care about.

Plain shapes and text only — GitHub sanitises SVG and strips scripts, and camo
proxies it. Colours are picked to read on both light and dark backgrounds, since
an <img> cannot see the viewer's theme.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from datetime import datetime, timezone
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from scripts.health_verdict import judge_all, load  # noqa: E402

# Probe name -> display name. Probes are machine names (`umferd`); humans read
# "Umferð". Anything not listed renders under its probe name.
DISPLAY = {
    "hagstofan": "Hagstofa Íslands",
    "sedlabanki": "Seðlabanki",
    "tekjusagan": "Tekjusagan",
    "velsaeldarvisar": "Velsældarvísar",
    "heimsmarkmid": "Heimsmarkmið",
    "rikisreikningur": "Ríkisreikningur",
    "landlaeknir": "Landlæknir",
    "vinnumalastofnun": "Vinnumálastofnun",
    "farsaeld_barna": "Farsæld barna",
    "maelabord_landbunadarins": "Mælaborð landb.",
    "ferdamalastofa": "Ferðamálastofa",
    "umferd": "Umferð",
    "byggdastofnun": "Byggðastofnun",
    "vernd": "Vernd",
    "skatturinn": "Skatturinn",
    "nasdaq": "Nasdaq Iceland",
    "fuel": "Fuel",
    "maskina": "Maskína",
    "opnirreikningar": "Opnir reikningar",
    "tenders": "Tenders",
    "hms": "HMS",
    "skipulagsmal": "Skipulagsmál",
    "samgongustofa": "Samgöngustofa",
    "car": "car (island.is)",
    "vedur": "Veður",
    "loftgaedi": "Loftgæði",
    "co2": "CO2",
    "lmi": "LMI",
    "lmi_hrl": "LMI HRL",
    "natt": "Náttúrufr.stofnun",
    "eea_sdi": "EEA SDI",
    "laun": "Laun",
    "gengi": "Gengi",
    "domstolar": "Dómstólar",
    "reykjavik": "Reykjavíkurborg",
    "fjarlog": "Fjárlög",
}

# Mid-tone fills, legible on white and on #0d1117 alike.
COLOR = {
    "healthy": "#2da44e",
    "flaky": "#d29922",
    "dead": "#cf222e",
    "broken": "#cf222e",
    "unknown": "#8b949e",
}

COLS = 3
ROW_H = 22
PAD = 14
HEADER_H = 34
COL_W = 210
DOT_R = 5


def _row(x: float, y: float, label: str, color: str, title: str) -> str:
    return (
        f'<g><title>{escape(title)}</title>'
        f'<circle cx="{x + DOT_R}" cy="{y - 4}" r="{DOT_R}" fill="{color}"/>'
        f'<text x="{x + DOT_R * 2 + 8}" y="{y}" class="l">{escape(label)}</text>'
        f"</g>"
    )


def render(history: pathlib.Path, window_days: int = 30) -> str:
    verdicts = judge_all(load(history, window_days))
    # Worst first — if something is broken, it should be the first thing seen.
    counts = {k: sum(1 for v in verdicts if v.verdict == k) for k in COLOR}

    rows = max(1, -(-len(verdicts) // COLS))  # ceil
    w = PAD * 2 + COL_W * COLS
    h = PAD * 2 + HEADER_H + rows * ROW_H

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = "  ".join(
        f"{counts[k]} {k}" for k in ("dead", "broken", "flaky", "healthy", "unknown") if counts[k]
    )

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="Source health: {escape(summary)}">',
        "<style>"
        ".l{font:12px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;fill:#57606a}"
        ".h{font:600 13px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;fill:#24292f}"
        ".s{font:11px -apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;fill:#8b949e}"
        "@media (prefers-color-scheme:dark){.l{fill:#8b949e}.h{fill:#e6edf3}}"
        "</style>",
        f'<text x="{PAD}" y="{PAD + 12}" class="h">Source health</text>',
        f'<text x="{w - PAD}" y="{PAD + 12}" class="s" text-anchor="end">{escape(stamp)}</text>',
        f'<text x="{PAD}" y="{PAD + 27}" class="s">{escape(summary)}</text>',
    ]

    for i, v in enumerate(verdicts):
        col, row = i % COLS, i // COLS
        x = PAD + col * COL_W
        y = PAD + HEADER_H + row * ROW_H + 12
        label = DISPLAY.get(v.source, v.source)
        note = f"{v.verdict}"
        if v.uptime is not None:
            note += f" · {v.uptime:.0%} of {v.observations} obs"
        if v.last_error:
            note += f" · {v.last_error[:80]}"
        out.append(_row(x, y, label, COLOR.get(v.verdict, "#8b949e"), f"{label}: {note}"))

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history", type=pathlib.Path, required=True)
    ap.add_argument("-o", "--out", type=pathlib.Path, default=pathlib.Path("panel.svg"))
    ap.add_argument("--window-days", type=int, default=30)
    args = ap.parse_args(argv)

    args.out.write_text(render(args.history, args.window_days), encoding="utf-8")
    print(f"panel -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
