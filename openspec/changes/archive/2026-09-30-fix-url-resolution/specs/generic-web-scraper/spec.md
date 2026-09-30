## ADDED Requirements

### Requirement: URL Resolution and Payload Sanitization
The system SHALL resolve relative links using `urllib.parse.urljoin` and SHALL NOT prepend any default or fallback host when a link or `target_url` already starts with `http://` or `https://`. If a user input contains an accidentally concatenated prefix host (e.g. `https://news.ycombinator.comhttps://www.prothomalo.com/`), the system SHALL sanitize and extract the trailing explicit absolute URL (`https://www.prothomalo.com/`).

#### Scenario: Submitting an absolute URL to /api/categories
- **WHEN** a user submits `https://www.prothomalo.com/` (or an accidentally concatenated `https://news.ycombinator.comhttps://www.prothomalo.com/`) to `/api/categories` or `/api/crawl`
- **THEN** the system sanitizes the payload to `https://www.prothomalo.com/` without prepending `https://news.ycombinator.com` and fetches navigation categories cleanly

#### Scenario: Resolving relative and absolute links with urljoin
- **WHEN** the crawler resolves extracted navigation or listing links against a `base_url`
- **THEN** relative paths are joined via `urllib.parse.urljoin(base_url, link)` while links starting with `http://` or `https://` remain unchanged without any prepended host
