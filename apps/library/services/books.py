"""Open-source book / PDF search (Semantic Scholar, Open Library, DuckDuckGo, Google Books)."""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Q

try:
    from django.core.cache import cache
except Exception:  # pragma: no cover
    cache = None

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
REMOTE_TIMEOUT_SECONDS = getattr(settings, "BOOK_REMOTE_TIMEOUT_SECONDS", 7)
BOOK_SEARCH_CACHE_TTL = getattr(settings, "BOOK_SEARCH_CACHE_TTL", timedelta(minutes=15))
SEARCH_CACHE_TTL_SECONDS = int(BOOK_SEARCH_CACHE_TTL.total_seconds())
GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_API_KEY = (getattr(settings, "GOOGLE_BOOKS_API_KEY", "") or "").strip()

NOISE = {
    "tutorial", "course", "pdf", "filetype", "learn", "study", "guide", "free",
}


def clean_query(raw: str, max_words: int = 6) -> str:
    raw = re.sub(r"filetype:\S+", "", raw, flags=re.IGNORECASE)
    words = [w for w in raw.split() if w.lower() not in NOISE and len(w) > 2]
    return " ".join(words[:max_words]).strip() or raw.strip()[:80]


def search_books(query: str, limit: int = 10) -> list[dict]:
    local_results = search_local_books(query, limit)
    if len(local_results) >= limit:
        return local_results

    remote_results = search_remote_books(query, limit - len(local_results))
    return local_results + remote_results


def search_local_books(query: str, limit: int = 10) -> list[dict]:
    from apps.library.models import Book

    normalized = query.strip()
    books_qs = Book.objects.filter(is_active=True)
    if normalized:
        books_qs = books_qs.filter(
            Q(title__icontains=normalized)
            | Q(author__icontains=normalized)
            | Q(description__icontains=normalized)
            | Q(language__icontains=normalized)
            | Q(category__icontains=normalized)
        )
    out = []
    for book in books_qs.order_by("-created_at")[:limit]:
        pdf_url = book.pdf_file.url if book.pdf_file else (book.url if (book.url or "").lower().endswith(".pdf") else "")
        viewer_type = "pdf" if pdf_url else "external"
        preview_url = pdf_url or book.url
        out.append({
            "book_id": book.pk,
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "source": "Library",
            "is_free": True,
            "is_pdf": bool(pdf_url),
            "viewer_type": viewer_type,
            "pdf_url": pdf_url,
            "preview_url": preview_url,
            "download_url": pdf_url,
            "cover_url": book.cover.url if book.cover else "",
            "url": book.url,
            "language": book.language,
            "category": book.category,
            "pages": book.pages,
            "is_cached": book.is_cached,
            "cached_at": book.cached_at,
            "cache_size": book.cache_size,
            "cache_expires_at": book.cache_expires_at,
        })
    return out


def search_remote_books(query: str, limit: int = 10) -> list[dict]:
    normalized_query = re.sub(r"\s+", " ", (query or "").strip()).lower()
    cache_key = f"library:remote_search:{hashlib.sha256(f'{normalized_query}|{limit}'.encode('utf-8')).hexdigest()}"
    if cache is not None:
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            return cached_results

    out: list[dict] = []
    sources = [_semantic_scholar, _open_library, _duckduckgo_pdfs, _google_books]
    for source in sources:
        try:
            items = source(query, limit) if source is _google_books else source(query)
        except Exception:
            continue
        for item in items:
            if len(out) >= limit:
                break
            source_url = item.get("url") or item.get("info_link") or item.get("web_reader_link") or ""
            pdf_url = item.get("pdf_download") or item.get("pdf_url") or ""
            if not pdf_url and _is_pdf_url(source_url):
                pdf_url = source_url
            if pdf_url and not _is_pdf_url(pdf_url):
                pdf_url = ""
            if not source_url and pdf_url:
                source_url = pdf_url
            if not source_url:
                continue
            viewer_type = _get_viewer_type(source_url, pdf_url)
            out.append({
                "book_id": None,
                "title": item.get("title", query),
                "author": item.get("author", ""),
                "description": item.get("description", ""),
                "source": item.get("source", "Web"),
                "is_free": item.get("is_free", True),
                "is_pdf": bool(pdf_url),
                "viewer_type": viewer_type,
                "pdf_url": pdf_url,
                "cover_url": item.get("thumbnail", ""),
                "url": source_url,
                "language": item.get("language", ""),
                "category": item.get("category", ""),
                "pages": item.get("page_count"),
                "is_cached": False,
                "cached_at": None,
                "cache_size": 0,
                "cached_expires_at": None,
            })
        if len(out) >= limit:
            break
    if cache is not None:
        cache.set(cache_key, out, SEARCH_CACHE_TTL_SECONDS)
    return out


