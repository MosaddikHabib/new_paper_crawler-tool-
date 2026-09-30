# Universal Crawler (`generic-web-scraper`)

A configurable, modular web scraper built with **OpenSpec** (Spec-Driven Development) and **gstack**. It accepts any `target_url` and `nav_category`, discovers navigation categories, extracts normalized `{ title, url }` listings from the selected category page, and provides both an interactive **Web UI** and a **CLI** to search and export results.

---

## 📁 Project Structure

```text
Crawler_checker_30_sep_2026/
├── app.py                     # Flask web server & REST API (/api/categories, /api/crawl, /api/search)
├── cli.py                     # Command-line interface for crawling, category discovery, and search
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
├── src/
│   ├── models.py              # Input/output schemas (CrawlInput, NavLink, ListingItem, CrawlOutput)
│   ├── crawler.py             # Navigation discovery, category matcher, and listing extractor
│   └── search.py              # Generic keyword & multi-token search filter over { title, url } items
├── templates/
│   └── index.html             # Interactive Web UI template
├── static/
│   ├── styles.css             # Dark-mode glassmorphic stylesheet
│   └── app.js                 # Frontend crawl, category pill selector, live search, and CSV/JSON export
├── tests/
│   └── test_crawler.py        # Unit and integration test suite (11 tests)
└── openspec/
    ├── specs/
    │   └── generic-web-scraper/spec.md   # Canonical OpenSpec specification
    └── changes/archive/                  # Archived OpenSpec changes
```

---

## ⚙️ 1. Environment Setup

A virtual environment (`.venv`) is already configured in the project root. If setting up from scratch:

```bash
# 1. Create virtual environment (if not already created)
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Tip:** You can also run commands directly without activating the shell environment by prefixing with `.venv/bin/python3` or `.venv/bin/pytest`.

---

## 🌐 2. Running & Operating the Web UI

### Start the Server
```bash
.venv/bin/python3 app.py
```
Then open **[http://127.0.0.1:5050](http://127.0.0.1:5050)** in your browser.

### How to Operate the Web UI
1. **Quick Presets (Optional)**:
   - Click any preset chip in the top-right header (**Hacker News (show)**, **Books to Scrape (Mystery)**, or **BD Pratidin (জাতীয়)**) to immediately populate and crawl a live site.
2. **Discover Navigation Categories**:
   - Enter any website URL in **Target Root URL (`target_url`)** (e.g., `https://books.toscrape.com` or `https://news.ycombinator.com`).
   - Click **Discover Nav**.
   - A drawer of clickable **Navigation Category Pills** discovered on that site will appear. Click any pill to automatically select that category and extract its listings.
3. **Crawl & Extract Listings**:
   - Type a category name in **Navigation Category (`nav_category`)** (exact, partial, or fuzzy match—or `all` to extract from the root page itself) and click **Crawl & Extract Listings**.
   - If a category name does not match, the UI displays an error banner and automatically lists all available navigation categories from the target site as clickable pills.
4. **Live Search & Filter**:
   - Type any keyword or multi-word phrase into the **Filter extracted titles or URLs...** search box.
   - Results filter instantaneously with highlighted matches across both `title` and `url`, updating the match counter (`matched / total`).
5. **View & Export**:
   - Toggle between **Listings View** (interactive cards) and **OpenSpec JSON** (`{ "items": [{ "title": "...", "url": "..." }] }`).
   - Click **Copy JSON** to copy the filtered OpenSpec JSON payload to your clipboard, or **Export CSV** to download `extracted_listings.csv`.

---

## 💻 3. Running & Operating the CLI

The CLI (`cli.py`) supports category discovery, crawling, filtering, file export, and an interactive search prompt.

### A. Discover Available Navigation Categories on a Website
```bash
.venv/bin/python3 cli.py --url https://books.toscrape.com --list-categories
```
*(Add `--json` to get JSON output of discovered categories.)*

### B. Crawl a Target URL & Navigation Category
```bash
.venv/bin/python3 cli.py --url https://books.toscrape.com --category "Mystery"
```

### C. Crawl + Filter by Search Query
```bash
.venv/bin/python3 cli.py --url https://books.toscrape.com --category "Mystery" --search "Sharp"
```

### D. Output Strict OpenSpec JSON (`{ "items": [{ "title", "url" }] }`)
```bash
.venv/bin/python3 cli.py --url https://news.ycombinator.com --category "show" --search "AI" --json
```

### E. Save Extracted Records to `.json` or `.csv`
```bash
# Save as JSON
.venv/bin/python3 cli.py --url https://books.toscrape.com --category "Mystery" --output mystery.json

# Save as CSV
.venv/bin/python3 cli.py --url https://books.toscrape.com --category "Mystery" --output mystery.csv
```

### F. Interactive Search Mode (`-i` / `--interactive`)
Crawl once and query the extracted dataset repeatedly in an interactive terminal prompt:
```bash
.venv/bin/python3 cli.py --url https://books.toscrape.com --category "Mystery" --interactive
```
Type any search term at the `search>` prompt, or `q` to quit.

---

## 🔌 4. REST API Endpoints

When `app.py` is running on `http://127.0.0.1:5050`, you can also query the endpoints programmatically:

1. **`POST /api/categories`** — Discover navigation links on a root URL:
   ```bash
   curl -s -X POST http://127.0.0.1:5050/api/categories \
     -H "Content-Type: application/json" \
     -d '{"target_url": "https://news.ycombinator.com"}'
   ```
2. **`POST /api/crawl`** — Crawl a category and extract `{ title, url }` items:
   ```bash
   curl -s -X POST http://127.0.0.1:5050/api/crawl \
     -H "Content-Type: application/json" \
     -d '{"target_url": "https://books.toscrape.com", "nav_category": "Mystery", "search_query": "Sharp"}'
   ```
3. **`POST /api/search`** — Filter extracted records by query:
   ```bash
   curl -s -X POST http://127.0.0.1:5050/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Sharp"}'
   ```

---

## 🧪 5. Running Tests & OpenSpec Validation

### Run the Pytest Suite
```bash
.venv/bin/pytest tests/ -v
```

### OpenSpec Commands
```bash
# List active specs
openspec list --specs

# Validate all specs and changes
openspec validate --all

# Propose a new feature change
openspec new change <feature-name>
```
