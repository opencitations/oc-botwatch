import csv
import json
import logging
import os
import re
import sys
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

DATE_LEN = 10
BATCH_SIZE = 50_000

CSV_FILES = [
    ("oc-2026-01-hashed.csv/outputgennaiohash.csv", "2026-01"),
    ("oc-2026-02-hashed.csv/oc-2026-02.csv", "2026-02"),
    ("oc-2026-03-hashed.csv/oc-2026-03.csv", "2026-03"),
]

_classify: Callable[[str], str]


def _build_ai_regex() -> re.Pattern[str]:
    with (BASE_DIR / "ai-robots-txt" / "robots.json").open() as f:
        data = json.load(f)
    return re.compile("|".join(re.escape(name) for name in data), re.IGNORECASE)


def _build_generic_bot_regex() -> re.Pattern[str]:
    with (BASE_DIR / "crawler-user-agents" / "crawler-user-agents.json").open() as f:
        data = json.load(f)
    patterns: list[str] = []
    for entry in data:
        if "tags" in entry and "ai-crawler" in entry["tags"]:
            continue
        patterns.append(entry["pattern"])
    return re.compile("|".join(patterns), re.IGNORECASE)


def build_classifier() -> Callable[[str], str]:
    ai_re = _build_ai_regex()
    generic_re = _build_generic_bot_regex()

    def classify(ua: str) -> str:
        if ai_re.search(ua):
            return "ai_bot"
        if generic_re.search(ua):
            return "generic_bot"
        return "human"

    return classify


def _init_worker() -> None:
    global _classify  # noqa: PLW0603
    _classify = build_classifier()


def _process_batch(batch: list[tuple[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for day, ua in batch:
        if day not in counts:
            counts[day] = {"human": 0, "generic_bot": 0, "ai_bot": 0}
        counts[day][_classify(ua)] += 1
    return counts


def _merge(target: dict[str, dict[str, int]], partial: dict[str, dict[str, int]]) -> None:
    for day, cats in partial.items():
        if day not in target:
            target[day] = {"human": 0, "generic_bot": 0, "ai_bot": 0}
        for cat, n in cats.items():
            target[day][cat] += n


def _count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as f:
        for _ in f:
            n += 1
    return n - 1


def main() -> None:
    csv.field_size_limit(sys.maxsize)
    workers = os.cpu_count() or 4

    daily: dict[str, dict[str, int]] = {}

    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as pool:
        for filename, _ in CSV_FILES:
            filepath = BASE_DIR / filename
            total = _count_lines(filepath)
            futures: list[Future[dict[str, dict[str, int]]]] = []

            with filepath.open(encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader)
                col_date = header.index("date")
                col_ua = header.index("user_agent")

                batch: list[tuple[str, str]] = []
                for row in tqdm(reader, total=total, desc=filename, unit=" rows", unit_scale=True):
                    batch.append((row[col_date][:DATE_LEN], row[col_ua]))
                    if len(batch) >= BATCH_SIZE:
                        futures.append(pool.submit(_process_batch, batch))
                        batch = []

                if batch:
                    futures.append(pool.submit(_process_batch, batch))

            for fut in tqdm(futures, desc=f"{filename} [merge]", unit=" batch"):
                _merge(daily, fut.result())

    out_path = BASE_DIR / "daily_traffic.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "human", "generic_bot", "ai_bot"])
        for day in sorted(daily):
            if len(day) != DATE_LEN:
                continue
            d = daily[day]
            writer.writerow([day, d["human"], d["generic_bot"], d["ai_bot"]])

    logger.info("Output: %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
