## Context

When `#target-url-input` had a pre-filled `value="https://news.ycombinator.com"` in `templates/index.html`, pasting `https://www.prothomalo.com/` into the field produced `https://news.ycombinator.comhttps://www.prothomalo.com/`. In addition, `normalize_target_url` did not strip concatenated prefix URLs or markdown link formatting, causing `POST /api/categories` to request the malformed concatenated URL.

## Goals / Non-Goals

**Goals:**
- Ensure `urllib.parse.urljoin` is used for all base + relative URL resolution.
- Never prepend a fallback/default host if a URL already starts with `http://` or `https://`.
- Automatically sanitize concatenated URLs (e.g. `https://news.ycombinator.comhttps://www.prothomalo.com/` -> `https://www.prothomalo.com/`) in both `static/app.js` and `src/models.py`.
- Remove pre-filled `value` attributes from `#target-url-input` and `#nav-category-input` in `templates/index.html` (keeping `placeholder` hints only).

**Non-Goals:**
- Changing the OpenSpec `{ items: [{ title, url }] }` output contract.

## Decisions

- **Centralized `resolve_url` and `normalize_target_url`**: Place strict sanitization and `urllib.parse.urljoin` handling in `src/models.py` and use it across `app.py` and `src/crawler.py`.
- **Frontend Input Sanitization**: Add `sanitizeTargetUrl()` in `static/app.js` to extract the explicit target URL before sending `POST /api/categories` or `POST /api/crawl`.

## Risks / Trade-offs

- If a URL legitimately embeds another URL inside a query string parameter (e.g. `?redirect=https://...`), only split concatenated `https?://` occurrences that appear in the netloc/path before any query string `?`.
