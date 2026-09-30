"""Generic search filter over extracted { title, url } listing records.

Implements OpenSpec Requirement:
- Generic CLI and UI Search Across Extracted Records
"""

from __future__ import annotations

from typing import Iterable

from src.models import ListingItem


def _coerce_item(item: ListingItem | dict[str, str]) -> ListingItem:
    if isinstance(item, ListingItem):
        return item
    if isinstance(item, dict) and "title" in item and "url" in item:
        return ListingItem(title=str(item["title"]), url=str(item["url"]))
    raise TypeError(f"Expected ListingItem or {{'title', 'url'}} dict, got {type(item).__name__}")


def search_listings(
    items: Iterable[ListingItem | dict[str, str]],
    query: str,
) -> list[ListingItem]:
    """Filter and rank extracted listing items matching `query` across `title` or `url`.

    - Empty or whitespace-only `query` returns all items unchanged.
    - Multi-word queries match when all query tokens appear in `title` or `url` (case-insensitive).
    - Results where the full query appears in `title` are ranked before URL-only matches.
    """
    normalized_items = [_coerce_item(i) for i in items]
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return normalized_items

    query_cf = cleaned_query.casefold()
    tokens = [tok for tok in query_cf.split() if tok]

    scored_matches: list[tuple[int, int, ListingItem]] = []
    for idx, item in enumerate(normalized_items):
        title_cf = item.title.casefold()
        url_cf = item.url.casefold()
        combined = f"{title_cf} {url_cf}"

        if query_cf in title_cf:
            # Highest relevance: exact substring in title
            score = 0 if title_cf.startswith(query_cf) else 1
            scored_matches.append((score, idx, item))
        elif query_cf in url_cf:
            # Exact substring in URL
            scored_matches.append((2, idx, item))
        elif len(tokens) > 1 and all(tok in combined for tok in tokens):
            # All tokens present across title/url
            all_in_title = all(tok in title_cf for tok in tokens)
            scored_matches.append((3 if all_in_title else 4, idx, item))

    scored_matches.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in scored_matches]
