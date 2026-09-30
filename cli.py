#!/usr/bin/env python3
"""CLI entrypoint for universal-crawler (generic-web-scraper).

Usage examples:
  # Discover navigation categories on a site
  python3 cli.py --url https://news.ycombinator.com --list-categories

  # Crawl a navigation category and output extracted (title, url) pairs
  python3 cli.py --url https://news.ycombinator.com --category "show"

  # Crawl and filter results with a search query, outputting strict OpenSpec JSON
  python3 cli.py --url https://news.ycombinator.com --category "new" --search "AI" --json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Sequence

from src.crawler import crawl_site, extract_nav_categories, fetch_html
from src.models import CategoryNotFoundError, ListingItem, normalize_target_url
from src.search import search_listings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universal-crawler",
        description="Configurable crawler to extract nav links and page listings from any target site.",
    )
    parser.add_argument(
        "-u",
        "--url",
        "--target-url",
        dest="target_url",
        required=True,
        help="Root target URL to crawl (e.g. https://news.ycombinator.com)",
    )
    parser.add_argument(
        "-c",
        "--category",
        "--nav-category",
        dest="nav_category",
        default="all",
        help="Target navigation category to select (default: 'all' or specify e.g. 'Sports', 'Tech', 'Show')",
    )
    parser.add_argument(
        "-s",
        "-q",
        "--search",
        "--query",
        dest="search_query",
        default="",
        help="Optional search query to filter extracted (title, url) records",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all discovered navigation categories on target_url and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output strict OpenSpec JSON schema: { 'items': [{ 'title', 'url' }] }",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="Optional file path to save results (.json or .csv)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Enter interactive search prompt after extracting records",
    )
    return parser


def _save_output(filepath: str, items: list[ListingItem]) -> None:
    if filepath.lower().endswith(".csv"):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url"])
            writer.writeheader()
            for item in items:
                writer.writerow(item.to_dict())
    else:
        payload = {"items": [item.to_dict() for item in items]}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


def _print_table(items: list[ListingItem], header: str | None = None) -> None:
    if header:
        print(header)
        print("-" * len(header))
    if not items:
        print("No matching items found.")
        return
    for idx, item in enumerate(items, start=1):
        print(f"{idx:3d}. {item.title}")
        print(f"     {item.url}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        target_url = normalize_target_url(args.target_url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.list_categories:
        try:
            html = fetch_html(target_url)
            categories = extract_nav_categories(html, target_url)
        except Exception as exc:
            print(f"Error fetching {target_url}: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(
                json.dumps(
                    {"categories": [c.to_dict() for c in categories]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"Discovered {len(categories)} navigation categories on {target_url}:")
            for idx, cat in enumerate(categories, start=1):
                print(f"  {idx:2d}. {cat.label} -> {cat.url}")
        return 0

    try:
        result = crawl_site(target_url=target_url, nav_category=args.nav_category)
    except CategoryNotFoundError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "error": str(exc),
                        "available_categories": [c.to_dict() for c in exc.available_categories],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error crawling {target_url}: {exc}", file=sys.stderr)
        return 1

    filtered_items = search_listings(result.items, args.search_query)

    if args.output_file:
        _save_output(args.output_file, filtered_items)

    if args.json:
        print(
            json.dumps(
                {"items": [item.to_dict() for item in filtered_items]},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        summary = (
            f"Target: {result.target_url} | Category: {result.matched_category} "
            f"({result.category_url}) | Extracted: {len(result.items)} | "
            f"Showing: {len(filtered_items)}"
        )
        _print_table(filtered_items, header=summary)

    if args.interactive and sys.stdin.isatty():
        print("\nInteractive Search Mode (type a query and press Enter, or 'q' to quit):")
        while True:
            try:
                q = input("search> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if q.lower() in ("q", "quit", "exit"):
                break
            matches = search_listings(result.items, q)
            _print_table(matches, header=f"Query: {q!r} ({len(matches)}/{len(result.items)} matches)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
