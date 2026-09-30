## Why

`POST /api/categories` and `POST /api/crawl` can receive malformed concatenated URLs such as `https://news.ycombinator.comhttps://www.prothomalo.com/` when a default base URL is pre-populated or concatenated with an explicit absolute URL. URL normalization and frontend payload construction must sanitize target inputs and resolve links strictly via `urllib.parse.urljoin` without prepending any default host when an input already starts with `http://` or `https://`.

## What Changes

- Refactor URL normalization and link resolution in `src/models.py`, `src/crawler.py`, and `app.py` to use `urllib.parse.urljoin` and guard against prepending any default host or retaining concatenated prefix URLs when the target or link already starts with `http://` or `https://`.
- Update `templates/index.html` and `static/app.js` to remove hardcoded default input `value` attributes that cause accidental URL concatenation and sanitize user inputs before sending requests to `/api/categories` and `/api/crawl`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `generic-web-scraper`: Add strict URL resolution and payload sanitization requirements so absolute URLs are never prefixed with a fallback/default host.

## Impact

- `src/models.py` (`normalize_target_url`, `resolve_url`)
- `src/crawler.py` (`_clean_url`, `extract_nav_categories`, `extract_listings`)
- `app.py` (`/api/categories`, `/api/crawl`)
- `static/app.js` and `templates/index.html`
- `tests/test_crawler.py`
