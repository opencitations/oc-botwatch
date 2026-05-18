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

## Running

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python analyze_traffic.py
```

Processing uses all available CPU cores.

Output goes to `daily_traffic.csv` in the project root.

## Output format

```csv
date,human,generic_bot,ai_bot
2026-01-01,150432,28901,4210
2026-01-02,148877,27650,4455
...
```
