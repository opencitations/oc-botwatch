# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import logging
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import polars as pl
from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

_SERVICES: tuple[str, ...] = ("web", "api", "sparql")
_CATEGORY_LABELS: tuple[str, ...] = ("Human", "Generic bot", "LLM bot")
_CATEGORY_COLUMNS: tuple[str, ...] = ("human", "generic_bot", "llm_bot")


def _prepare(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("date").str.to_date("%Y-%m-%d", strict=False)).drop_nulls("date").sort("date")


def _fmt_axis(x: float, _pos: int) -> str:
    return f"{x / 1e6:.0f}M" if x >= 1e6 else f"{x / 1e3:.0f}K"  # noqa: PLR2004


def _setup_xaxis(ax: Axes) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def _pivot_by_service(long_df: pl.DataFrame, service: str) -> pl.DataFrame:
    pivoted = (
        long_df.filter(pl.col("service") == service)
        .pivot(on="category", index="date", values="count")
        .fill_null(0)
    )
    for cat in _CATEGORY_COLUMNS:
        if cat not in pivoted.columns:
            pivoted = pivoted.with_columns(pl.lit(0).alias(cat))
    return _prepare(pivoted.select("date", *_CATEGORY_COLUMNS))


def plot_daily_traffic(df: pl.DataFrame, output: Path) -> None:
    df = _prepare(df)
    dates = df["date"].to_list()
    human = df["human"].to_list()
    generic_bot = df["generic_bot"].to_list()
    llm_bot = df["llm_bot"].to_list()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(dates, human, generic_bot, llm_bot, labels=list(_CATEGORY_LABELS), alpha=0.8)
    ax.legend(loc="upper left")
    ax.set_ylabel("Requests")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_axis))
    _setup_xaxis(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    logger.info("Output: %s", output)


def plot_daily_traffic_pct(df: pl.DataFrame, output: Path) -> None:
    df = _prepare(df)
    total = df["human"] + df["generic_bot"] + df["llm_bot"]
    human_pct = (df["human"] / total * 100).to_list()
    generic_pct = (df["generic_bot"] / total * 100).to_list()
    llm_pct = (df["llm_bot"] / total * 100).to_list()
    dates = df["date"].to_list()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(dates, human_pct, generic_pct, llm_pct, labels=list(_CATEGORY_LABELS), alpha=0.8)
    ax.legend(loc="upper left")
    ax.set_ylabel("Share of daily requests (%)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    _setup_xaxis(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    logger.info("Output: %s", output)


def plot_daily_traffic_by_service(long_df: pl.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(len(_SERVICES), 1, figsize=(12, 12), sharex=True)
    for ax, service in zip(axes, _SERVICES, strict=True):
        sub = _pivot_by_service(long_df, service)
        dates = sub["date"].to_list()
        layers = [sub[c].to_list() for c in _CATEGORY_COLUMNS]
        ax.stackplot(dates, *layers, labels=list(_CATEGORY_LABELS), alpha=0.8)
        ax.legend(loc="upper left")
        ax.set_title(service)
        ax.set_ylabel("Requests")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_axis))
    _setup_xaxis(axes[-1])
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    logger.info("Output: %s", output)


def plot_daily_traffic_by_service_pct(long_df: pl.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(len(_SERVICES), 1, figsize=(12, 12), sharex=True)
    for ax, service in zip(axes, _SERVICES, strict=True):
        sub = _pivot_by_service(long_df, service)
        total = sub["human"] + sub["generic_bot"] + sub["llm_bot"]
        layers = [(sub[c] / total * 100).fill_nan(0).to_list() for c in _CATEGORY_COLUMNS]
        dates = sub["date"].to_list()
        ax.stackplot(dates, *layers, labels=list(_CATEGORY_LABELS), alpha=0.8)
        ax.legend(loc="upper left")
        ax.set_title(service)
        ax.set_ylabel("Share (%)")
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    _setup_xaxis(axes[-1])
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    logger.info("Output: %s", output)


def main(output_dir: Path = OUTPUT_DIR) -> None:
    logging.basicConfig(level=logging.INFO)
    df = pl.read_csv(output_dir / "daily_traffic.csv")
    plot_daily_traffic(df, output_dir / "daily_traffic.png")
    plot_daily_traffic_pct(df, output_dir / "daily_traffic_pct.png")

    long_df = pl.read_csv(output_dir / "daily_traffic_by_service.csv")
    plot_daily_traffic_by_service(long_df, output_dir / "daily_traffic_by_service.png")
    plot_daily_traffic_by_service_pct(long_df, output_dir / "daily_traffic_by_service_pct.png")


if __name__ == "__main__":
    main()  # pragma: no cover