def _semantic_scholar(query: str) -> list[dict]:
    resp = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": query, "fields": "title,authors,year,openAccessPdf", "limit": 12},
        headers=HEADERS,
        timeout=REMOTE_TIMEOUT_SECONDS,
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
            "is_pdf": True,
        })
    return out


def _open_library(query: str) -> list[dict]:
    resp = requests.get(
        "https://openlibrary.org/search.json",
        params={"q": query, "fields": "title,author_name,ia,key", "limit": 12},
        headers=HEADERS,
        timeout=REMOTE_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        return []
    out = []
    for doc in resp.json().get("docs", []):
        doc_key = doc.get("key")
        if not doc_key:
            continue
        openlibrary_url = f"https://openlibrary.org{doc_key}"
        authors = doc.get("author_name", [])
        out.append({
            "title": doc.get("title", query),
            "author": authors[0] if authors else "",
            "url": openlibrary_url,
            "source": "Open Library",
            "is_free": True,
            "is_pdf": False,
            "pdf_url": "",
        })
    return out


def _archive_resolve_pdf(ia_id: str) -> str:
    """Pick a real .pdf file from archive.org metadata when the default name 404s."""
    try:
        r = requests.get(f"https://archive.org/metadata/{ia_id}", headers=HEADERS, timeout=REMOTE_TIMEOUT_SECONDS)
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
            "is_pdf": True,
        })
        if len(out) >= 10:
            break
    return out


def is_safe_remote_book_url(url: str) -> bool:
    p = urlparse((url or "").strip())
    if p.scheme not in ("http", "https"):
        return False
    host = (p.netloc or "").lower()
    if not host or host.startswith("127.") or host in ("localhost", "::1"):
        return False
    if host.endswith(".local"):
        return False
    return True


def _pdf_cache_dir() -> Path:
    path = Path(settings.MEDIA_ROOT) / "cached_pdfs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cached_pdf_path(url: str) -> Path:
    return _pdf_cache_dir() / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.pdf"


def cache_remote_pdf(url: str) -> Path | None:
    if not is_safe_remote_book_url(url):
        return None
    resolved = resolve_openlibrary_pdf_url(url) or url
    pdf_path = cached_pdf_path(resolved)
    if pdf_path.is_file() and pdf_path.stat().st_size > 1024:
        return pdf_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://archive.org/",
    }
    response = None
    try:
        response = requests.get(
            resolved,
            headers=headers,
            timeout=90,
            stream=True,
            allow_redirects=True,
        )
        if response.status_code != 200:
            return None

        tmp_path = pdf_path.with_suffix(f".tmp-{uuid.uuid4().hex}")
        first_chunk = None
        with tmp_path.open("wb") as out_file:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    if first_chunk is None:
                        first_chunk = chunk
                    out_file.write(chunk)

        if tmp_path.stat().st_size <= 1024 or not first_chunk or first_chunk[:4] != b"%PDF":
            tmp_path.unlink(missing_ok=True)
            return None

        try:
            tmp_path.replace(pdf_path)
        except Exception:
            if pdf_path.is_file() and pdf_path.stat().st_size > 1024:
                tmp_path.unlink(missing_ok=True)
                return pdf_path
            tmp_path.unlink(missing_ok=True)
            return None
        return pdf_path
    except Exception:
        return None
    finally:
        try:
            if response is not None:
                response.close()
        except Exception:
            pass


def find_alternative_book_url(query: str) -> tuple[str | None, bool]:
    if not query or not GOOGLE_BOOKS_API_KEY:
        return None, False
    for item in _google_books(query, 8):
        if item.get("is_pdf") and item.get("pdf_download"):
            return item["pdf_download"], True
        if item.get("web_reader_link"):
            return item["web_reader_link"], False
        if item.get("info_link"):
            return item["info_link"], False
    return None, False


