"""Generic modular crawler for navigation discovery, category selection, and listing extraction.

Implements OpenSpec requirements:
1. Target URL Crawling and Navigation Category Selection
2. Listing Extraction from Category Page
"""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Callable
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from src.models import (
    CategoryNotFoundError,
    CrawlInput,
    CrawlOutput,
    ListingItem,
    NavLink,
    normalize_target_url,
)

try:
    from curl_cffi import requests as cffi_requests

    HAS_CURL_CFFI = True
except ImportError:
    cffi_requests = None
    HAS_CURL_CFFI = False

import requests as std_requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
}

NAV_CONTAINER_PATTERN = re.compile(
    r"(nav|menu|navbar|header|masthead|categor|cat-list|top-bar|pagetop|subnav|tabs|sidebar|topic|section-list)",
    re.IGNORECASE,
)

LISTING_CONTAINER_PATTERN = re.compile(
    r"(article|post|card|item|listing|entry|story|news|product|result|row|feed|grid|box|headline|title|content|main)",
    re.IGNORECASE,
)

BOILERPLATE_TEXT_PATTERN = re.compile(
    r"^(log\s*in|sign\s*in|sign\s*up|register|subscribe|privacy\s*policy|terms\s*of\s*(service|use)|"
    r"cookie\s*policy|contact\s*us|about\s*us|advertise|skip\s*to\s*content|read\s*more|more|next|prev|previous|"
    r"page\s*\d+|\d+|«|»|←|→)$",
    re.IGNORECASE,
)

IGNORED_SCHEMES = ("javascript:", "mailto:", "tel:", "data:", "whatsapp:", "viber:")


