import json
import logging
import re
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATE_LEN = 10

INPUT_DIR = BASE_DIR / "input"


def _build_ai_pattern() -> str:
    with (BASE_DIR / "ai-robots-txt" / "robots.json").open() as f:
        data = json.load(f)
    return "(?i)" + "|".join(re.escape(name) for name in data)


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
    return "(?i)" + "|".join(patterns)


def classify_traffic() -> pl.DataFrame:
    ai_pat = _build_ai_pattern()
    generic_pat = _build_generic_bot_pattern()

    frames = [
        pl.scan_csv(f, schema_overrides={"user_agent": pl.Utf8, "date": pl.Utf8}).select(
            "date", "user_agent",
        )
        for f in sorted(INPUT_DIR.glob("*.csv"))
    ]

    daily = (
        pl.concat(frames)
        .with_columns(pl.col("date").str.slice(0, DATE_LEN).alias("date"))
        .filter(pl.col("date").str.len_chars() == DATE_LEN)
        .with_columns(
            pl.when(pl.col("user_agent").str.contains(ai_pat))
            .then(pl.lit("ai_bot"))
            .when(pl.col("user_agent").str.contains(generic_pat))
            .then(pl.lit("generic_bot"))
            .otherwise(pl.lit("human"))
            .alias("category"),
        )
        .group_by("date", "category")
        .len()
        .collect(engine="streaming")
    )

    return (
        daily.pivot(on="category", index="date", values="len")
        .fill_null(0)
        .sort("date")
        .select("date", "human", "generic_bot", "ai_bot")
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    result = classify_traffic()
    out_path = BASE_DIR / "output" / "daily_traffic.csv"
    result.write_csv(out_path)
    logger.info("Output: %s", out_path)


if __name__ == "__main__":
    main()