def _google_books(query: str, limit: int) -> list[dict]:
    if not GOOGLE_BOOKS_API_KEY or not query:
        return []
    params = {
        "q": query,
        "filter": "free-ebooks",
        "printType": "books",
        "maxResults": min(limit, 40),
        "key": GOOGLE_BOOKS_API_KEY,
    }
    try:
        resp = requests.get(
            GOOGLE_BOOKS_BASE_URL,
            params=params,
            headers=HEADERS,
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            return []
        out = []
        for item in resp.json().get("items", [])[:limit]:
            volume_info = item.get("volumeInfo", {})
            access_info = item.get("accessInfo", {})
            title = volume_info.get("title", query)
            authors = ", ".join(volume_info.get("authors", []))
            pdf_info = access_info.get("pdf", {}) or {}
            pdf_download = pdf_info.get("downloadLink") if pdf_info.get("isAvailable") else None
            web_reader_link = access_info.get("webReaderLink") or volume_info.get("previewLink")
            info_link = volume_info.get("infoLink")
            thumbnail = volume_info.get("imageLinks", {}).get("thumbnail", "")
            description = (volume_info.get("description") or "")
            publisher = volume_info.get("publisher", "")
            published_date = volume_info.get("publishedDate", "")
            page_count = volume_info.get("pageCount")
            if pdf_download and pdf_download.lower().endswith(".pdf"):
                url = pdf_download
            elif web_reader_link:
                url = web_reader_link
            elif info_link:
                url = info_link
            else:
                continue
            if url.startswith("http://"):
                url = url.replace("http://", "https://", 1)
            out.append({
                "title": title,
                "author": authors,
                "url": url,
                "source": "Google Books",
                "is_free": True,
                "is_pdf": bool(pdf_download),
                "thumbnail": thumbnail,
                "web_reader_link": web_reader_link,
                "pdf_download": pdf_download,
                "info_link": info_link,
                "description": description,
                "publisher": publisher,
                "published_date": published_date,
                "page_count": page_count,
            })
        return out
    except Exception:
        logger.exception("Google Books API failed")
        return []


def resolve_openlibrary_pdf_url(open_url: str) -> str | None:
    try:
        parsed = urlparse(open_url)
        if parsed.netloc.lower() != "openlibrary.org":
            return None
        path = parsed.path.rstrip("/")
        if path.startswith("/works/"):
            return _resolve_openlibrary_work_pdf(path)
        if path.startswith("/books/"):
            return _resolve_openlibrary_book_pdf(path)
    except Exception:
        logger.debug("Failed to resolve Open Library PDF URL for %s", open_url, exc_info=True)
    return None


def _resolve_openlibrary_work_pdf(work_path: str) -> str | None:
    try:
        resp = requests.get(
            f"https://openlibrary.org{work_path}/editions.json",
            params={"limit": 50},
            headers=HEADERS,
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            return None
        for entry in resp.json().get("entries", []):
            ia_value = entry.get("ia") or entry.get("ocaid")
            if not ia_value:
                continue
            ia_id = ia_value[0] if isinstance(ia_value, list) else ia_value
            if not ia_id:
                continue
            pdf_url = _archive_resolve_pdf(ia_id)
            if _is_url_accessible(pdf_url):
                return pdf_url
    except Exception:
        logger.debug("Open Library work PDF resolution failed for %s", work_path, exc_info=True)
    return None


def _resolve_openlibrary_book_pdf(book_path: str) -> str | None:
    try:
        resp = requests.get(
            f"https://openlibrary.org{book_path}.json",
            headers=HEADERS,
            timeout=REMOTE_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        ia_value = data.get("ia") or data.get("ocaid")
        if not ia_value:
            return None
        ia_id = ia_value[0] if isinstance(ia_value, list) else ia_value
        if not ia_id:
            return None
        pdf_url = _archive_resolve_pdf(ia_id)
        if _is_pdf_url(pdf_url):
            return pdf_url
    except Exception:
        logger.debug("Open Library book PDF resolution failed for %s", book_path, exc_info=True)
    return None


def _is_google_books_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").lower()
    if "books.google.com" in host:
        return True
    if "play.google.com" in host:
        return parsed.path.startswith("/books/reader")
    return False


def _is_doi_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").lower()
    return "doi.org" in host or url.lower().startswith("doi:")


def _is_openlibrary_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return "openlibrary.org" in (parsed.netloc or "").lower()


def _is_archive_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return "archive.org" in (parsed.netloc or "").lower()


def _get_viewer_type(source_url: str, pdf_url: str | None = None) -> str:
    if pdf_url and _is_pdf_url(pdf_url):
        if _is_archive_url(pdf_url):
            return "archive"
        return "pdf"
    if _is_google_books_url(source_url):
        return "google_books"
    if _is_doi_url(source_url):
        return "doi"
    if _is_openlibrary_url(source_url):
        return "openlibrary"
    if _is_archive_url(source_url):
        return "archive"
    if source_url:
        return "html"
    return "external"


def _is_pdf_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower()
    if "doi.org" in host or url.lower().startswith("doi:"):
        return False
    return parsed.path.lower().endswith(".pdf")


def _is_url_accessible(url: str, timeout: int = 4) -> bool:
    try:
        resp = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        content_type = (resp.headers.get("content-type") or "").lower()
        parsed = urlparse(resp.url or url)
        if resp.status_code in (200, 206) and content_type.startswith("application/pdf"):
            return True
        if resp.status_code in (200, 206) and parsed.path.lower().endswith(".pdf"):
            return True
        if resp.status_code in (302, 303, 307, 308):
            final_url = resp.url
            return _is_pdf_url(final_url)
        if resp.status_code in (401, 403, 405):
            get_resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True, allow_redirects=True)
            get_content_type = (get_resp.headers.get("content-type") or "").lower()
            if get_resp.status_code in (200, 206) and get_content_type.startswith("application/pdf"):
                get_resp.close()
                return True
        return False
    except Exception:
        logger.debug("URL check failed: %s", url)
        return False
