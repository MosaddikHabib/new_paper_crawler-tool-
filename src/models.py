"""Data schemas for universal-crawler (generic-web-scraper).

Follows OpenSpec specification in openspec/changes/universal-crawler/:
- inputs: target_url (string), nav_category (string)
- outputs: items: Array<{ title: string, url: string }>
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse


def normalize_target_url(url: str) -> str:
    """Validate and normalize a root target URL."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("target_url must be a non-empty string.")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid target_url: {url!r}")
    return cleaned


@dataclass(frozen=True)
class CrawlInput:
    """Input configuration for the universal crawler."""

    target_url: str
    nav_category: str

    def __post_init__(self) -> None:
        normalized_url = normalize_target_url(self.target_url)
        cleaned_category = (self.nav_category or "").strip()
        if not cleaned_category:
            raise ValueError("nav_category must be a non-empty string.")
        object.__setattr__(self, "target_url", normalized_url)
        object.__setattr__(self, "nav_category", cleaned_category)


@dataclass(frozen=True)
class NavLink:
    """A discovered navigation category link on the target website."""

    label: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "url": self.url}


@dataclass(frozen=True)
class ListingItem:
    """A single extracted page listing record ({ title, url })."""

    title: str
    url: str

    def __post_init__(self) -> None:
        cleaned_title = " ".join((self.title or "").split()).strip()
        cleaned_url = (self.url or "").strip()
        if not cleaned_title:
            raise ValueError("ListingItem.title must be non-empty.")
        if not cleaned_url:
            raise ValueError("ListingItem.url must be non-empty.")
        object.__setattr__(self, "title", cleaned_title)
        object.__setattr__(self, "url", cleaned_url)

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url}


@dataclass
class CrawlOutput:
    """Structured output conforming to OpenSpec generic-web-scraper schema."""

    items: list[ListingItem] = field(default_factory=list)
    target_url: str = ""
    nav_category: str = ""
    matched_category: str = ""
    category_url: str = ""
    available_categories: list[NavLink] = field(default_factory=list)

    def to_spec_dict(self) -> dict[str, Any]:
        """Return strict OpenSpec output schema: { 'items': [{ 'title': ..., 'url': ... }] }."""
        return {
            "items": [item.to_dict() for item in self.items],
        }

    def to_full_dict(self) -> dict[str, Any]:
        """Return enriched payload for UI/API diagnostics alongside spec items."""
        return {
            "target_url": self.target_url,
            "nav_category": self.nav_category,
            "matched_category": self.matched_category,
            "category_url": self.category_url,
            "available_categories": [nav.to_dict() for nav in self.available_categories],
            "total_items": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }


class CategoryNotFoundError(LookupError):
    """Raised when nav_category does not match any navigation link on target_url."""

    def __init__(self, nav_category: str, available_categories: list[NavLink]) -> None:
        self.nav_category = nav_category
        self.available_categories = available_categories
        available_labels = [c.label for c in available_categories]
        preview = ", ".join(available_labels[:20]) if available_labels else "none discovered"
        super().__init__(
            f"Navigation category {nav_category!r} not found. "
            f"Available categories ({len(available_labels)}): {preview}"
        )
