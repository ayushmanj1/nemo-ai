"""
browser_search.py — Backend search module for Thing AI Browser Mode.
Provides web search results for All / Images / Videos / News tabs.
Now uses Serper (serper.dev) for 100% reliable, structured Google Search results.
"""

import os
import re
import json
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv(override=True)

# Serper API Key from .env
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

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

def _serper_search(query, search_type="all"):
    """
    Search using Serper API.
    Supports: search (all), images, videos, news
    """
    if not SERPER_API_KEY:
        print("[BrowserSearch] No SERPER_API_KEY found.")
        return []

    # Map search_type to Serper endpoint
    endpoint_map = {
        "all": "search",
        "images": "images",
        "videos": "videos",
        "news": "news"
    }
    
    endpoint = endpoint_map.get(search_type, "search")
    url = f"https://google.serper.dev/{endpoint}"
    
    payload = json.dumps({
        "q": query,
        "num": 20 if search_type in ["images", "videos"] else 15
    })
    
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"[BrowserSearch] Serper API Error {response.status_code}: {response.text}")
            return []
            
        data = response.json()
        results = []
        
        if search_type == "all":
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": _clean_snippet(item.get("snippet", "")),
                    "source": urlparse(item.get("link", "")).netloc,
                    "favicon": _extract_favicon(item.get("link", ""))
                })
                
        elif search_type == "images":
            for item in data.get("images", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),          # the website page
                    "image": item.get("imageUrl", ""),    # the direct image
                    "thumbnail": item.get("thumbnailUrl", item.get("imageUrl", "")),
                    "source": item.get("source", urlparse(item.get("link", "")).netloc),
                    "width": item.get("imageWidth", 0),
                    "height": item.get("imageHeight", 0)
                })
                
        elif search_type == "videos":
            for item in data.get("videos", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),          # the video link (e.g. youtube)
                    "thumbnail": item.get("imageUrl", ""), # video thumbnail
                    "source": item.get("source", urlparse(item.get("link", "")).netloc),
                    "duration": item.get("duration", ""),
                    "description": _clean_snippet(item.get("snippet", "")),
                    "published": item.get("date", "")
                })
                
        elif search_type == "news":
            for item in data.get("news", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": _clean_snippet(item.get("snippet", "")),
                    "source": item.get("source", urlparse(item.get("link", "")).netloc),
                    "published": item.get("date", ""),
                    "image": item.get("imageUrl", "")
                })
                
        return results

    except Exception as e:
        print(f"[BrowserSearch] Serper API Exception: {e}")
        return []

# ═══════════════════════════════════════════════════════
# Main Search Function
# ═══════════════════════════════════════════════════════

def browser_search(query, search_type="all"):
    """
    Main search function for Browser Mode.
    
    Args:
        query: Search query string
        search_type: "all", "images", "videos", or "news"
    
    Returns:
        List of result dicts
    """
    query = query.strip()
    if not query:
        return []

    print(f"[BrowserSearch] 🔍 Searching via Serper: '{query}' (type: {search_type})")
    
    results = _serper_search(query, search_type)
    
    print(f"[BrowserSearch] ✅ Returning {len(results)} results")
    return results
