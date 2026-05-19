# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import json
import logging
import re
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

_SKIP_LLM_NAMES: frozenset[str] = frozenset({"Spider", "Code"})

_SUPPLEMENTARY_BOT_FILE = BASE_DIR / "supplementary_bots.txt"

_SPARQL_HOST = "sparql.opencitations.net"
_SPARQL_PATH_RE = r"/sparql(/|$|\?)"
_SPARQL_QUERY_RE = r"\?query="
_API_VERSIONED_PATH_RE = r"^/(index(/api)?|meta(/api)?)/v\d+/.+"
_REDIRECT_CODES: frozenset[str] = frozenset({"301", "302", "303", "307", "308"})


def _build_llm_pattern() -> str:
    with (BASE_DIR / "ai-robots-txt" / "robots.json").open() as f:
        data: dict[str, object] = json.load(f)
    parts: list[str] = []
    for name in data:
        if name in _SKIP_LLM_NAMES:
            continue
        parts.append(rf"\b{re.escape(name)}\b")
    return "(?i)" + "|".join(parts)


def _build_generic_bot_pattern() -> str:
    with (BASE_DIR / "crawler-user-agents" / "crawler-user-agents.json").open() as f:
        crawlers = json.load(f)
    with (BASE_DIR / "COUNTER-Robots" / "COUNTER_Robots_list.json").open() as f:
        counter = json.load(f)
    patterns: list[str] = []
    for entry in crawlers:
        if "tags" in entry and "ai-crawler" in entry["tags"]:
            continue
        patterns.append(entry["pattern"])
    patterns.extend(entry["pattern"] for entry in counter)
    patterns.extend(line for line in _SUPPLEMENTARY_BOT_FILE.read_text().splitlines() if line.strip())
    return "(?i)" + "|".join(patterns)


def _classify_service(host: pl.Expr, path: pl.Expr, method: pl.Expr) -> pl.Expr:
    return (
        pl.when(path.str.contains(_SPARQL_PATH_RE))
        .then(pl.lit("sparql"))
        .when(
            (host == _SPARQL_HOST)
            & (path.str.contains(_SPARQL_QUERY_RE) | (method == "POST"))
        )
        .then(pl.lit("sparql"))
        .when(path.str.contains(_API_VERSIONED_PATH_RE))
        .then(pl.lit("api"))
        .otherwise(pl.lit("web"))
    )


def classify_traffic(input_dir: Path = INPUT_DIR) -> pl.DataFrame:
    llm_pat = _build_llm_pattern()
    generic_pat = _build_generic_bot_pattern()

    frames = [
        pl.scan_csv(
            f,
            schema_overrides={
                "user_agent": pl.Utf8,
                "date": pl.Utf8,
                "request_host": pl.Utf8,
                "request_path": pl.Utf8,
                "request_method": pl.Utf8,
                "http_response_code": pl.Utf8,
            },
        ).select("date", "user_agent", "request_host", "request_path", "request_method", "http_response_code")
        for f in sorted(input_dir.glob("*.csv"))
    ]

    return (
        pl.concat(frames)
        .with_columns(pl.col("date").str.slice(0, 10).alias("date"))
        .filter(pl.col("date").str.contains(r"^\d{4}-\d{2}-\d{2}$"))
        .filter(~pl.col("http_response_code").is_in(_REDIRECT_CODES))
        .with_columns(
            pl.when(pl.col("user_agent").str.contains(llm_pat))
            .then(pl.lit("llm_bot"))
            .when(pl.col("user_agent").str.contains(generic_pat))
            .then(pl.lit("generic_bot"))
            .otherwise(pl.lit("human"))
            .alias("category"),
            _classify_service(pl.col("request_host"), pl.col("request_path"), pl.col("request_method")).alias("service"),
        )
        .group_by("date", "category", "service")
        .len()
        .rename({"len": "count"})
        .collect(engine="streaming")
        .sort("date", "service", "category")
        .select("date", "category", "service", "count")
    )


def _wide_from_long(long_df: pl.DataFrame) -> pl.DataFrame:
    return (
        long_df.group_by("date", "category")
        .agg(pl.col("count").sum())
        .pivot(on="category", index="date", values="count")
        .fill_null(0)
        .sort("date")
        .select("date", "human", "generic_bot", "llm_bot")
    )


def main(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> None:
    logging.basicConfig(level=logging.INFO)
    long_df = classify_traffic(input_dir)
    long_path = output_dir / "daily_traffic_by_service.csv"
    long_df.write_csv(long_path)
    logger.info("Output: %s", long_path)

    wide_df = _wide_from_long(long_df)
    wide_path = output_dir / "daily_traffic.csv"
    wide_df.write_csv(wide_path)
    logger.info("Output: %s", wide_path)


if __name__ == "__main__":
    main()  # pragma: no cover
