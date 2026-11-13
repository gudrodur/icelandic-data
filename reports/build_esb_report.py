"""Build reports/esb_kannanir_2026.json — hand-verified ESB poll report.

Every figure was hand-checked against the article prose on 2026-08-01
(five auto-extractions were corrected by hand — see extraction.method).
Article titles/urls/timestamps are enriched from the skodanakannanir
discovery cache (data/raw/skodanakannanir/articles.json).
"""

import json
from pathlib import Path

# Repo root, resolved from this file so the script runs from any cwd. It was
# a hardcoded absolute home path while this file was untracked; now that it is
# in git it has to work on someone else's machine.
ROOT = Path(__file__).resolve().parent.parent
cache = {a["id"]: a for a in json.loads(
    (ROOT / "data/raw/skodanakannanir/articles.json").read_text())}


# Articles discovery structurally cannot reach, so the cache can never hold
# them. ruv-483052 carries the Áfram Ísland poll's cleanest topline, and RÚV
# never tagged it "Skoðanakönnun" — see the skodanakannanir skill, Caveat 7.
UNLISTED = {
    "ruv-483052": {
        "source": "ruv",
        "title": "Hnífjafnt milli fylkinga",
        "url": "https://www.ruv.is/frettir/innlent/2026-08-06-hnifjafnt-milli-fylkinga-483052",
        "published_at": "2026-08-06T08:11:00",
    },
}


def art(article_id, **extra):
    """Enrich one article id from the discovery cache.

    Raises on a miss rather than emitting nulls. articles.json is OVERWRITTEN
    by each `list` run, so it holds only the last --source requested: building
    right after `list --source visir` used to strip every RÚV article in this
    report down to a bare id with title=None and url=None, quietly, and the
    report still looked well-formed. Run
    `list --source all --since 2025 --topic esb` before building.
    """
    a = cache.get(article_id) or UNLISTED.get(article_id)
    if a is None:
        raise SystemExit(
            f"{article_id} is in neither the discovery cache "
            f"({len(cache)} articles) nor UNLISTED. Run:\n"
            "  uv run python scripts/skodanakannanir.py list --source all "
            "--since 2025 --topic esb\n"
            "and if discovery genuinely cannot see it, add it to UNLISTED."
        )
    return {
        "source": a.get("source", article_id.split("-")[0]),
        "id": article_id,
        "title": a.get("title"),
        "url": a.get("url"),
        "published_at": a.get("published_at"),
        **extra,
    }


