## Why

Need a configurable, generic web scraper (`generic-web-scraper`) capable of crawling any target website starting from a `target_url`, discovering and navigating into a specified `nav_category`, extracting structured listing items (`title` and `url`), and allowing users to search across the extracted records via CLI or web UI.

## What Changes

- Introduce a configurable crawler engine accepting `target_url` (string) and `nav_category` (string).
- Implement navigation link discovery and category matching to locate and follow the target category page.
- Extract page listing records into structured `{ title: string, url: string }` items.
- Provide a generic CLI and interactive UI search interface over the extracted listing records.

## Capabilities

### New Capabilities
- `generic-web-scraper`: Configurable crawler to extract navigation links and page listings from any target site, with CLI and UI search across extracted records.

### Modified Capabilities
<!-- None -->

## Impact

- New crawler and parser module for navigation discovery and listing extraction.
- New CLI and web UI search interface over extracted `{ title, url }` items.
