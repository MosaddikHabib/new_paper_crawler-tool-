"""Comprehensive unit and integration tests for universal-crawler (generic-web-scraper)."""

from __future__ import annotations

import json
import pytest

import app as web_app
import cli
from src.crawler import (
    crawl_site,
    extract_listings,
    extract_nav_categories,
    select_nav_category,
)
from src.models import (
    CategoryNotFoundError,
    CrawlInput,
    ListingItem,
    NavLink,
    normalize_target_url,
    resolve_url,
)
from src.search import search_listings

SAMPLE_ROOT_HTML = """
<!DOCTYPE html>
<html>
<head><title>Portal Home</title></head>
<body>
  <header>
    <nav aria-label="Main Navigation">
      <a href="/">Home</a>
      <a href="/category/technology">Technology</a>
      <a href="/category/sports">Sports</a>
      <a href="/category/science-health">Science &amp; Health</a>
      <a href="javascript:void(0)">Ignore JS</a>
      <a href="#footer">Skip</a>
    </nav>
  </header>
  <main>
    <article class="story-card">
      <h2><a href="/post/root-featured">Featured Root Story</a></h2>
    </article>
  </main>
</body>
</html>
"""

SAMPLE_CATEGORY_HTML = """
<!DOCTYPE html>
<html>
<head><title>Technology News</title></head>
<body>
  <nav>
    <a href="/">Home</a>
    <a href="/category/technology">Technology</a>
    <a href="/category/sports">Sports</a>
  </nav>
  <main>
    <article class="post-card">
      <h2><a href="/articles/quantum-chip-2026">Breakthrough in Quantum Chip Architecture</a></h2>
      <p>Summary text...</p>
    </article>
    <article class="post-card">
      <a href="/articles/open-source-ai-agents" class="card-link">
        <span class="meta">Sep 30</span>
        <h3 class="headline">Open Source AI Agents Reach New Milestone</h3>
      </a>
    </article>
    <div class="listing-item">
      <a href="https://external.example.org/rust-kernel-guide">Rust in the Linux Kernel: 2026 Guide</a>
    </div>
    <div class="pagination">
      <a href="/category/technology?page=2">Next</a>
      <a href="/category/technology?page=2">2</a>
    </div>
  </main>
  <footer>
    <a href="/privacy">Privacy Policy</a>
    <a href="/login">Sign In</a>
  </footer>
</body>
</html>
"""


def fake_fetcher(url: str) -> str:
    if url.endswith("/category/technology"):
        return SAMPLE_CATEGORY_HTML
    return SAMPLE_ROOT_HTML


class TestModelsAndValidation:
    def test_normalize_target_url_adds_https_and_validates(self):
        assert normalize_target_url("example.com") == "https://example.com"
        assert normalize_target_url("https://news.ycombinator.com") == "https://news.ycombinator.com"
        with pytest.raises(ValueError):
            normalize_target_url("   ")

    def test_crawl_input_validation(self):
        inp = CrawlInput(target_url="example.com/news", nav_category="  Technology ")
        assert inp.target_url == "https://example.com/news"
        assert inp.nav_category == "Technology"
        with pytest.raises(ValueError):
            CrawlInput(target_url="https://example.com", nav_category="")

    def test_listing_item_normalization(self):
        item = ListingItem(title="  Hello   World \n ", url=" https://example.com/a ")
        assert item.to_dict() == {"title": "Hello World", "url": "https://example.com/a"}
        with pytest.raises(ValueError):
            ListingItem(title="   ", url="https://example.com")


