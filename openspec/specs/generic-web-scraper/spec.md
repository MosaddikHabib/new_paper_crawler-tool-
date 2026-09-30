# generic-web-scraper Specification

## Purpose
Configurable crawler to extract navigation links and page listings (`title` and `url`) from any target website and support generic CLI and UI search across extracted records.

## Requirements

### Requirement: Target URL Crawling and Navigation Category Selection
The system SHALL accept `target_url` (string) and `nav_category` (string) as inputs, crawl starting from `target_url`, and identify and select the matching navigation category link.

#### Scenario: Matching navigation category found on target site
- **WHEN** the user provides a valid `target_url` and `nav_category`
- **THEN** the crawler fetches `target_url`, locates the navigation link matching `nav_category` (case-insensitive / fuzzy match), and resolves the category page URL

#### Scenario: Navigation category not found
- **WHEN** `nav_category` does not match any navigation link on `target_url`
- **THEN** the crawler returns a descriptive error listing available navigation categories discovered on the page

### Requirement: Listing Extraction from Category Page
The system SHALL extract all listing titles and URLs from the selected category page and output them as an array of `{ title: string, url: string }` items.

#### Scenario: Extracting listings from a category page
- **WHEN** the crawler navigates to the selected `nav_category` page
- **THEN** it extracts all listing items with normalized non-empty `title` and absolute `url` fields into the `items` array

### Requirement: Generic CLI and UI Search Across Extracted Records
The system SHALL support filtering and searching across extracted `{ title, url }` records via both CLI arguments and an interactive UI search input.

#### Scenario: Searching extracted items by keyword
- **WHEN** a user enters a search query in the CLI or UI
- **THEN** the system returns all extracted items whose `title` or `url` matches the search query

### Requirement: URL Resolution and Payload Sanitization
The system SHALL resolve relative links using `urllib.parse.urljoin` and SHALL NOT prepend any default or fallback host when a link or `target_url` already starts with `http://` or `https://`. If a user input contains an accidentally concatenated prefix host (e.g. `https://news.ycombinator.comhttps://www.prothomalo.com/`), the system SHALL sanitize and extract the trailing explicit absolute URL (`https://www.prothomalo.com/`).

#### Scenario: Submitting an absolute URL to /api/categories
- **WHEN** a user submits `https://www.prothomalo.com/` (or an accidentally concatenated `https://news.ycombinator.comhttps://www.prothomalo.com/`) to `/api/categories` or `/api/crawl`
- **THEN** the system sanitizes the payload to `https://www.prothomalo.com/` without prepending `https://news.ycombinator.com` and fetches navigation categories cleanly

#### Scenario: Resolving relative and absolute links with urljoin
- **WHEN** the crawler resolves extracted navigation or listing links against a `base_url`
- **THEN** relative paths are joined via `urllib.parse.urljoin(base_url, link)` while links starting with `http://` or `https://` remain unchanged without any prepended host
