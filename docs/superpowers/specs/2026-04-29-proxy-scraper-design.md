# Proxy Scraper Design

## Overview

Automatically scrape fresh proxies from multiple free sources before each validation cycle.

## Architecture

```
proxy_scraper.py (new)          validate_proxies.py (existing)
        ↓                                    ↓
proxyscrape_raw.txt ──────────────────────▶ working.txt
        ↓
run_daily.py calls scraper first, then validator
```

## Sources (in order)

1. **ProxyScrape** - `https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all`
2. **Free Proxy List** - `https://free-proxy-list.net/` (HTML parse)
3. **GeoNode** - `https://geonode.com/free-proxy-list/api/` (JSON API)

## Behavior

- Try each source in order until at least one returns proxies
- If a source fails, log warning and continue to next
- Deduplicate across all sources
- Append to `proxyscrape_raw.txt` (don't overwrite - preserve existing)
- Report count per source and total found

## Output

`proxyscrape_raw.txt` - one `host:port` per line, deduplicated

## CLI

```bash
python proxy_scraper.py                    # scrape all sources
python proxy_scraper.py --source 1       # scrape only ProxyScrape
python proxy_scraper.py --source 2       # scrape only Free Proxy List
python proxy_scraper.py --source 3       # scrape only GeoNode
```

## Integration

`run_daily.py` calls `scrape_proxies()` before `validate_proxies()`:

```python
def scrape_and_validate_proxies():
    scraped = scrape_proxies()  # new
    if not scraped:
        # try existing proxyscrape_raw.txt anyway
        pass
    proxies = validate_proxies()
    return proxies
```