class TestNavigationDiscoveryAndSelection:
    def test_extract_nav_categories_from_semantic_nav(self):
        nav_links = extract_nav_categories(SAMPLE_ROOT_HTML, "https://portal.example.com")
        labels = [n.label for n in nav_links]
        assert labels == ["Home", "Technology", "Sports", "Science & Health"]
        assert nav_links[1].url == "https://portal.example.com/category/technology"

    def test_select_nav_category_exact_and_fuzzy(self):
        nav_links = extract_nav_categories(SAMPLE_ROOT_HTML, "https://portal.example.com")
        # Case-insensitive exact match
        assert select_nav_category(nav_links, "technology").url.endswith("/category/technology")
        # Substring match
        assert select_nav_category(nav_links, "Science").label == "Science & Health"
        # Fuzzy match (typo)
        assert select_nav_category(nav_links, "Technolgy").label == "Technology"

    def test_select_nav_category_not_found_lists_available_categories(self):
        nav_links = extract_nav_categories(SAMPLE_ROOT_HTML, "https://portal.example.com")
        with pytest.raises(CategoryNotFoundError) as exc_info:
            select_nav_category(nav_links, "Finance & Crypto")
        err = exc_info.value
        assert "Finance & Crypto" in str(err)
        assert "Technology" in str(err)
        assert len(err.available_categories) == 4


class TestListingExtractionAndCrawlFlow:
    def test_extract_listings_resolves_urls_and_ignores_boilerplate(self):
        nav_urls = {
            "https://portal.example.com/",
            "https://portal.example.com/category/technology",
            "https://portal.example.com/category/sports",
        }
        items = extract_listings(
            SAMPLE_CATEGORY_HTML,
            "https://portal.example.com/category/technology",
            nav_urls=nav_urls,
        )
        assert len(items) == 3
        assert items[0].to_dict() == {
            "title": "Breakthrough in Quantum Chip Architecture",
            "url": "https://portal.example.com/articles/quantum-chip-2026",
        }
        assert items[1].to_dict() == {
            "title": "Open Source AI Agents Reach New Milestone",
            "url": "https://portal.example.com/articles/open-source-ai-agents",
        }
        assert items[2].to_dict() == {
            "title": "Rust in the Linux Kernel: 2026 Guide",
            "url": "https://external.example.org/rust-kernel-guide",
        }

    def test_crawl_site_end_to_end_spec_output(self):
        output = crawl_site(
            target_url="https://portal.example.com",
            nav_category="Technology",
            fetcher=fake_fetcher,
        )
        assert output.matched_category == "Technology"
        assert output.category_url == "https://portal.example.com/category/technology"
        spec_dict = output.to_spec_dict()
        assert "items" in spec_dict
        assert len(spec_dict["items"]) == 3
        assert spec_dict["items"][0]["title"] == "Breakthrough in Quantum Chip Architecture"


class TestGenericSearchFilter:
    def test_search_listings_by_title_url_and_multi_token(self):
        items = [
            ListingItem(title="Breakthrough in Quantum Chip Architecture", url="https://ex.com/quantum"),
            ListingItem(title="Open Source AI Agents Reach New Milestone", url="https://ex.com/ai-agents"),
            ListingItem(title="Rust in the Linux Kernel: 2026 Guide", url="https://ex.com/rust-kernel"),
        ]
        # Empty query returns all
        assert len(search_listings(items, "")) == 3
        # Keyword in title
        q_matches = search_listings(items, "quantum")
        assert len(q_matches) == 1
        assert q_matches[0].title == "Breakthrough in Quantum Chip Architecture"
        # Multi-token query
        multi_matches = search_listings(items, "rust 2026")
        assert len(multi_matches) == 1
        assert multi_matches[0].url == "https://ex.com/rust-kernel"
        # URL match
        url_matches = search_listings(items, "ai-agents")
        assert len(url_matches) == 1
        assert url_matches[0].title == "Open Source AI Agents Reach New Milestone"


