# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import csv
from pathlib import Path

import polars as pl

from oc_botwatch import classify, visualize

GPTBOT_UA = "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"
CLAUDEBOT_UA = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ClaudeBot/1.0"
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
NODE_UA = "node"
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

EXPECTED_DAILY_TRAFFIC = [
    {"date": "2026-01-15", "human": 7, "generic_bot": 3, "llm_bot": 1},
    {"date": "2026-01-16", "human": 1, "generic_bot": 1, "llm_bot": 0},
]

EXPECTED_BY_SERVICE = [
    {"date": "2026-01-15", "category": "human", "service": "api", "count": 1},
    {"date": "2026-01-15", "category": "generic_bot", "service": "sparql", "count": 1},
    {"date": "2026-01-15", "category": "llm_bot", "service": "sparql", "count": 1},
    {"date": "2026-01-15", "category": "generic_bot", "service": "web", "count": 2},
    {"date": "2026-01-15", "category": "human", "service": "web", "count": 6},
    {"date": "2026-01-16", "category": "generic_bot", "service": "api", "count": 1},
    {"date": "2026-01-16", "category": "human", "service": "web", "count": 1},
]


def _write_csv(path: Path, rows: list[tuple[str, str, str, str, str, int]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "user_agent", "request_host", "request_path", "request_method", "http_response_code"])
        writer.writerows(rows)


def _write_input_csvs(input_dir: Path) -> None:
    input_dir.mkdir(parents=True)
    _write_csv(
        input_dir / "2026-01-a.csv",
        [
            ("2026-01-15T08:00:00", GPTBOT_UA, "sparql.opencitations.net", "/meta?query=SELECT", "GET", 200),
            ("2026-01-15T09:00:00", CLAUDEBOT_UA, "opencitations.net", "/sparql?query=SELECT", "GET", 301),
            ("2026-01-15T10:00:00", GOOGLEBOT_UA, "opencitations.net", "/index/sparql", "GET", 301),
            ("2026-01-15T11:00:00", CHROME_UA, "api.opencitations.net", "/index/v2/citations/doi:1", "GET", 200),
            ("2026-01-15T12:00:00", CHROME_UA, "opencitations.net", "/index/api/v1/citations/doi:2", "GET", 301),
            ("2026-01-15T13:00:00", NODE_UA, "opencitations.net", "/meta/v1/metadata/doi:3", "GET", 301),
            ("2026-01-15T14:00:00", NODE_UA, "opencitations.net", "/index/coci/api/v1/citations/doi:4", "GET", 308),
            ("2026-01-15T15:00:00", NODE_UA, "opencitations.net", "/meta/api/", "GET", 200),
            ("2026-01-15T16:00:00", CHROME_UA, "opencitations.net", "/about", "GET", 200),
            ("2026-01-15T17:00:00", CHROME_UA, "ldd.opencitations.net", "/meta/br/123", "GET", 200),
            ("2026-01-15T18:00:00", CHROME_UA, "search.opencitations.net", "/", "GET", 200),
            ("2026-01-15T19:00:00", CHROME_UA, "www.sparontologies.net", "/", "GET", 200),
            ("not-a-date", CHROME_UA, "opencitations.net", "/", "GET", 200),
            ("2026-01-15T20:00:00", GOOGLEBOT_UA, "sparql.opencitations.net", "/meta", "POST", 200),
            ("2026-01-15T21:00:00", CHROME_UA, "sparql.opencitations.net", "/robots.txt", "GET", 200),
            ("2026-01-15T22:00:00", GOOGLEBOT_UA, "api.opencitations.net", "/robots.txt", "GET", 404),
            ("2026-01-15T23:00:00", CHROME_UA, "api.opencitations.net", "/index/v1", "GET", 200),
        ],
    )
    _write_csv(
        input_dir / "2026-01-b.csv",
        [
            ("2026-01-16T11:00:00", NODE_UA, "api.opencitations.net", "/index/v2/citations/doi:5", "GET", 200),
            ("2026-01-16T12:00:00", CHROME_UA, "opencitations.net", "/", "GET", 200),
        ],
    )


def test_classify_main_end_to_end(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    _write_input_csvs(input_dir)
    output_dir.mkdir()

    classify.main(input_dir=input_dir, output_dir=output_dir)

    daily_csv = output_dir / "daily_traffic.csv"
    by_service_csv = output_dir / "daily_traffic_by_service.csv"
    assert daily_csv.exists()
    assert by_service_csv.exists()
    assert pl.read_csv(daily_csv).to_dicts() == EXPECTED_DAILY_TRAFFIC
    assert pl.read_csv(by_service_csv).to_dicts() == EXPECTED_BY_SERVICE


def test_visualize_main_generates_pngs(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "daily_traffic.csv").write_text(
        "date,human,generic_bot,llm_bot\n"
        "2026-01-15,205984,1978755,33985\n"
        "2026-01-16,156806,1476709,49966\n"
        "2026-01-17,350000,2500000,75000\n",
    )
    (output_dir / "daily_traffic_by_service.csv").write_text(
        "date,category,service,count\n"
        "2026-01-15,human,web,50000\n"
        "2026-01-15,generic_bot,web,80000\n"
        "2026-01-15,llm_bot,web,5000\n"
        "2026-01-15,human,api,150000\n"
        "2026-01-15,generic_bot,api,1800000\n"
        "2026-01-15,llm_bot,api,28000\n"
        "2026-01-15,human,sparql,5984\n"
        "2026-01-15,generic_bot,sparql,98755\n"
        "2026-01-15,llm_bot,sparql,985\n"
        "2026-01-16,human,web,40000\n"
        "2026-01-16,generic_bot,web,70000\n"
        "2026-01-16,llm_bot,web,8000\n"
        "2026-01-16,human,api,110000\n"
        "2026-01-16,generic_bot,api,1400000\n"
        "2026-01-16,llm_bot,api,40000\n"
        "2026-01-16,human,sparql,6806\n"
        "2026-01-16,generic_bot,sparql,6709\n"
        "2026-01-16,llm_bot,sparql,1966\n"
        "2026-01-17,human,web,90000\n"
        "2026-01-17,generic_bot,web,120000\n"
        "2026-01-17,llm_bot,web,10000\n"
        "2026-01-17,human,api,250000\n"
        "2026-01-17,generic_bot,api,2370000\n"
        "2026-01-17,llm_bot,api,64000\n"
        "2026-01-17,human,sparql,10000\n"
        "2026-01-17,generic_bot,sparql,10000\n"
        "2026-01-17,llm_bot,sparql,1000\n",
    )

    visualize.main(output_dir=output_dir)

    assert (output_dir / "daily_traffic.png").exists()
    assert (output_dir / "daily_traffic_pct.png").exists()
    assert (output_dir / "daily_traffic_by_service.png").exists()
    assert (output_dir / "daily_traffic_by_service_pct.png").exists()
