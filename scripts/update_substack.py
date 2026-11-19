"""Read the Substack feed and write the latest articles into index.html.

Runs daily on GitHub Actions. It replaces only the text between
<!-- SUBSTACK:START --> and <!-- SUBSTACK:END --> in index.html.
If the feed cannot be read, the page is left unchanged.
"""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://inclib.substack.com/feed"
PUB_URL = "https://inclib.substack.com/"
MAX_POSTS = 6
PAGE = Path(__file__).resolve().parent.parent / "index.html"
START, END = "<!-- SUBSTACK:START -->", "<!-- SUBSTACK:END -->"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "inculturationliberation-site/1.0 (+GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def plain(text, limit=220):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def build(feed_xml):
    root = ET.fromstring(feed_xml)
    items = root.findall("./channel/item")[:MAX_POSTS]
    if not items:
        return None
    rows = []
    for it in items:
        title = html.escape(plain(it.findtext("title"), 200))
        link = html.escape(it.findtext("link") or PUB_URL, quote=True)
        desc = html.escape(plain(it.findtext("description")))
        date = ""
        if it.findtext("pubDate"):
            try:
                date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%d %b %Y")
            except (TypeError, ValueError):
                pass
        row = f'      <li><a class="t" href="{link}" target="_blank" rel="noopener">{title}</a>'
        if date:
            row += f'<span class="d">{date}</span>'
        if desc:
            row += f"<p>{desc}</p>"
        rows.append(row + "</li>")
    return (
        "    <ul>\n" + "\n".join(rows) + "\n    </ul>\n"
        f'    <a class="all" href="{PUB_URL}" target="_blank" rel="noopener">All articles on Substack →</a>'
    )


def main():
    feed = Path(sys.argv[1]).read_bytes() if len(sys.argv) > 1 else fetch(FEED_URL)
    block = build(feed)
    if block is None:
        print("Feed has no posts yet; page unchanged.")
        return
    page = PAGE.read_text(encoding="utf-8")
    a, b = page.index(START) + len(START), page.index(END)
    new = page[:a] + "\n" + block + "\n" + page[b:]
    if new != page:
        PAGE.write_text(new, encoding="utf-8")
        print("index.html updated.")
    else:
        print("No new articles.")


if __name__ == "__main__":
    main()
