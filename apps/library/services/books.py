"""Open-source book / PDF search (Semantic Scholar, Open Library, DuckDuckGo)."""
from __future__ import annotations

import logging
import re
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

NOISE = {
    "tutorial", "course", "pdf", "filetype", "learn", "study", "guide", "free",
}


def clean_query(raw: str, max_words: int = 6) -> str:
    raw = re.sub(r"filetype:\S+", "", raw, flags=re.IGNORECASE)
    words = [w for w in raw.split() if w.lower() not in NOISE and len(w) > 2]
    return " ".join(words[:max_words]).strip() or raw.strip()[:80]


def search_books(query: str, limit: int = 10) -> list[dict]:
    q = clean_query(query)
    for fn in (_semantic_scholar, _open_library, _duckduckgo_pdfs):
        try:
            results = fn(q)
            if results:
                return results[:limit]
        except Exception as e:
            logger.warning("%s failed: %s", fn.__name__, e)
    return []


def _semantic_scholar(query: str) -> list[dict]:
    resp = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": query, "fields": "title,authors,year,openAccessPdf", "limit": 12},
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    out = []
    for paper in resp.json().get("data", []):
        pdf = paper.get("openAccessPdf")
        if not pdf or not pdf.get("url"):
            continue
        authors = ", ".join(a.get("name", "") for a in paper.get("authors", [])[:2])
        out.append({
            "title": paper.get("title", query),
            "author": authors,
            "url": pdf["url"],
            "source": "Semantic Scholar",
            "is_free": True,
        })
    return out


def _open_library(query: str) -> list[dict]:
    resp = requests.get(
        "https://openlibrary.org/search.json",
        params={"q": query, "fields": "title,author_name,ia", "limit": 12},
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    out = []
    for doc in resp.json().get("docs", []):
        ia = doc.get("ia")
        if not ia:
            continue
        ia_id = ia[0] if isinstance(ia, list) else ia
        authors = doc.get("author_name", [])
        pdf_url = _archive_resolve_pdf(ia_id)
        out.append({
            "title": doc.get("title", query),
            "author": authors[0] if authors else "",
            "url": pdf_url,
            "source": "Open Library",
            "is_free": True,
        })
    return out


def _archive_resolve_pdf(ia_id: str) -> str:
    """Pick a real .pdf file from archive.org metadata when the default name 404s."""
    try:
        r = requests.get(f"https://archive.org/metadata/{ia_id}", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            names = []
            for f in data.get("files", []):
                name = f.get("name") or ""
                if name.lower().endswith(".pdf"):
                    fmt = (f.get("format") or "").lower()
                    names.append((0 if "pdf" in fmt else 1, len(name), name))
            if names:
                names.sort()
                best = names[0][2]
                return f"https://archive.org/download/{ia_id}/{best}"
    except Exception:
        logger.warning("archive metadata failed for %s", ia_id)
    return f"https://archive.org/download/{ia_id}/{ia_id}.pdf"


def _duckduckgo_pdfs(query: str) -> list[dict]:
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": f"{query} programming book filetype:pdf"},
        headers=HEADERS,
        timeout=15,
    )
    soup = BeautifulSoup(resp.text, "html.parser")
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "uddg=" in href:
            real = unquote(href.split("uddg=")[1].split("&")[0])
        elif href.startswith("http"):
            real = href
        else:
            continue
        if real in seen or ".pdf" not in real.lower():
            continue
        seen.add(real)
        name = re.sub(r"\.pdf.*", "", real.split("/")[-1], flags=re.I).replace("%20", " ").replace("-", " ")
        out.append({
            "title": name[:80] or query,
            "author": "",
            "url": real,
            "source": "Web",
            "is_free": True,
        })
        if len(out) >= 10:
            break
    return out


def is_safe_remote_book_url(url: str) -> bool:
    from urllib.parse import urlparse

    p = urlparse((url or "").strip())
    if p.scheme not in ("http", "https"):
        return False
    host = (p.netloc or "").lower()
    if not host or host.startswith("127.") or host in ("localhost", "::1"):
        return False
    if host.endswith(".local"):
        return False
    return True