def fetch_html(url: str, timeout: int = 20) -> str:
    """Fetch HTML content from a target URL with browser TLS impersonation fallback."""
    normalized = normalize_target_url(url)
    last_error: Exception | None = None

    if HAS_CURL_CFFI and cffi_requests is not None:
        try:
            resp = cffi_requests.get(
                normalized,
                headers=DEFAULT_HEADERS,
                impersonate="chrome124",
                timeout=timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()
            if resp.encoding and resp.encoding.lower() != "iso-8859-1":
                return resp.text
            return resp.content.decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc

    try:
        resp = std_requests.get(
            normalized,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as exc:
        if last_error is not None:
            raise RuntimeError(f"Failed to fetch {normalized}: {exc} (fallback after: {last_error})") from exc
        raise RuntimeError(f"Failed to fetch {normalized}: {exc}") from exc


def _clean_url(href: str, base_url: str) -> str | None:
    """Resolve relative href against base_url and discard non-HTTP/anchor-only links."""
    raw = (href or "").strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.lower().startswith(IGNORED_SCHEMES):
        return None
    resolved = urljoin(base_url, raw)
    defragged, _ = urldefrag(resolved)
    parsed = urlparse(defragged)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return defragged


def _extract_anchor_label(anchor: Tag) -> str:
    """Extract clean human-readable label from an anchor tag."""
    text = " ".join(anchor.get_text(" ", strip=True).split())
    if not text:
        text = (anchor.get("title") or anchor.get("aria-label") or "").strip()
        text = " ".join(text.split())
    return text


def _extract_listing_title(anchor: Tag) -> str:
    """Extract the primary title from a listing anchor (handling card-wrapping anchors)."""
    heading = anchor.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading:
        h_text = " ".join(heading.get_text(" ", strip=True).split())
        if len(h_text) >= 3:
            return h_text

    title_el = anchor.find(
        attrs={"class": re.compile(r"(title|headline|name|heading)", re.IGNORECASE)}
    )
    if title_el:
        t_text = " ".join(title_el.get_text(" ", strip=True).split())
        if len(t_text) >= 3:
            return t_text

    # If the anchor itself is inside a heading, use the anchor text or parent heading text
    text = _extract_anchor_label(anchor)
    if text:
        return text

    parent_heading = anchor.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
    if parent_heading:
        return " ".join(parent_heading.get_text(" ", strip=True).split())

    return ""


def extract_nav_categories(html: str, base_url: str) -> list[NavLink]:
    """Discover navigation category links on a page using semantic and structural heuristics."""
    soup = BeautifulSoup(html, "html.parser")
    seen_urls: set[str] = set()
    seen_labels: set[str] = set()
    nav_links: list[NavLink] = []

    def add_candidate(anchor: Tag, allow_short: bool = True) -> None:
        href = anchor.get("href")
        if not isinstance(href, str):
            return
        url = _clean_url(href, base_url)
        if not url:
            return
        label = _extract_anchor_label(anchor)
        if not label:
            return
        # Navigation labels are typically concise (1 to 60 chars)
        if len(label) > 65 or (not allow_short and len(label) < 2):
            return
        if re.match(r"^(skip to|sign in|log in|login|register|subscribe)$", label, re.I):
            return
        label_key = label.casefold()
        if url in seen_urls or label_key in seen_labels:
            return
        seen_urls.add(url)
        seen_labels.add(label_key)
        nav_links.append(NavLink(label=label, url=url))

    # Tier 1: Semantic <nav>, [role="navigation"], <header>
    semantic_containers: list[Tag] = []
    semantic_containers.extend(soup.find_all("nav"))
    semantic_containers.extend(soup.find_all(attrs={"role": "navigation"}))
    semantic_containers.extend(soup.find_all("header"))

    # Tier 2: Elements with nav/menu/category class or id
    for tag in soup.find_all(["div", "ul", "ol", "aside", "section", "td", "table"]):
        if not isinstance(tag, Tag):
            continue
        classes = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class") or "")
        el_id = str(tag.get("id") or "")
        if NAV_CONTAINER_PATTERN.search(f"{classes} {el_id}"):
            semantic_containers.append(tag)

    for container in semantic_containers:
        for anchor in container.find_all("a", href=True):
            add_candidate(anchor)

    # Tier 3: Fallback if page has no semantic nav containers (or very few links)
    if len(nav_links) < 3:
        for anchor in soup.find_all("a", href=True):
            add_candidate(anchor, allow_short=False)

    return nav_links


def _url_slug_tokens(url: str) -> list[str]:
    """Extract lowercase path slug tokens from a URL for category matching."""
    parsed = urlparse(url)
    segments = [seg.strip().lower() for seg in parsed.path.split("/") if seg.strip()]
    tokens: list[str] = list(segments)
    for seg in segments:
        tokens.extend(re.split(r"[-_.]", seg))
    return [t for t in tokens if t]


def select_nav_category(
    nav_links: list[NavLink],
    nav_category: str,
    target_url: str | None = None,
) -> NavLink:
    """Identify and select the target navigation category from discovered nav links.

    Raises CategoryNotFoundError listing available categories if no match is found.
    """
    query = (nav_category or "").strip()
    if not query:
        raise ValueError("nav_category must be non-empty.")

    query_cf = query.casefold()
    query_slug = re.sub(r"[^a-z0-9\u0980-\u09ff]+", "-", query_cf).strip("-")

    # Support explicit root/all category keywords when target_url is provided
    if target_url and query_cf in ("all", "*", "root", "home", "index"):
        for link in nav_links:
            if link.label.casefold() in ("home", "all", "index"):
                return link
        return NavLink(label="All (Root Page)", url=normalize_target_url(target_url))

    if not nav_links:
        raise CategoryNotFoundError(query, [])

    # 1. Exact case-insensitive label match
    for link in nav_links:
        if link.label.casefold() == query_cf:
            return link

    # 2. Exact slug / path segment match in URL
    for link in nav_links:
        slug_tokens = _url_slug_tokens(link.url)
        if query_cf in slug_tokens or (query_slug and query_slug in slug_tokens):
            return link

    # 3. Substring match on label (e.g. "Tech" matches "Technology" or "Tech News")
    label_substring_matches: list[NavLink] = []
    for link in nav_links:
        label_cf = link.label.casefold()
        if query_cf in label_cf or label_cf in query_cf:
            label_substring_matches.append(link)
    if label_substring_matches:
        # Prefer shortest label difference
        label_substring_matches.sort(key=lambda l: abs(len(l.label) - len(query)))
        return label_substring_matches[0]

    # 4. Substring match on URL path
    for link in nav_links:
        path_cf = urlparse(link.url).path.casefold()
        if query_cf in path_cf or (query_slug and len(query_slug) >= 3 and query_slug in path_cf):
            return link

    # 5. Fuzzy match on label or URL slug
    best_link: NavLink | None = None
    best_score = 0.0
    for link in nav_links:
        label_score = SequenceMatcher(None, query_cf, link.label.casefold()).ratio()
        slug_scores = [
            SequenceMatcher(None, query_cf, token).ratio()
            for token in _url_slug_tokens(link.url)
        ]
        score = max([label_score, *slug_scores])
        if score > best_score:
            best_score = score
            best_link = link

    if best_link is not None and best_score >= 0.72:
        return best_link

    raise CategoryNotFoundError(query, nav_links)


def extract_listings(
    html: str,
    category_url: str,
    nav_urls: set[str] | None = None,
) -> list[ListingItem]:
    """Extract all listing (title, url) records from a category page."""
    soup = BeautifulSoup(html, "html.parser")
    nav_url_set = set(nav_urls or set())
    normalized_cat_url = _clean_url(category_url, category_url) or category_url

    # Remove non-visible tags
    for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    structured_items: list[ListingItem] = []
    fallback_items: list[ListingItem] = []
    seen_structured_urls: set[str] = set()
    seen_fallback_urls: set[str] = set()

    def is_valid_listing(title: str, url: str, is_structured: bool) -> bool:
        if not title or not url:
            return False
        if url == normalized_cat_url:
            return False
        if BOILERPLATE_TEXT_PATTERN.match(title):
            return False
        # Skip pure 1-2 char labels
        if len(title) < 3:
            return False
        # If it's a known top-level nav link and doesn't have a multi-word headline title, skip it
        if url in nav_url_set and len(title.split()) <= 2 and not is_structured:
            return False
        return True

    def is_in_listing_context(anchor: Tag) -> bool:
        # Check if anchor wraps a heading or is inside a heading
        if anchor.find(["h1", "h2", "h3", "h4", "h5", "h6"]) is not None:
            return True
        if anchor.find_parent(["h1", "h2", "h3", "h4", "h5", "h6", "article", "main"]) is not None:
            return True
        # Check if anchor or any close parent has listing-like class/id
        curr: Tag | None = anchor
        depth = 0
        while curr is not None and depth < 4:
            if isinstance(curr, Tag):
                # Skip links strictly inside <nav> or <footer> unless inside <main>/<article>
                if curr.name in ("nav", "footer") and anchor.find_parent(["main", "article"]) is None:
                    return False
                classes = (
                    " ".join(curr.get("class", []))
                    if isinstance(curr.get("class"), list)
                    else str(curr.get("class") or "")
                )
                el_id = str(curr.get("id") or "")
                if LISTING_CONTAINER_PATTERN.search(f"{classes} {el_id}"):
                    return True
            curr = curr.parent if isinstance(curr, Tag) else None
            depth += 1
        return False

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        url = _clean_url(href, category_url)
        if not url:
            continue

        title = _extract_listing_title(anchor)
        structured = is_in_listing_context(anchor)

        if structured and is_valid_listing(title, url, is_structured=True):
            # Exclude pure nav links unless they have descriptive listing titles (> 3 words)
            if url in nav_url_set and len(title.split()) <= 2:
                pass
            elif url not in seen_structured_urls:
                seen_structured_urls.add(url)
                structured_items.append(ListingItem(title=title, url=url))

        # Also collect into fallback_items if not inside <nav>/<footer>
        if anchor.find_parent(["nav", "footer"]) is None and is_valid_listing(
            title, url, is_structured=False
        ):
            if url not in seen_fallback_urls:
                seen_fallback_urls.add(url)
                fallback_items.append(ListingItem(title=title, url=url))

    if structured_items:
        # Merge any fallback items that weren't in nav_url_set if structured_items was very small (< 3)
        if len(structured_items) < 3 and len(fallback_items) > len(structured_items):
            for item in fallback_items:
                if item.url not in seen_structured_urls and item.url not in nav_url_set:
                    seen_structured_urls.add(item.url)
                    structured_items.append(item)
        return structured_items

    return fallback_items


def crawl_site(
    target_url: str,
    nav_category: str,
    fetcher: Callable[[str], str] = fetch_html,
) -> CrawlOutput:
    """Execute end-to-end crawl per OpenSpec generic-web-scraper behavior:
    1. Crawl starting from target_url
    2. Identify and select the target nav category
    3. Extract all listing titles and URLs from the target category page
    """
    crawl_input = CrawlInput(target_url=target_url, nav_category=nav_category)

    root_html = fetcher(crawl_input.target_url)
    nav_links = extract_nav_categories(root_html, crawl_input.target_url)
    selected_nav = select_nav_category(
        nav_links,
        crawl_input.nav_category,
        target_url=crawl_input.target_url,
    )

    # Avoid refetching if the selected category URL is identical to target_url
    cleaned_root = _clean_url(crawl_input.target_url, crawl_input.target_url) or crawl_input.target_url
    cleaned_cat = _clean_url(selected_nav.url, crawl_input.target_url) or selected_nav.url
    if cleaned_cat.rstrip("/") == cleaned_root.rstrip("/"):
        category_html = root_html
    else:
        category_html = fetcher(selected_nav.url)

    nav_url_set = {link.url for link in nav_links if link.url != selected_nav.url}
    listings = extract_listings(category_html, selected_nav.url, nav_urls=nav_url_set)

    return CrawlOutput(
        items=listings,
        target_url=crawl_input.target_url,
        nav_category=crawl_input.nav_category,
        matched_category=selected_nav.label,
        category_url=selected_nav.url,
        available_categories=nav_links,
    )
