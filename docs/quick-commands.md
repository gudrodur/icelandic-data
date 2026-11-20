# Quick commands

Per-source commands for fetching and processing each dataset. Moved out of `AGENTS.md` verbatim to keep the always-loaded file small; `AGENTS.md` links here.

```bash
# Process raw data into tidy CSVs
uv run python scripts/sedlabanki.py

# Fetch CBI FX intervention (net purchases/sales, turnover, reserves, ISK/EUR) -> monthly CSV
uv run python scripts/sedlabanki_fx.py fetch
uv run python scripts/sedlabanki_fx.py list

# Currency exchange rates — Borgun card rates (current) + ECB reference rates (historical)
uv run python scripts/gengi.py USD,EUR --history 6m

# Query processed data
uv run python scripts/sql.py "SELECT * FROM 'data/processed/fuel_prices_daily.csv' LIMIT 10"

# Get company info and annual reports list
uv run python scripts/skatturinn.py info <kennitala>

# Download annual report PDF
uv run python scripts/skatturinn.py download <kennitala> --year 2024

# Extract financials from PDF (full pipeline)
uv run python scripts/financials.py company <kennitala> --year 2024

# Extract from local PDF
uv run python scripts/financials.py extract /path/to/report.pdf

# Eurostat — euro-area / EU statistics (wages, HICP, GDP, unemployment)
uv run python scripts/eurostat.py list
uv run python scripts/eurostat.py fetch prc_hicp_midx --filter geo=EA20 --filter coicop=CP00 --filter unit=I15
uv run python scripts/eurostat.py fetch namq_10_a10 --filter geo=EA20 --filter na_item=D1 --filter s_adj=SCA --filter unit=CP_MEUR --filter nace_r2=TOTAL
uv run python scripts/eurostat.py fetch namq_10_pe --filter geo=EA20 --filter na_item=EMP_DC --filter s_adj=SCA --filter unit=THS_PER

# Property price analysis
uv run python scripts/sql.py "SELECT YEAR(kaupsamningur_dags), median(kaupverd*1000/einflm_m2) FROM 'data/processed/kaupskra_geocoded.parquet' WHERE NOT onothaefur AND tegund='Fjölbýli' GROUP BY 1 ORDER BY 1"

# Geocode an Icelandic address
uv run python -c "from iceaddr import iceaddr_lookup; print(iceaddr_lookup('Laugavegur', number=22, postcode=101))"

# List Nasdaq Iceland companies
uv run python scripts/nasdaq.py companies

# Search company announcements (handles Icelandic encoding)
uv run python scripts/nasdaq.py search --company "Arion banki hf." --category "Ársreikningur"

# Process Gasvaktin fuel prices
uv run python scripts/fuel.py

# Energy Authority — electricity generation by source (1969–2024)
uv run python scripts/energy.py list
uv run python scripts/energy.py fetch

# Hafrannsóknastofnun / MFRI — current cod stock assessment
uv run python scripts/hafogvatn.py list
uv run python scripts/hafogvatn.py fetch --stock cod --year 2026

# Fiskistofa — public current fishing closures (open WFS; not paid catch/quota REST)
uv run python scripts/fiskistofa.py list
uv run python scripts/fiskistofa.py fetch

# Environment Agency GIS — contaminated land registry (open WFS)
uv run python scripts/ust_gis.py list
uv run python scripts/ust_gis.py fetch

# Air quality — UST PM10/PM2.5/NO2/H2S bulk CSVs + Open-Meteo wind, daily aggregates for Grensásvegur
uv run python scripts/loftgaedi.py

# Veðurstofa — stations, latest AWS observations, earthquakes (api.vedur.is JSON, no auth)
uv run python scripts/vedur.py list
uv run python scripts/vedur.py fetch                              # all three datasets
uv run python scripts/vedur.py fetch --dataset quakes --days 7 --min-magnitude 1
uv run python scripts/vedur.py fetch --dataset observations --aggregation hour

# EEA geospatial catalogue (sdi.eea.europa.eu, GeoNetwork 4.4)
uv run python scripts/eea_sdi.py search "grassland" --iceland --size 10
uv run python scripts/eea_sdi.py record   35a036bb-c027-401c-8625-2ecf722e8461
uv run python scripts/eea_sdi.py links    35a036bb-c027-401c-8625-2ecf722e8461
uv run python scripts/eea_sdi.py xml      35a036bb-c027-401c-8625-2ecf722e8461 -o data/raw/eea_sdi/grassland_2015.xml

# Hagstofan: any PX table — browse with breadcrumbs (last_updated, note counts, next command), read notes, fetch
uv run python scripts/hagstofan_query.py list Ibuar/buferlaflutningar/buferlaflmillilanda
uv run python scripts/hagstofan_query.py notes Ibuar/buferlaflutningar/buferlaflmillilanda/MAN01400.px
uv run python scripts/hagstofan_query.py fetch Ibuar/buferlaflutningar/buferlaflmillilanda/MAN01400.px --filters '{"Kyn":["0"]}' --since 2015 --out out.json

# Hagstofan: CPI sub-components (headline + 12 COICOP groups + imported/domestic/services)
# Chain-links VIS01304/01102 archive onto VIS01300/01101 current across the June 2024 break
uv run python scripts/hagstofan_cpi.py

# Hagstofan: population by citizenship (quarterly + annual by country), wages by private sector, immigrant labor share
uv run python scripts/hagstofan_population_wages.py

# Hagstofan: wage index (LAU04000) + labor/total income deciles (TEK01006/07) + PAYE by background (TEK02012)
# Tidy long format with CPI-deflated real values
uv run python scripts/hagstofan_income.py

# Hagstofan: bike & e-bike imports by tariff code (ebikes/escooters/bikes) -> data/processed/bike_imports_all.csv
uv run python scripts/hagstofan.py

# Hagstofan income distribution — TEK01001 by source/age/gender (mean+median) + tax burden CSVs
uv run python scripts/income_distribution.py

# Take-home salary calculator (payday.is) — monthly gross -> take-home, tax + pension breakdown
uv run python scripts/laun.py 1000000

# HMS: house-price (kaupvísitala) vs rental-price (leiguvísitala) indices, rebased to 2023-05=100
# The visitala page is Vercel-guarded, but the CSVs fetch straight from object storage.
uv run python scripts/hms_indices.py fetch     # -> data/raw/hms/indices/{kaup,leigu}visitala.csv
uv run python scripts/hms_indices.py           # -> data/processed/hms_rent_vs_price_index.csv

# HMS kaupskrá: fetch the 48 MB property-transaction CSV, convert Latin-1 -> UTF-8, report freshness
uv run python scripts/kaupskra_fetch.py        # -> data/raw/hms/kaupskra_utf8.csv
uv run python scripts/kaupskra_fetch.py report

# HMS mánaðarskýrsla: newest monthly report's workbook + page text (headless Chromium for discovery)
uv run python scripts/hms_manadarskyrsla.py           # -> data/processed/hms_manadarskyrsla/{YYYY-MM}/{sheet}.csv
uv run python scripts/hms_manadarskyrsla.py list

# HMS húsnæðisáætlanir (annual housing plans): completions vs need, waitlists, plots
uv run python scripts/hms_housing_plans.py            # parse the newest local workbook
uv run python scripts/hms_housing_plans.py --year 2026
uv run python scripts/hms_housing_plans.py list

# Housing completions 1970–2025 — Hagstofan IDN03001 + HMS húsnæðisáætlanir -> data/processed/iceland_housing_completions.csv
uv run python scripts/housing_completions.py

# Download LMI geodata layers (~50 MB)
uv run python scripts/lmi.py download

# Generate Iceland maps
uv run python scripts/kortagerð.py static -o reports/iceland-map.png
uv run python scripts/kortagerð.py html -o reports/iceland-map.html
uv run python scripts/kortagerð.py static --bounds capital --highlight "Reykjavíkurborg" -o reports/rvk.png

# Iceland grassland map (Copernicus HRL via LMI, 20 m raster) — uses Tier 3 cache
uv run python scripts/lmi_hrl.py fetch grassland       # one-time, ~860 MB
uv run python scripts/build_cache.py rasters           # one-time, → 9 MB ISN93 GeoTIFF
uv run python scripts/grassland_map.py                 # ≈3 s warm

# GRAVPI heatmap (Copernicus EEA discomap WMS — no LMI Iceland clip exists)
uv run python scripts/grassland_probability_heatmap.py

# Directorate of Health — list all dashboards, scrape one (Playwright)
uv run python scripts/landlaeknir.py list
uv run python scripts/landlaeknir.py fetch --slug mortis

# Vinnumálastofnun — Excel + Power BI capture
uv run python scripts/vinnumalastofnun.py fetch

# Farsæld barna — child wellbeing Power BI capture
uv run python scripts/farsaeld_barna.py fetch

# Vernd — asylum / international-protection dashboard
uv run python scripts/vernd.py info
uv run python scripts/vernd.py fetch

# Byggðastofnun — regional-development dashboard catalog (Tableau Public)
uv run python scripts/byggdastofnun.py list
uv run python scripts/byggdastofnun.py url tekjur

# Tekjusagan — income history 1991–2024 (open JSON API; disposable income, assets/debt, gender×education)
uv run python scripts/tekjusagan.py list
uv run python scripts/tekjusagan.py fetch                       # -> data/processed/tekjusagan_{series}.csv
uv run python scripts/tekjusagan.py fetch --series radstofun --set "Tekjubil=Tekjubil 1"

# Skoðanakannanir — RÚV + Vísir opinion-poll aggregators (national + Reykjavík, all pollsters)
uv run python scripts/skodanakannanir.py list
uv run python scripts/skodanakannanir.py list --source visir --since 2025 --scope reykjavik
uv run python scripts/skodanakannanir.py list --source all --since 2025
uv run python scripts/skodanakannanir.py fetch 479261
uv run python scripts/skodanakannanir.py fetch visir-20262904348    # Vísir works too, no browser needed

# Skoðanakannanir --topic esb — same pipeline, EU-membership support/oppose (ahead of the 2026-08-29 þjóðaratkvæðagreiðsla)
uv run python scripts/skodanakannanir.py list --source visir --since 2025 --topic esb
uv run python scripts/skodanakannanir.py fetch visir-20262915377 --topic esb   # or omit --topic: auto-detected per article

# Ferðamálastofa — Keflavík tourism Power BI
uv run python scripts/ferdamalastofa.py --help

# Velsældarvísar + Félagsvísar + Menningarvísar — Hagstofa indicator catalog
uv run python scripts/velsaeldarvisar.py fetch
uv run python scripts/velsaeldarvisar.py list --section velsaeldarvisar
uv run python scripts/velsaeldarvisar.py pxtables

# Heimsmarkmið — UN SDG national statistics (open-sdg)
uv run python scripts/heimsmarkmid.py fetch
uv run python scripts/heimsmarkmid.py list --goal 4
uv run python scripts/heimsmarkmid.py get 1-1-1

# Ríkisreikningur — state accounts ACTUALS (Fjársýsla)
uv run python scripts/rikisreikningur.py summary
uv run python scripts/rikisreikningur.py malefni
uv run python scripts/rikisreikningur.py files

# Opnir reikningar — state paid invoices by org/vendor (2017–present)
uv run python scripts/opnirreikningar.py search-org "Veðurstofa"
uv run python scripts/opnirreikningar.py fetch --org-text "14412 - Veðurstofa Íslands" --from 2024-01-01 --to 2024-12-31
uv run python scripts/opnirreikningar.py top-vendors --org 14412 --year 2024

# Public procurement — TED API + OCDS bulk data (3,494+ tenders), award tracking, CPV search
uv run python scripts/tenders.py download-ocds
uv run python scripts/tenders.py search --cpv 90600000 --date-from 20240101
uv run python scripts/tenders.py awards --buyer "Reykjavíkurborg"

# Reykjavík útboðsvefur (In-Tend) — all tender notices since 2017 -> data/processed/utbod_reykjavik_projects.csv
uv run python scripts/utbod_reykjavik.py fetch
uv run python scripts/utbod_reykjavik.py list
uv run python scripts/utbod_reykjavik.py search 'ræsting'

# Reykjavík winter/street tender results 2018–2024 (reykjavik.is scrape) -> data/processed/reykjavik_winter_tenders.csv
uv run python scripts/reykjavik_tenders.py

# Reykjavík env-ops wages vs other-costs ratio (outsourcing proxy) -> data/processed/reykjavik_env_ops_ratio.csv
uv run python scripts/reykjavik_winter.py

# Ríkissjóður balance 1980-2025 — Hagstofan THJ05211 (pre-2015; the Fjársýsla API only goes back to 2015)
uv run python scripts/hagstofan_rikissjod.py list     # sibling tables + coverage
uv run python scripts/hagstofan_rikissjod.py fetch    # → data/processed/rikissjod_balance.csv

# Alþingi — parliamentary XML: MPs, per-MP vote records, bills, committees, speeches
# --thing defaults to the sitting parliament (resolved at runtime, never hardcoded)
uv run python scripts/althingi.py list                        # all parliaments
uv run python scripts/althingi.py list --datasets
uv run python scripts/althingi.py fetch --dataset members     # roster + party + constituency
uv run python scripts/althingi.py fetch --dataset votes --thing 156   # events + per-MP ballots
uv run python scripts/althingi.py fetch --dataset all --thing 150-156

# Fjárlög — state budget APPROPRIATIONS + 5-yr plan (málaflokkur level)
uv run python scripts/fjarlog.py fetch                 # → data/processed/fjarlog.parquet
uv run python scripts/fjarlog.py products              # afurð × year coverage
uv run python scripts/fjarlog.py mala 04.30            # defense across actual/enacted/bill

# CO2.is — climate action plan
uv run python scripts/co2.py fetch
uv run python scripts/co2.py list --kerfi S
uv run python scripts/co2.py list --status "Í framkvæmd"

# HMS Landeignaskrá — download shapefile, build landsnr → lon/lat CSV
uv run python scripts/landeignaskra.py download    # 25 MB Azure blob
uv run python scripts/landeignaskra.py extract
uv run python scripts/landeignaskra.py build       # data/processed/landeignaskra.csv
uv run python scripts/landeignaskra.py lookup 0174540

# Reykjavík planning activity (Planitor) — building/planning cases by type & stage -> data/processed/planitor_reykjavik_planning.csv
uv run python scripts/skipulagsmal.py

# Seðlabanki interest rates — Power BI scrape via gagnabanki.is
uv run python scripts/sedlabanki_rates.py

# Lánamál ríkisins — government bond yields (RIKB/RIKS, no auth, UTF-16 JSON)
uv run python scripts/lanamal.py list                # live orderbook catalog from /markadsyfirlit
uv run python scripts/lanamal.py fetch              # daily fixings -> data/processed/lanamal.csv
uv run python scripts/lanamal.py fetch --orderbook RIKB_31_0124

# Samgöngustofa bifreiðatölur — vehicle registrations via reverse-engineered Power BI API
# (geo-fenced: run from an Icelandic IP). list shows both reports + all dimensions.
uv run python scripts/samgongustofa.py list
uv run python scripts/samgongustofa.py fetch --report onroad --dimension fuel        # current fleet EV split
uv run python scripts/samgongustofa.py fetch --dimension make --years 2020-2026      # imports by brand/year
uv run python scripts/samgongustofa.py fetch --dimension fuel --years 2025,2026 --monthly

# island.is vehicle lookup by plate or VIN (public GraphQL API)
uv run python scripts/car.py AB123

# Traffic counters (Vegagerðin) — list, snapshot, accumulate, render
uv run python scripts/umferd.py stations
uv run python scripts/umferd.py snapshot
uv run python scripts/umferd.py collect
uv run python scripts/umferd.py report
uv run python scripts/umferd_map.py    # Iceland-wide traffic map (depends on LMI cache from PR 1)

# Mælaborð landbúnaðarins — cattle-subsidy recipients (Playwright scrape of "Eftir búi" matrix)
uv run python scripts/maelabord_nautgripa.py fetch

# Render cattle-subsidy farms on an Iceland map (depends on PR 1 LMI cache + PR 4 landeignaskra)
uv run python scripts/nautgripa_map.py

# Map-construction caching (Tier 3+4; ISN93-reprojected raster + Iceland constants)
uv run python scripts/build_cache.py all                 # build all derived caches
uv run python scripts/build_cache.py status              # what is cached / stale / missing
uv run python scripts/build_cache.py rasters --only grassland_isn93

# Benchmark map-construction speed (cold|warm-raw|warm), JSON history
uv run python scripts/bench_maps.py run --mode warm
uv run python scripts/bench_maps.py history

# Cache + render integration tests
uv run pytest tests/test_cache_consistency.py tests/test_maps_render.py -v
```

