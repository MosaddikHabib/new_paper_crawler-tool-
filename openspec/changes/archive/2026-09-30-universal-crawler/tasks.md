## 1. Core Scraper & Navigation Discovery

- [x] 1.1 Define input/output data schemas (`target_url`, `nav_category`, and `items: Array<{ title: string, url: string }>`)
- [x] 1.2 Implement crawler starting from `target_url` with navigation link extraction and `nav_category` matching
- [x] 1.3 Implement category page listing extractor returning normalized `{ title, url }` records

## 2. Search & Interfaces (CLI / UI)

- [x] 2.1 Implement generic search filter over extracted `{ title, url }` records
- [x] 2.2 Build CLI entrypoint to run crawls and search extracted listings
- [x] 2.3 Build interactive UI to configure `target_url` + `nav_category`, view extracted listings, and live-search results

## 3. Verification & Testing

- [x] 3.1 Add unit and integration tests for nav category selection, listing extraction, and search filtering
