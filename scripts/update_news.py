#!/usr/bin/env python3
"""
Fetches latest news about Salah Sarsour from Google News RSS and updates
the news ticker and news cards in index.html.

Uses only Python standard library -- no pip installs required.
"""

import os
import platform
import re
import sys
import html
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=Salah+Sarsour&hl=en-US&gl=US&ceid=US:en"
)

MAX_ARTICLES = 10

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(REPO_ROOT, "index.html")

# strftime day-without-leading-zero: %-d on Linux/macOS, %#d on Windows
_DAY_FMT = "%#d" if platform.system() == "Windows" else "%-d"
DATE_FMT = f"%B {_DAY_FMT}, %Y"  # e.g. "April 2, 2026"


def fetch_rss():
    """Download and parse Google News RSS feed. Returns list of article dicts."""
    req = urllib.request.Request(RSS_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; FreeSalahSarsourBot/1.0)"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    articles = []

    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        source_el = item.find("source")

        if title_el is None or link_el is None:
            continue

        title_text = title_el.text or ""
        link_text = link_el.text or ""

        # Google News often appends " - Source Name" to the title
        source_name = ""
        if source_el is not None and source_el.text:
            source_name = source_el.text.strip()
            # Remove trailing " - Source" from title if present
            suffix = " - " + source_name
            if title_text.endswith(suffix):
                title_text = title_text[: -len(suffix)]

        # Parse date
        date_str = ""
        if pub_date_el is not None and pub_date_el.text:
            try:
                # RFC 2822 format: "Wed, 02 Apr 2026 12:00:00 GMT"
                dt = datetime.strptime(
                    pub_date_el.text.strip(),
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                date_str = dt.strftime(DATE_FMT)  # "April 2, 2026"
            except (ValueError, AttributeError):
                try:
                    dt = datetime.strptime(
                        pub_date_el.text.strip()[:25],
                        "%a, %d %b %Y %H:%M:%S"
                    )
                    date_str = dt.strftime(DATE_FMT)
                except (ValueError, AttributeError):
                    date_str = pub_date_el.text.strip()

        articles.append({
            "title": title_text.strip(),
            "link": link_text.strip(),
            "source": source_name.upper() if source_name else "NEWS",
            "date": date_str,
        })

    return articles[:MAX_ARTICLES]


def escape(text):
    """HTML-escape text for safe embedding."""
    return html.escape(text, quote=True)


def build_ticker_html(articles):
    """Build the inner HTML for the news-ticker-inner div (duplicated for seamless scroll)."""
    items = []
    for art in articles:
        items.append(
            f'<span class="news-ticker-item">'
            f'<span class="news-ticker-source">{escape(art["source"])}</span> '
            f'<a href="{escape(art["link"])}" target="_blank">{escape(art["title"])}</a>'
            f'</span>'
        )
        items.append('<span class="news-ticker-dot">&bull;</span>')

    single_pass = "\n        ".join(items)
    # Duplicate for seamless infinite scroll
    full = single_pass + "\n        " + single_pass
    return full


def build_cards_html(articles):
    """Build the inner HTML for the news-grid div."""
    cards = []
    for art in articles:
        cards.append(
            f'<div class="news-card">\n'
            f'            <div><div class="news-card-source">{escape(art["source"])}</div>\n'
            f'            <div class="news-card-title"><a href="{escape(art["link"])}" target="_blank">'
            f'{escape(art["title"])}</a></div></div>\n'
            f'            <div class="news-card-date">{escape(art["date"])}</div>\n'
            f'        </div>'
        )
    return "\n        ".join(cards)


def update_index(articles):
    """Replace ticker and cards sections in index.html. Returns True if file was changed."""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # --- Update news ticker ---
    # Match everything inside <div class="news-ticker-inner">...</div>
    ticker_pattern = re.compile(
        r'(<div\s+class="news-ticker-inner">)\s*(.*?)\s*(</div>\s*</div>\s*\n*\s*<!-- HERO)',
        re.DOTALL,
    )
    ticker_match = ticker_pattern.search(content)
    if ticker_match:
        new_ticker = build_ticker_html(articles)
        content = (
            content[: ticker_match.start()]
            + ticker_match.group(1)
            + "\n        "
            + new_ticker
            + "\n    "
            + ticker_match.group(3)
            + content[ticker_match.end():]
        )
    else:
        print("WARNING: Could not find news-ticker-inner section in index.html")

    # --- Update news cards ---
    cards_pattern = re.compile(
        r'(<div\s+class="news-grid">)\s*(.*?)\s*(</div>\s*</section>)',
        re.DOTALL,
    )
    cards_match = cards_pattern.search(content)
    if cards_match:
        new_cards = build_cards_html(articles)
        content = (
            content[: cards_match.start()]
            + cards_match.group(1)
            + "\n        "
            + new_cards
            + "\n    "
            + cards_match.group(3)
            + content[cards_match.end():]
        )
    else:
        print("WARNING: Could not find news-grid section in index.html")

    if content == original:
        return False

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def main():
    print(f"Fetching news from Google News RSS...")
    try:
        articles = fetch_rss()
    except (urllib.error.URLError, ET.ParseError, OSError) as e:
        print(f"ERROR fetching RSS feed: {e}")
        print("Existing content left unchanged.")
        sys.exit(0)  # Exit cleanly so CI doesn't fail

    if not articles:
        print("No articles found. Existing content left unchanged.")
        sys.exit(0)

    print(f"Found {len(articles)} articles:")
    for i, art in enumerate(articles, 1):
        print(f"  {i}. [{art['source']}] {art['title']}")

    changed = update_index(articles)
    if changed:
        print(f"\nindex.html updated successfully.")
    else:
        print(f"\nNo changes needed (content identical).")


if __name__ == "__main__":
    main()