REPORT = {
    "meta": {
        "title": "ESB-skoðanakannanir 2026",
        "description": (
            "All EU-membership (ESB) opinion polls published in 2026 found via "
            "the maskina skill (WordPress API + Tableau VizQL) and the "
            "skodanakannanir skill (RÚV/Vísir/Heimildin aggregators, --topic esb). "
            "Every figure hand-verified against the article prose; five "
            "auto-extractions were corrected by hand (see extraction.method). "
            "Excluded: visir-20262917099 (Maskína, 2026-08-04) asks whether interest "
            "rates would fall and whether a fisheries exemption is likely — an "
            "attitudes poll, not voting intention."
        ),
        "generated": "2026-08-19",
        "period_covered": {"from": "2026-01-01", "to": "2026-08-19"},
        "referendum": {
            "date": "2026-08-29",
            "question": "Á Ísland að hefja á ný aðildarviðræður við Evrópusambandið?",
            "type": "þjóðaratkvæðagreiðsla",
        },
        "sources": {
            "skills": [
                ".agents/skills/maskina/SKILL.md",
                ".agents/skills/skodanakannanir/SKILL.md",
            ],
            "discovery_commands": [
                "uv run python scripts/skodanakannanir.py list --source all --since 2025 --topic esb",
                "curl 'https://maskina.is/wp-json/wp/v2/posts?search=ESB&after=2026-01-01T00:00:00'",
            ],
            "verification": (
                "Hand-read article prose for every poll; auto-extracted values "
                "kept only where they matched the text. Tableau workbook "
                "12_01_2026-ESB_virur read directly via VizQL for the January "
                "Maskína poll."
            ),
        },
        "question_framings": {
            "membership": "Aðild sjálf: 'Ert þú hlynnt(ur) eða andvíg(ur) því að Ísland gangi í ESB?'",
            "talks": "Aðildarviðræður: support for (resuming/continuing) accession negotiations",
            "referendum_vote": "Atkvæðið: how the respondent would vote in the 2026-08-29 referendum",
            "referendum_approval": "Afstaða til þess að atkvæðagreiðslan sé haldin yfirhöfuð",
            "note": (
                "The three framings measure systematically differently and are "
                "not interchangeable: membership itself polls negative all year, "
                "talks poll positive, and the referendum vote itself has stayed "
                "narrowly 'já' in every direct measurement (52, 52, 52/48, 53/47)."
            ),
        },
        "result_bases": {
            "all": "share of all respondents",
            "decided": "share of those who took a stance (afstöðu tekið)",
            "unspecified": "article does not state the basis unambiguously",
        },
        "extractor_gaps_found": [
            {
                "gap": "NATO synonym missing from _ESB_EXCLUDE_RE",
                "detail": (
                    "'Atlantshafsbandalagið'/'bandalagið' not excluded (only "
                    "'varnarbandalag' is) — visir-20262838574's NATO figures "
                    "(78/17/9) were extracted as ESB figures."
                ),
                "independent_examples": 2,
                "meets_fix_threshold": True,
            },
            {
                "gap": "'greiða atkvæði með/gegn' vocabulary not recognized",
                "detail": (
                    "The referendum-vote phrasing carries no já/nei/hlynnt/andvígt "
                    "answer term — toplines skipped in visir-20262902621 and "
                    "visir-20262853438, subgroup numbers extracted instead."
                ),
                "independent_examples": 2,
                "meets_fix_threshold": True,
            },
            {
                "gap": "demographic-subgroup sentences unguarded",
                "detail": (
                    "Sentences scoped to karla/kvenna/aldurshópa pair as toplines "
                    "(62/22 = women's numbers in visir-20262853438; 63/58 = age "
                    "groups in visir-20262902621). _NON_SUPPORT_TOPIC_RE guards "
                    "kjósend-/fylgismann- subgroups but not demographic ones."
                ),
                "independent_examples": 2,
                "meets_fix_threshold": True,
            },
        ],
    },
    "polls": [
        {
            "poll_id": "maskina-2025-12-kryddsild",
            "published": "2026-01-12",
            "pollster": "Maskína",
            "commissioned_by": "Sýn (Kryddsíld)",
            "population": "national",
            "fieldwork": {"note": "3.–15. október 2025 (per article methodology); Tableau wave labelled 2025-12-01"},
            "sample": {"size": 1765, "panel": "Þjóðgátt", "weighting": "Þjóðskrá"},
            "questions": [
                {
                    "framing": "talks",
                    "question_text": "Ef haldin verður atkvæðagreiðsla um áframhaldandi aðildarviðræður við ESB, myndir þú greiða atkvæði með eða á móti?",
                    "results": [
                        {"answer": "Með (hlynnt)", "pct": 53.0, "basis": "decided"},
                        {"answer": "Á móti (andvígt)", "pct": 47.0, "basis": "decided"},
                    ],
                    "change": {"vs": "2024-12", "med_pct_then": 50.9, "delta_pt": 2.1},
                    "extraction": {"method": "auto_verified", "note": "cross-checked against Tableau workbook waves"},
                }
            ],
            "structured_data": {
                "tableau_workbook": "12_01_2026-ESB_virur",
                "tableau_view": "Frtt-ESB",
                "worksheet": "helstu-ESB (2)",
                "waves": [
                    {"date": "2024-12-01", "med_pct": 50.9, "a_moti_pct": 49.1},
                    {"date": "2025-12-01", "med_pct": 53.0, "a_moti_pct": 47.0},
                ],
            },
            "articles": [
                {"source": "maskina", "id": "maskina-6202",
                 "title": "53% hlynnt áframhaldandi aðildarviðræðum við ESB",
                 "url": "https://maskina.is/53-hlynnt-aframhaldandi-adildarvidraedum-vid-esb/",
                 "published_at": "2026-01-12"},
                art("visir-20262827389"),
            ],
        },
        {
            "poll_id": "gallup-2026-02-thjodarpuls",
            "published": "2026-02-04",
            "pollster": "Gallup",
            "commissioned_by": None,
            "series": "Þjóðarpúls",
            "population": "national",
            "fieldwork": {"from": "2026-01-21", "to": "2026-02-02"},
            "sample": {"size": 1672, "response_rate_pct": 48.8},
            "questions": [
                {
                    "framing": "membership",
                    "question_text": "Hlynnt(ur) eða andvíg(ur) aðild Íslands að Evrópusambandinu?",
                    "results": [
                        {"answer": "Hlynnt", "pct": 42.0, "basis": "all"},
                        {"answer": "Andvígt", "pct": 42.0, "basis": "all"},
                    ],
                    "change": {"vs": "2025", "andvigt_delta_pt": 6, "hlynnt_delta_pt": -2},
                    "extraction": {
                        "method": "hand_corrected",
                        "note": (
                            "Auto-extraction returned the same poll's NATO figures "
                            "(hlynnt 78 / hvorki né 17 / andvígt 9) because "
                            "'Atlantshafsbandalaginu' is not in _ESB_EXCLUDE_RE."
                        ),
                    },
                }
            ],
            "related_non_esb_questions": [
                {"topic": "NATO membership", "results": {"hlynnt": 78, "hvorki_ne": 17, "andvigt": 9}}
            ],
            "articles": [
                art("visir-20262838574"),
                art("ruv-466122", note="Same-day security-survey angle; correctly yielded no ESB figures"),
            ],
        },
        {
            "poll_id": "gallup-2026-03-referendum",
            "published": "2026-03-09",
            "pollster": "Gallup",
            "commissioned_by": None,
            "series": "Þjóðarpúls",
            "population": "national",
            "fieldwork": {"note": "not stated beyond 'nýr Þjóðarpúls'"},
            "sample": {"size_note": "rúmlega 800 þátttakendur"},
            "questions": [
                {
                    "framing": "referendum_approval",
                    "question_text": "Hlynnt(ur) eða andvíg(ur) þjóðaratkvæðagreiðslunni um framhald aðildarviðræðna?",
                    "results": [
                        {"answer": "Hlynnt", "pct": 58.0, "basis": "all",
                         "breakdown": {"alfarið": 33, "mjög": 12, "frekar": 13}},
                        {"answer": "Hvorki né", "pct": 12.0, "basis": "all"},
                        {"answer": "Andvígt", "pct": 30.0, "basis": "all",
                         "breakdown": {"frekar": 7, "mjög": 5, "alfarið": 18}},
                    ],
                    "extraction": {
                        "method": "hand_corrected",
                        "note": "Auto-extraction returned the women's subgroup (hlynnt 62 / andvígt 22) as the topline.",
                    },
                },
                {
                    "framing": "referendum_vote",
                    "question_text": "Hvernig myndir þú líklegast greiða atkvæði ef þjóðaratkvæðagreiðslan væri haldin í dag?",
                    "results": [
                        {"answer": "Með áframhaldandi viðræðum", "pct": 52.0, "basis": "unspecified"},
                        {"answer": "Hætta viðræðum", "pct": 48.0, "basis": "unspecified"},
                    ],
                    "extraction": {"method": "hand_corrected", "note": "Skipped by auto-extraction ('kjósa með' phrasing outside vocabulary)."},
                },
            ],
            "articles": [art("visir-20262853438")],
        },
        {
            "poll_id": "si-members-2026-03",
            "published": "2026-03-09",
            "pollster": None,
            "commissioned_by": "Samtök iðnaðarins",
            "population": "si_members",
            "population_note": "Félagsmenn SI — interest-group survey, not a national sample",
            "fieldwork": {"note": "febrúar–mars 2026"},
            "questions": [
                {
                    "framing": "membership",
                    "results": [
                        {"answer": "Andvígt", "pct": 57.0, "basis": "all",
                         "breakdown": {"mjög_andvíg": 43}},
                        {"answer": "Hlynnt", "pct": 25.0, "approx": True, "basis": "all",
                         "breakdown": {"mjög_fylgjandi": 10, "frekar_hlynnt": 15}},
                    ],
                    "change": {"vs": "2024", "note": "mjög andvíg nearly doubled; mjög fylgjandi fell 17 → 10"},
                    "extraction": {
                        "method": "hand_corrected",
                        "note": "Auto-extraction recorded hlynnt 10 (only the 'mjög fylgjandi' component).",
                    },
                }
            ],
            "articles": [art("visir-20262853308")],
        },
        {
            "poll_id": "gallup-vb-2026-04",
            "published": "2026-04-07",
            "pollster": "Gallup",
            "commissioned_by": "Viðskiptablaðið",
            "population": "national",
            "fieldwork": {"note": "byrjun apríl 2026"},
            "questions": [
                {
                    "framing": "membership",
                    "results": [
                        {"answer": "Hlynnt", "pct": 40.0, "basis": "all"},
                        {"answer": "Andvígt", "pct": 47.0, "basis": "all"},
                        {"answer": "Hvorki né", "pct": 13.0, "basis": "all"},
                    ],
                    "extraction": {
                        "method": "auto_verified",
                        "note": "Two independent articles agree; figures restated in visir-20262895588's retrospective.",
                    },
                }
            ],
            "articles": [art("visir-20262866089"), art("visir-20262866297")],
        },
        {
            "poll_id": "maskina-2026-04",
            "published": "2026-04-15",
            "pollster": "Maskína",
            "commissioned_by": None,
            "population": "national",
            "questions": [
                {
                    "framing": "membership",
                    "question_text": "Afstaða til aðildar Íslands að ESB í dag",
                    "results": [{"answer": "Andvígt", "pct": 46.0, "basis": "unspecified"}],
                    "change": {"vs": "2025-04", "andvigt_pct_then": 39.8},
                    "extraction": {"method": "auto_verified", "note": "Verified in SKILL.md regression set."},
                },
                {
                    "framing": "talks",
                    "results": [{"answer": "Hlynnt", "pct": 42.0, "basis": "unspecified"}],
                    "extraction": {"method": "auto_verified"},
                },
            ],
            "multi_question_note": "Same article asks both membership and talks — the two figures answer different questions.",
            "articles": [art("visir-20262869821")],
        },
        {
            "poll_id": "gallup-vb-2026-06",
            "published": "2026-06-10",
            "pollster": "Gallup",
            "commissioned_by": "Viðskiptablaðið",
            "population": "national",
            "questions": [
                {
                    "framing": "membership",
                    "question_text": "Ert þú hlynnt(ur) eða andvíg(ur) því að Ísland gangi í Evrópusambandið (ESB)?",
                    "results": [
                        {"answer": "Hlynnt", "pct": 39.0, "basis": "all"},
                        {"answer": "Andvígt", "pct": 47.0, "basis": "all"},
                        {"answer": "Hvorki né", "pct": 13.0, "basis": "all"},
                        {"answer": "Hlynnt", "pct": 46.0, "basis": "decided"},
                        {"answer": "Andvígt", "pct": 54.0, "basis": "decided"},
                    ],
                    "extraction": {"method": "auto_verified", "note": "Verified in SKILL.md; bases confirmed by hand-read 2026-08-01."},
                }
            ],
            "articles": [art("visir-20262895588")],
        },
        {
            "poll_id": "maskina-dv-2026-06",
            "published": "2026-06-13",
            "pollster": "Maskína",
            "commissioned_by": "DV",
            "population": "national",
            "fieldwork": {"from": "2026-06-02", "to": "2026-06-11"},
            "sample": {"size": 1856, "decided": 1558},
            "questions": [
                {
                    "framing": "talks",
                    "results": [
                        {"answer": "Hlynnt", "pct": 44.5, "basis": "all"},
                        {"answer": "Andvígt", "pct": 39.4, "basis": "all"},
                        {"answer": "Veit ekki", "pct": 14.6, "basis": "all"},
                        {"answer": "Vildu ekki svara", "pct": 1.5, "basis": "all"},
                        {"answer": "Hlynnt", "pct": 53.1, "basis": "decided"},
                        {"answer": "Andvígt", "pct": 46.9, "basis": "decided"},
                    ],
                    "extraction": {"method": "auto_verified", "note": "Verified in SKILL.md; bases confirmed by hand-read 2026-08-01."},
                }
            ],
            "articles": [art("visir-20262897210")],
        },
        {
            "poll_id": "gallup-2026-06-thjodarpuls",
            "published": "2026-06-27",
            "pollster": "Gallup",
            "commissioned_by": None,
            "series": "Þjóðarpúls",
            "population": "national",
            "fieldwork": {"from": "2026-06-12", "to": "2026-06-24", "mode": "netkönnun, Viðhorfahópur Gallup"},
            "sample": {"size": 1993, "response_rate_pct": 41.1},
            "questions": [
                {
                    "framing": "referendum_vote",
                    "question_text": "Ef þjóðaratkvæðagreiðsla færi fram í dag þar sem spurt væri: 'Á Ísland að hefja á ný aðildarviðræður við Evrópusambandið?', hvernig telur þú líklegast að þú myndir greiða atkvæði?",
                    "results": [
                        {"answer": "Já (með)", "pct": 52.0, "basis": "unspecified"},
                        {"answer": "Nei (gegn)", "pct": 48.0, "basis": "unspecified"},
                    ],
                    "extraction": {
                        "method": "hand_corrected",
                        "note": (
                            "Auto-extraction returned age subgroups (já 63 = 18–29 ára, "
                            "nei 58 = 30–39 ára); topline phrasing 'greiða atkvæði "
                            "með/gegn' is outside the answer vocabulary."
                        ),
                    },
                }
            ],
            "articles": [art("visir-20262902621")],
        },
        {
            "poll_id": "gallup-sa-2026-07",
            "published": "2026-07-28",
            "pollster": "Gallup",
            "commissioned_by": "Samtök atvinnulífsins",
            "population": "sa_member_companies",
            "population_note": "Aðildarfyrirtæki SA — company survey, not a national sample",
            "questions": [
                {
                    "framing": "membership",
                    "results": [{"answer": "Andvígt", "pct": 66.0, "basis": "all"}],
                    "extraction": {
                        "method": "auto_verified",
                        "note": "Verified in SKILL.md; the same survey's euro-adoption question is correctly excluded by _ESB_EXCLUDE_RE.",
                    },
                }
            ],
            "articles": [art("visir-20262914497")],
        },
        {
            "poll_id": "maskina-dv-2026-07",
            "published": "2026-07-30",
            "pollster": "Maskína",
            "commissioned_by": "DV",
            "population": "national",
            "fieldwork": {"from": "2026-07-22", "to": "2026-07-29"},
            "questions": [
                {
                    "framing": "referendum_vote",
                    "question_text": "Atkvæði í þjóðaratkvæðagreiðslunni 29. ágúst um framhald aðildarviðræðna",
                    "results": [
                        {"answer": "Já", "pct": 53.0, "basis": "decided"},
                        {"answer": "Nei", "pct": 47.0, "basis": "decided"},
                        {"answer": "Já", "pct": 43.8, "basis": "all"},
                        {"answer": "Nei", "pct": 38.9, "basis": "all"},
                        {"answer": "Veit ekki", "pct": 13.5, "basis": "all"},
                        {"answer": "Vildu ekki svara", "pct": 3.8, "basis": "all"},
                    ],
                    "extraction": {"method": "auto_verified", "note": "Verified in SKILL.md; bases confirmed by hand-read 2026-08-01."},
                }
            ],
            "articles": [art("visir-20262915377")],
        },
        {
            "poll_id": "gallup-2026-07-afram-island",
            "published": "2026-08-06",
            "pollster": "Gallup",
            "commissioned_by": "Áfram Ísland",
            "population": "national",
            "fieldwork": {"from": "2026-07-15", "to": "2026-07-30"},
            "sample": {"size": 1996, "respondents": 804, "response_rate_pct": 40.3},
            "questions": [
                {
                    "framing": "referendum_vote",
                    "question_text": "Á Ísland að hefja á ný aðildarviðræður við Evrópusambandið?",
                    "results": [
                        {"answer": "Já", "pct": 46.0, "basis": "all"},
                        {"answer": "Nei", "pct": 46.0, "basis": "all"},
                        {"answer": "Óákveðin", "pct": 8.0, "basis": "all"},
                    ],
                    "breakdowns": [
                        "Reykjavík 55% fylgjandi; landsbyggðin 56% andvíg; Kraginn um 50% fylgjandi og rúm 40% á móti.",
                        "Viðreisn 93% og Samfylking 89% fylgjandi, Flokkur fólksins 70%.",
                        "Miðflokkur 95%, Sjálfstæðisflokkur 82% og Framsókn 69% ætla að segja nei.",
                    ],
                    "extraction": {
                        "method": "hand_entered",
                        "note": (
                            "Neither source yields this poll automatically. RÚV states the "
                            "topline cleanly but never tagged the article 'Skoðanakönnun', so "
                            "discovery cannot list it (skodanakannanir SKILL.md, Caveat 7); "
                            "Vísir lists it but words the result as one number covering two "
                            "answers — 'Átta prósent segjast óákveðin en 46 prósent eru síðan "
                            "á sitt hvorri hliðinni, já og nei' — which the extractor correctly "
                            "declines to guess at. Read by hand from ruv-483052 on 2026-08-19."
                        ),
                    },
                }
            ],
            "caveats": [
                "Commissioned by Áfram Ísland, a campaign organisation opposed to resuming "
                "talks. Gallup did the fieldwork; the commissioner belongs in every citation.",
                "The 46/46 split is of ALL respondents, undecided included — not of those "
                "taking a stance, which is the basis Gallup's own þjóðarpúls and Maskína use. "
                "Plotting it in the same series as a decided-basis figure without saying so "
                "would overstate a swing that is partly a change of denominator.",
                "Vísir's write-up says 'einungis 40% sem tóku afstöðu til spurningarinnar', "
                "which cannot be reconciled with 46+46=92% taking a stance; it looks like the "
                "40,3% response rate restated. RÚV's figures are used here.",
            ],
            "articles": [
                art("ruv-483052"),
                art("visir-20262917613"),
            ],
        },
        {
            "poll_id": "maskina-2026-08",
            "published": "2026-08-13",
            "pollster": "Maskína",
            "commissioned_by": None,
            "population": "national",
            "fieldwork": {"note": "Published 2026-08-13; window not stated in the coverage."},
            "questions": [
                {
                    "framing": "referendum_vote",
                    "question_text": "Ætlar þú að segja já eða nei við því að Ísland hefji að nýju aðildarviðræður við Evrópusambandið?",
                    "results": [
                        {"answer": "Já", "pct": 52.2, "basis": "decided"},
                        {"answer": "Nei", "pct": 47.8, "basis": "decided"},
                        {"answer": "Veit ekki", "pct": 10.0, "basis": "all"},
                        {"answer": "Vildu ekki svara", "pct": 3.1, "basis": "all"},
                    ],
                    "change": {
                        "vs": "2026-06",
                        "lead_pt_now": 4.4,
                        "lead_pt_then": 6.2,
                        "note": "Já lækkar um 0,9 stig frá júní (53,1), Nei hækkar um 0,9 (46,9). Breytingin er innan skekkjumarka. Í lok júlí mældist 53/47.",
                    },
                    "breakdowns": [
                        "Rúmlega 61% þeirra sem taka afstöðu í Reykjavík ætla að segja já; tæp 53% í nágrannasveitarfélögunum.",
                        "Andstaðan mest á Austurlandi, þar sem tæp 63% ætla að segja nei.",
                        "Rúmlega 60% háskólamenntaðra ætla að segja já; tæp 57% þeirra með grunnskólapróf ætla að segja nei.",
                    ],
                    "extraction": {
                        "method": "auto_verified",
                        "note": "Extractor returned Já 52,2 / Nei 47,8; confirmed against prose 2026-08-19 and the 4,4 stiga forskot matches the subtitle. 13,1% taka ekki afstöðu alls (10% veit ekki, 3,1% vilja ekki svara); Já/Nei á öllum svarendum var ekki birt, svo sá grunnur er ekki skráður.",
                    },
                }
            ],
            "articles": [art("visir-20262920711")],
        },
        {
            "poll_id": "gallup-2026-08-thjodarpuls",
            "published": "2026-08-14",
            "pollster": "Gallup",
            "commissioned_by": "Þjóðarpúls",
            "population": "national",
            "fieldwork": {
                "from": "2026-08-01",
                "to": "2026-08-13",
                "note": "RÚV states it: 'Nýi þjóðarpúlsinn var gerður dagana 1.–13. ágúst.'",
            },
            "sample": {"size": 4128, "response_rate_pct": 41.9},
            "questions": [
                {
                    "framing": "referendum_vote",
                    "question_text": "Atkvæði í þjóðaratkvæðagreiðslunni 29. ágúst um framhald aðildarviðræðna",
                    "results": [
                        {"answer": "Já", "pct": 51.5, "basis": "decided"},
                        {"answer": "Nei", "pct": 48.5, "basis": "decided"},
                        {"answer": "Óákveðin", "pct": 7.0, "basis": "all"},
                        {"answer": "Vildu ekki svara", "pct": 1.0, "basis": "all"},
                    ],
                    "margin_of_error_pt": 2.5,
                    "significance": "Munurinn er ekki tölfræðilega marktækur (vikmörk 2,5 prósentustig).",
                    "breakdowns": [
                        "14% þeirra sem segjast kjósa Miðflokkinn ætla að segja já, á móti 9% Sjálfstæðismanna.",
                        "Tæplega níu af hverjum tíu sem styðja ríkisstjórnina hyggjast segja já; 14% þeirra sem styðja hana ekki.",
                    ],
                    "extraction": {
                        "method": "hand_corrected",
                        "note": "Extractor returned Já 48,5 / Nei 48,5 / Óákveðin 1,0 — it reused 48,5 for both sides and read the 1% 'vildi ekki svara' as undecided, missing the 7% óákveðin. Prose reads: '51,5% þeirra sem tóku afstöðu sögðust ætla að greiða atkvæði með og 48,5% þeirra á móti'. Corrected by hand 2026-08-19.",
                    },
                }
            ],
            "articles": [
                art("ruv-483977"),
                art("visir-20262921222"),
                art("visir-20262921428"),
                art("ruv-483994", role="analysis companion, not a separate poll"),
                art("ruv-483992", role="analysis companion, not a separate poll"),
            ],
        },
    ],
}

out = ROOT / "reports/esb_kannanir_2026.json"
out.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n")
n_polls = len(REPORT["polls"])
n_q = sum(len(p["questions"]) for p in REPORT["polls"])
print(f"Wrote {out} — {n_polls} polls, {n_q} questions, {out.stat().st_size:,} bytes")
