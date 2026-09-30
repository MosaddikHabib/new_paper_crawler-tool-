"""Flask web server and REST API for Universal Crawler (generic-web-scraper)."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from src.crawler import crawl_site, extract_nav_categories, fetch_html
from src.models import CategoryNotFoundError, normalize_target_url
from src.search import search_listings

app = Flask(__name__)

# Keep most recent crawl output in memory for instant server-side search queries
_last_crawl_items: list[dict[str, str]] = []


@app.route("/")
def index():
    """Render the interactive Universal Crawler & Search UI."""
    return render_template("index.html")


@app.route("/api/categories", methods=["POST"])
def api_discover_categories():
    """Discover navigation categories on a given target_url."""
    payload = request.get_json(silent=True) or {}
    raw_url = str(payload.get("target_url") or "").strip()
    try:
        target_url = normalize_target_url(raw_url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        html = fetch_html(target_url)
        categories = extract_nav_categories(html, target_url)
        return jsonify(
            {
                "target_url": target_url,
                "categories": [c.to_dict() for c in categories],
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    """Crawl target_url, select nav_category, and extract { title, url } listings."""
    global _last_crawl_items
    payload = request.get_json(silent=True) or {}
    target_url = str(payload.get("target_url") or "").strip()
    nav_category = str(payload.get("nav_category") or "").strip()
    search_query = str(payload.get("search_query") or "").strip()

    try:
        result = crawl_site(target_url=target_url, nav_category=nav_category)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except CategoryNotFoundError as exc:
        return (
            jsonify(
                {
                    "error": str(exc),
                    "nav_category": exc.nav_category,
                    "available_categories": [c.to_dict() for c in exc.available_categories],
                }
            ),
            404,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    _last_crawl_items = [item.to_dict() for item in result.items]
    filtered = search_listings(result.items, search_query)

    response_data = result.to_full_dict()
    response_data["items"] = [item.to_dict() for item in filtered]
    response_data["spec_output"] = {"items": [item.to_dict() for item in filtered]}
    return jsonify(response_data)


@app.route("/api/search", methods=["POST"])
def api_search():
    """Filter provided or cached { title, url } records using the generic search engine."""
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query") or "").strip()
    raw_items = payload.get("items")
    source_items = raw_items if isinstance(raw_items, list) else _last_crawl_items
    try:
        matched = search_listings(source_items, query)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "query": query,
            "total": len(matched),
            "items": [item.to_dict() for item in matched],
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
