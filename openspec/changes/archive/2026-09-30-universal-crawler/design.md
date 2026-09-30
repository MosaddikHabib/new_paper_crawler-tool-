## Context

Different websites structure their navigation menus and category listing pages differently. `universal-crawler` (`generic-web-scraper`) provides a unified, configurable scraper that starts at `target_url`, selects a target `nav_category`, extracts `{ title, url }` listings, and exposes search via CLI and UI.

## Goals / Non-Goals

**Goals:**
- Crawl starting from any `target_url` and discover navigation links automatically.
- Match and follow `nav_category` to the target listing page.
- Extract clean `{ title: string, url: string }` items using resilient DOM heuristics.
- Support fast keyword/fuzzy search across extracted items in both CLI and web UI.

**Non-Goals:**
- Bypassing CAPTCHAs or authenticated paywalls.
- Site-specific hardcoded scrapers.

## Decisions

- **Heuristic Nav Discovery**: Inspect semantic navigation containers (`<nav>`, `<header>`, `[role="navigation"]`, menu lists) first, falling back to top-level anchor links when matching `nav_category`.
- **Listing Extraction Heuristics**: Identify repeated card/article/list patterns (`<article>`, `<li>`, `<h2>/<h3>` anchors, grid cards) and resolve relative `href` attributes against the category page URL using `urllib.parse.urljoin` / `new URL()`.
- **Dual Interface (CLI + Web UI)**: Expose a clean JSON/structured core output (`items: [{ title, url }]`) consumable by both CLI search commands and a web dashboard.

## Risks / Trade-offs

- **Client-side rendered SPAs**: Static HTTP fetching may miss dynamically rendered listings; fallback to headless browser rendering (Playwright/crawl4ai) can be used when static DOM has insufficient links.
