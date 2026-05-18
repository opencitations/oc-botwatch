# oc-botwatch

Classifies traffic from [OpenCitations](https://opencitations.net) server access logs into three categories: human visitors, generic bots (search engine crawlers and the like), and AI bots (LLM training crawlers, AI assistants, etc.).

It reads monthly CSV dumps, classifies each request by its user-agent string, and outputs a single `daily_traffic.csv` with per-day counts for each category.

## Access log format

The input CSV files are monthly exports of OpenCitations HTTP access logs. IP addresses are SHA-1 hashed for privacy. Each file has the following columns:

| Column | Example |
|---|---|
| `hashed_ip` | `5aaa3bbdc584a2931a9cc04bac2d2125cb2511e5` |
| `continent_name` | `Europe` |
| `country_iso_code` | `ES` |
| `country_name` | `Spain` |
| `request_method` | `GET` |
| `request_host` | `opencitations.net` |
| `request_path` | `/index/api/v2/citation-count/doi:` |
| `http_response_code` | `301` |
| `user_agent` | `python-requests/2.32.5` |
| `token` | `null` |
| `date` | `2026-01-01T00:01:15Z` |
| `referer` | `None` |

## How classification works

User-agent strings are matched against two open databases (included as git submodules):

- [ai.robots.txt](https://github.com/ai-robots-txt/ai.robots.txt)
- [crawler-user-agents](https://github.com/monperrus/crawler-user-agents)

A request is labeled `ai_bot` if its user-agent matches any entry in ai.robots.txt. Otherwise, if it matches crawler-user-agents (excluding entries already tagged as `ai-crawler`), it's labeled `generic_bot`. Everything else is `human`.

### Why these two sources

Because they have already been adopted in the literature. In particular, [Liu et al. (2025)](https://doi.org/10.1145/3730567.3732913) uses Dark Visitors, the upstream data source of ai.robots.txt, as its primary reference for compiling AI user agents, and relies on crawler-user-agents as a supplementary corpus of general-purpose bot signatures when testing the coverage of Cloudflare's bot-blocking feature.

## Limitations

User-agent string matching only detects bots that openly identify themselves. In practice, this means that the bot counts produced here are a lower bound on actual bot traffic, and the human counts are an upper bound. The classification remains useful for tracking relative trends over time, since the same lists applied consistently yield comparable proportions across periods.

## References

Liu, E., Luo, E., Shan, S., Voelker, G. M., Zhao, B. Y., & Savage, S. (2025). Somesite I Used To Crawl: Awareness, Agency and Efficacy in Protecting Content Creators From AI Crawlers. In *Proceedings of the 2025 ACM Internet Measurement Conference (IMC '25)*, 78–99. https://doi.org/10.1145/3730567.3732913

## Running

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python analyze_traffic.py
```

Processing is parallelized internally by Polars.

Output goes to `daily_traffic.csv` in the project root.

## Output format

```csv
date,human,generic_bot,ai_bot
2026-01-01,150432,28901,4210
2026-01-02,148877,27650,4455
...
```
