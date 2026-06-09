"""
browser_search.py — Backend search module for Thing AI Browser Mode.
Provides web search results for All / Images / Videos tabs.
Uses DuckDuckGo (free, no key) with optional Google CSE upgrade.
"""

import os
import re
import json
import requests
import traceback
from urllib.parse import quote_plus, urlparse
from dotenv import load_dotenv

load_dotenv(override=True)

# Optional Google Custom Search Engine keys (free tier: 100 queries/day)
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "AIzaSyDBgeEOSjS7_GAH1x88xDP9ctuFLvceuJI")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX", "c42dbfe89250e4023")


def _extract_favicon(url):
    """Get favicon URL for a domain."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.hostname or ""
        if domain:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
    except:
        pass
    return ""


def _clean_snippet(text):
    """Clean HTML tags and extra whitespace from snippet text."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ═══════════════════════════════════════════════════════
# DuckDuckGo Search (Free, No API Key)
# ═══════════════════════════════════════════════════════

def _ddg_search_all(query, max_results=20):
    """Search DuckDuckGo for web results."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": _clean_snippet(r.get("body", "")),
                    "source": urlparse(r.get("href", "")).netloc,
                    "favicon": _extract_favicon(r.get("href", "")),
                })
    except Exception as e:
        print(f"[BrowserSearch] DDG text error: {e}")
    return results


def _ddg_search_images(query, max_results=30):
    """Search DuckDuckGo for image results."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.images(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),          # page URL
                    "image": r.get("image", ""),       # direct image URL
                    "thumbnail": r.get("thumbnail", r.get("image", "")),
                    "source": r.get("source", urlparse(r.get("url", "")).netloc),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                })
    except Exception as e:
        print(f"[BrowserSearch] DDG images error: {e}")
    return results


def _ddg_search_videos(query, max_results=20):
    """Search DuckDuckGo for video results."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.videos(query, max_results=max_results):
                # Extract thumbnail
                images = r.get("images", {})
                thumbnail = ""
                if isinstance(images, dict):
                    thumbnail = images.get("large", images.get("medium", images.get("small", "")))
                elif isinstance(images, str):
                    thumbnail = images

                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("content", ""),       # video URL
                    "thumbnail": thumbnail,
                    "source": r.get("publisher", urlparse(r.get("content", "")).netloc),
                    "duration": r.get("duration", ""),
                    "description": _clean_snippet(r.get("description", "")),
                    "published": r.get("published", ""),
                })
    except Exception as e:
        print(f"[BrowserSearch] DDG videos error: {e}")
    return results


def _ddg_search_news(query, max_results=20):
    """Search DuckDuckGo for news results."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": _clean_snippet(r.get("body", "")),
                    "source": r.get("source", urlparse(r.get("url", "")).netloc),
                    "published": r.get("date", ""),
                    "image": r.get("image", "")
                })
    except Exception as e:
        print(f"[BrowserSearch] DDG news error: {e}")
    return results


# ═══════════════════════════════════════════════════════
# Google Custom Search (Optional, 100 free queries/day)
# ═══════════════════════════════════════════════════════

def _google_cse_search(query, search_type="all", max_results=10):
    """Search using Google Custom Search Engine API."""
    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_CX:
        return None  # Signal to use DDG fallback

    results = []
    try:
        params = {
            "key": GOOGLE_CSE_API_KEY,
            "cx": GOOGLE_CSE_CX,
            "q": query,
            "num": min(max_results, 10),
        }

        if search_type == "images":
            params["searchType"] = "image"
        elif search_type == "videos":
            params["q"] = f"{query} site:youtube.com OR site:vimeo.com"

        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=8
        )

        if resp.status_code != 200:
            print(f"[BrowserSearch] Google CSE HTTP {resp.status_code}")
            return None

        data = resp.json()
        items = data.get("items", [])

        for item in items:
            if search_type == "images":
                img_info = item.get("image", {})
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("image", {}).get("contextLink", ""),
                    "image": item.get("link", ""),
                    "thumbnail": img_info.get("thumbnailLink", item.get("link", "")),
                    "source": urlparse(item.get("displayLink", "")).netloc or item.get("displayLink", ""),
                    "width": img_info.get("width", 0),
                    "height": img_info.get("height", 0),
                })
            else:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": _clean_snippet(item.get("snippet", "")),
                    "source": item.get("displayLink", ""),
                    "favicon": _extract_favicon(item.get("link", "")),
                })

        print(f"[BrowserSearch] Google CSE returned {len(results)} results for '{query}' ({search_type})")

    except Exception as e:
        print(f"[BrowserSearch] Google CSE error: {e}")
        return None

    return results


# ═══════════════════════════════════════════════════════
# Main Search Function
# ═══════════════════════════════════════════════════════

def browser_search(query, search_type="all"):
    """
    Main search function for Browser Mode.
    
    Args:
        query: Search query string
        search_type: "all", "images", or "videos"
    
    Returns:
        List of result dicts
    """
    query = query.strip()
    if not query:
        return []

    print(f"[BrowserSearch] 🔍 Searching: '{query}' (type: {search_type})")

    # Try Google CSE first (if keys are configured)
    results = _google_cse_search(query, search_type)

    # Fall back to DuckDuckGo (free, always available)
    if results is None or len(results) == 0:
        print(f"[BrowserSearch] Using DuckDuckGo fallback")
        if search_type == "all":
            results = _ddg_search_all(query, max_results=20)
        elif search_type == "images":
            results = _ddg_search_images(query, max_results=30)
        elif search_type == "videos":
            results = _ddg_search_videos(query, max_results=20)
        elif search_type == "news":
            results = _ddg_search_news(query, max_results=20)
        else:
            results = _ddg_search_all(query, max_results=20)

    print(f"[BrowserSearch] ✅ Returning {len(results)} results")
    return results