class TestCLIAndWebAPI:
    def test_cli_json_crawl_and_search(self, monkeypatch, capsys):
        monkeypatch.setattr(
            cli,
            "crawl_site",
            lambda target_url, nav_category: crawl_site(target_url, nav_category, fetcher=fake_fetcher),
        )
        exit_code = cli.main(
            ["--url", "https://portal.example.com", "--category", "Technology", "--search", "Quantum", "--json"]
        )
        assert exit_code == 0
        captured = json.loads(capsys.readouterr().out)
        assert captured == {
            "items": [
                {
                    "title": "Breakthrough in Quantum Chip Architecture",
                    "url": "https://portal.example.com/articles/quantum-chip-2026",
                }
            ]
        }

    def test_flask_api_crawl_and_search(self, monkeypatch):
        monkeypatch.setattr(
            web_app,
            "crawl_site",
            lambda target_url, nav_category: crawl_site(target_url, nav_category, fetcher=fake_fetcher),
        )
        client = web_app.app.test_client()

        # 1. Index page renders
        res_home = client.get("/")
        assert res_home.status_code == 200
        assert b"Universal Crawler" in res_home.data

        # 2. Crawl endpoint returns extracted records + OpenSpec schema
        res_crawl = client.post(
            "/api/crawl",
            json={"target_url": "https://portal.example.com", "nav_category": "Technology"},
        )
        assert res_crawl.status_code == 200
        data = res_crawl.get_json()
        assert data["matched_category"] == "Technology"
        assert len(data["items"]) == 3
        assert len(data["spec_output"]["items"]) == 3

        # 3. Search endpoint filters cached crawl items
        res_search = client.post("/api/search", json={"query": "Rust"})
        assert res_search.status_code == 200
        s_data = res_search.get_json()
        assert s_data["total"] == 1
        assert s_data["items"][0]["title"] == "Rust in the Linux Kernel: 2026 Guide"

        # 4. Missing category returns 404 with available_categories
        res_missing = client.post(
            "/api/crawl",
            json={"target_url": "https://portal.example.com", "nav_category": "NonExistentCategory"},
        )
        assert res_missing.status_code == 404
        err_data = res_missing.get_json()
        assert len(err_data["available_categories"]) == 4

    def test_url_resolution_and_concatenated_sanitization(self, monkeypatch):
        # Concatenated default host + explicit URL is sanitized to explicit URL
        assert (
            normalize_target_url("https://news.ycombinator.comhttps://www.prothomalo.com/")
            == "https://www.prothomalo.com/"
        )
        # Markdown link syntax is unwrapped cleanly
        assert (
            normalize_target_url("[https://www.prothomalo.com/](https://www.prothomalo.com/)")
            == "https://www.prothomalo.com/"
        )
        # resolve_url uses urljoin for relative links and never prepends base_url to absolute URLs
        assert (
            resolve_url("https://news.ycombinator.com", "/bangladesh")
            == "https://news.ycombinator.com/bangladesh"
        )
        assert (
            resolve_url("https://news.ycombinator.com", "https://www.prothomalo.com/politics")
            == "https://www.prothomalo.com/politics"
        )
        assert (
            resolve_url(
                "https://news.ycombinator.com",
                "https://news.ycombinator.comhttps://www.prothomalo.com/",
            )
            == "https://www.prothomalo.com/"
        )

        # Verify POST /api/categories sanitizes target_url and does not prepend news.ycombinator.com
        fetched_urls: list[str] = []

        def spy_fetcher(url: str) -> str:
            fetched_urls.append(url)
            return SAMPLE_ROOT_HTML

        monkeypatch.setattr(web_app, "fetch_html", spy_fetcher)
        client = web_app.app.test_client()

        res_cat = client.post(
            "/api/categories",
            json={"target_url": "https://news.ycombinator.comhttps://www.prothomalo.com/"},
        )
        assert res_cat.status_code == 200
        cat_data = res_cat.get_json()
        assert cat_data["target_url"] == "https://www.prothomalo.com/"
        assert fetched_urls == ["https://www.prothomalo.com/"]
        assert cat_data["categories"][1]["url"] == "https://www.prothomalo.com/category/technology"

