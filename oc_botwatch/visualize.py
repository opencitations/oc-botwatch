import logging
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import polars as pl
from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def _prepare(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("date").str.to_date("%Y-%m-%d", strict=False)).drop_nulls("date").sort("date")


def _fmt_axis(x: float, _pos: int) -> str:
    return f"{x / 1e6:.0f}M" if x >= 1e6 else f"{x / 1e3:.0f}K"  # noqa: PLR2004


def _setup_xaxis(ax: Axes) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def plot_daily_traffic(df: pl.DataFrame, output: Path) -> None:
    df = _prepare(df)
    dates = df["date"].to_list()
    human = df["human"].to_list()
    generic_bot = df["generic_bot"].to_list()
    llm_bot = df["llm_bot"].to_list()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(dates, human, generic_bot, llm_bot, labels=["Human", "Generic bot", "LLM bot"], alpha=0.8)
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
    ax.stackplot(dates, human_pct, generic_pct, llm_pct, labels=["Human", "Generic bot", "LLM bot"], alpha=0.8)
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    df = pl.read_csv(BASE_DIR / "output" / "daily_traffic.csv")
    out = BASE_DIR / "output"
    plot_daily_traffic(df, out / "daily_traffic.png")
    plot_daily_traffic_pct(df, out / "daily_traffic_pct.png")


if __name__ == "__main__":
    main()
