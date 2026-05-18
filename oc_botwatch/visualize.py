import logging
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import polars as pl

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


def plot_daily_traffic(df: pl.DataFrame, output: Path) -> None:
    df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d", strict=False)).drop_nulls("date").sort("date")

    dates = df["date"].to_list()
    human = df["human"].to_list()
    generic_bot = df["generic_bot"].to_list()
    ai_bot = df["ai_bot"].to_list()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(dates, human, generic_bot, ai_bot, labels=["Human", "Generic bot", "AI bot"], alpha=0.8)
    ax.legend(loc="upper left")
    ax.set_ylabel("Requests")
    def _fmt_axis(x: float, _pos: int) -> str:
        return f"{x / 1e6:.0f}M" if x >= 1e6 else f"{x / 1e3:.0f}K"  # noqa: PLR2004

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_axis))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    logger.info("Output: %s", output)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    df = pl.read_csv(BASE_DIR / "output" / "daily_traffic.csv")
    plot_daily_traffic(df, BASE_DIR / "output" / "daily_traffic.png")


if __name__ == "__main__":
    main()
