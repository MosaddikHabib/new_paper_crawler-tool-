## 1. Backend URL Resolution & Sanitization

- [x] 1.1 Refactor `normalize_target_url` and add `resolve_url` in `src/models.py` using `urllib.parse.urljoin`, guarding against prepending hosts to absolute URLs and sanitizing concatenated URLs
- [x] 1.2 Update `src/crawler.py` and `app.py` (`/api/categories` and `/api/crawl`) to use sanitized URL resolution

## 2. Frontend Payload Sanitization

- [x] 2.1 Remove pre-filled default URL values in `templates/index.html` and sanitize user URL inputs in `static/app.js` before POSTing to `/api/categories` and `/api/crawl`

## 3. Verification

- [x] 3.1 Add regression tests in `tests/test_crawler.py` and verify live category discovery for `https://www.prothomalo.com/`
