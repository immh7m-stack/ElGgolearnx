import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

import mimetypes
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from apps.roadmaps.models import Field
from apps.quizzes.models import VideoQuizCatalog, QuizAttempt

from .models import Book, DownloadJob, UserLibraryItem, UserPlaylist
from .playlist_utils import record_playlist_open
from .services import books, cache, download, youtube

logger = logging.getLogger(__name__)


def search_page(request):
    query = request.GET.get("q", "").strip()
    search_type = (request.GET.get("search_type") or request.GET.get("type") or "courses").strip().lower()
    if search_type not in {"courses", "books", "all"}:
        search_type = "courses"

    playlists = []
    book_results = []
    grouped_book_results = []
    recommended_sites = []

    if query:
        if search_type in {"courses", "all"}:
            playlists = youtube.search_playlists(query, max_results=8)
        if search_type in {"books", "all"}:
            book_results = books.search_books(query, limit=40)
            if book_results:
                grouped = {}
                for book in book_results:
                    source_name = book.get("source") or "Other"
                    grouped.setdefault(source_name, []).append(book)
                grouped_book_results = [{"source": source, "books": items} for source, items in grouped.items()]

            from .models import EducationalSite

            query_terms = [term.lower() for term in re.findall(r"[\w\u0600-\u06FF]+", query)]
            candidate_sites = list(EducationalSite.objects.filter(is_active=True))
            for site in candidate_sites:
                haystack = " ".join(
                    filter(None, [site.name, site.name_ar, site.description_en, site.description_ar])
                ).lower()
                site_tags = [str(tag).lower() for tag in (site.fields_tags or [])]
                if any(term in haystack for term in query_terms) or any(term in site_tags for term in query_terms):
                    recommended_sites.append(site)
            if not recommended_sites:
                recommended_sites = [site for site in candidate_sites if site.category in {"books", "docs"}][:6]

    quick_topics = ["Python", "JavaScript", "React", "Machine Learning", "Cybersecurity", "SQL"]
    search_modes = [
        ("courses", "Playlists"),
        ("books", "Books"),
        ("all", "Both"),
    ]
    return render(
        request,
        "library/search.html",
        {
            "query": query,
            "search_type": search_type,
            "playlists": playlists,
            "book_results": book_results,
            "grouped_book_results": grouped_book_results,
            "recommended_sites": recommended_sites,
            "quick_topics": quick_topics,
            "search_modes": search_modes,
        },
    )


def search_api(request):
    query = request.GET.get("q", "").strip()
    search_type = (request.GET.get("search_type") or request.GET.get("type") or "courses").strip().lower()
    if search_type not in {"courses", "books", "all"}:
        search_type = "courses"

    playlists = []
    book_results = []

    if query:
        if search_type in {"courses", "all"}:
            playlists = youtube.search_playlists(query, max_results=8)
        if search_type in {"books", "all"}:
            book_results = books.search_books(query, limit=40)

    return JsonResponse({
        "query": query,
        "search_type": search_type,
        "playlists": playlists,
        "book_results": book_results,
    })


def sites_page(request):
    from .models import EducationalSite

    category = request.GET.get("category", "")
    field = request.GET.get("field", "")
    sites = EducationalSite.objects.filter(is_active=True)
    if category:
        sites = sites.filter(category=category)
    if field:
        sites = [s for s in sites if field in (s.fields_tags or []) or not s.fields_tags]
    return render(
        request,
        "library/sites.html",
        {
            "sites": sites,
            "categories": EducationalSite.CATEGORY_CHOICES,
            "current_category": category,
            "fields": Field.objects.filter(is_active=True),
        },
    )


@login_required
def my_library(request):
    playlists = list(UserPlaylist.objects.filter(user=request.user))
    for pl in playlists:
        if pl.playlist_id and not (pl.thumbnail or "").strip():
            meta = youtube.get_playlist_meta(pl.playlist_id)
            t = (meta.get("thumbnail", "") if meta else "") or ""
            if t:
                UserPlaylist.objects.filter(pk=pl.pk).update(thumbnail=t)
                pl.thumbnail = t
    items = UserLibraryItem.objects.filter(user=request.user)
    downloads = DownloadJob.objects.filter(user=request.user)[:20]
    return render(
        request,
        "library/my_library.html",
        {"items": items, "playlists": playlists, "downloads": downloads},
    )


@login_required
def history_page(request):
    playlists = UserPlaylist.objects.filter(user=request.user)[:100]
    book_items = UserLibraryItem.objects.filter(user=request.user, item_type="book")[:100]
    return render(
        request,
        "library/history.html",
        {"playlists": playlists, "book_items": book_items},
    )


def watch_playlist(request):
    url = request.GET.get("url", "")
    title = request.GET.get("title", "Course")
    playlist_id = request.GET.get("list", "")
    if not url and playlist_id:
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
    videos = youtube.get_playlist_videos(url) if url else []
    thumb = ""
    if playlist_id:
        meta = youtube.get_playlist_meta(playlist_id)
        if meta:
            thumb = meta.get("thumbnail", "")
            title = title or meta.get("title", "Course")
    elif videos:
        playlist_id = youtube.extract_playlist_id_from_url(url)
    record_playlist_open(
        request.user,
        url,
        title,
        playlist_id,
        thumb,
    )

    first_video_id = (videos[0].get("video_id") if videos and isinstance(videos[0], dict) else "") or youtube.extract_video_id_from_url(url or "")
    quiz_catalog = None
    quiz_attempts = []
    if first_video_id:
        quiz_catalog = VideoQuizCatalog.objects.filter(video_id=first_video_id).first()
        if request.user.is_authenticated and quiz_catalog is not None:
            quiz_attempts = (
                QuizAttempt.objects.filter(user=request.user, video_catalog=quiz_catalog)
                .order_by("-completed_at")[:3]
            )

    return render(
        request,
        "library/watch.html",
        {
            "playlist_url": url,
            "title": title,
            "videos": videos,
            "hero_thumb": thumb,
            "playlist_id": playlist_id or youtube.extract_playlist_id_from_url(url or ""),
            "first_video_id": first_video_id,
            "quiz_catalog": quiz_catalog,
            "attempts": quiz_attempts,
        },
    )


@login_required
def read_book_page(request):
    book_id = request.GET.get("book_id", "").strip()
    url = request.GET.get("url", "").strip()
    title = request.GET.get("title", "Book").strip()
    is_pdf = request.GET.get("is_pdf", "1") == "1"

    book = None
    viewer_type = request.GET.get("viewer_type", "")
    if book_id and book_id.lower() != "none":
        try:
            book = Book.objects.get(pk=book_id, is_active=True)
        except (Book.DoesNotExist, ValueError):
            return HttpResponse("Invalid book ID", status=400)
        url = book.pdf_file.url if book.pdf_file else book.url
        title = title or book.title
        is_pdf = bool(book.pdf_file or (book.url or "").lower().endswith(".pdf"))
        viewer_type = "pdf" if is_pdf else "external"

    if not url:
        return HttpResponse("Invalid book URL", status=400)

    reader_src = url
    if viewer_type == "pdf" or (is_pdf and books._is_pdf_url(url)):
        if book:
            reader_src = f"{reverse('library:read_pdf')}?book_id={book.pk}&title={requests.utils.quote(title, safe='')}"
        else:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and books._is_pdf_url(url):
                reader_src = (
                    f"{reverse('library:read_pdf')}?url={requests.utils.quote(url, safe='')}"
                    f"&title={requests.utils.quote(title, safe='')}"
                )
            else:
                viewer_type = "external"

    if viewer_type == "google_books":
        logger.info("read_book_page -> redirect to google_books_viewer, reader_src=%s, url=%s, title=%s, is_pdf=%s", reverse('library:google_books_viewer'), url, title, is_pdf)
        return redirect(f"{reverse('library:google_books_viewer')}?url={requests.utils.quote(url, safe='')}&title={requests.utils.quote(title, safe='')}")

    if viewer_type in {"doi", "html", "openlibrary", "external"}:
        logger.info("read_book_page -> external redirect, url=%s, title=%s, is_pdf=%s", url, title, is_pdf)
        return redirect(url)

    logger.info("read_book_page -> render read_book.html, reader_src=%s, url=%s, title=%s, is_pdf=%s", reader_src, url, title, is_pdf)
    return render(
        request,
        "library/read_book.html",
        {
            "book_url": url,
            "reader_src": reader_src,
            "title": title,
            "is_pdf": is_pdf,
        },
    )


def _google_books_embed_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    query = parse_qs(parsed.query)
    if "books.google.com" in host:
        embedded_id = query.get("id", [None])[0] or query.get("vid", [None])[0]
        if embedded_id:
            return f"https://books.google.com/books?id={embedded_id}&printsec=frontcover&output=embed"
    if "play.google.com" in host and parsed.path.startswith("/books/reader"):
        embedded_id = query.get("id", [None])[0]
        if embedded_id:
            return f"https://books.google.com/books?id={embedded_id}&printsec=frontcover&output=embed"
    return url


def google_books_viewer(request):
    url = request.GET.get("url", "").strip()
    title = request.GET.get("title", "").strip()
    if not url or not books.is_safe_remote_book_url(url):
        return HttpResponse("Invalid Google Books URL", status=400)

    return render(
        request,
        "library/google_books_viewer.html",
        {
            "viewer_url": _google_books_embed_url(url),
            "title": title or "Google Books",
        },
    )


@login_required
@require_POST
def save_playlist(request):
    url = request.POST.get("url", "").strip()
    title = request.POST.get("title", "Playlist")
    thumbnail = request.POST.get("thumbnail", "")
    post_pid = request.POST.get("playlist_id", "").strip()
    canon, playlist_id = youtube.canonical_playlist_url(url, post_pid)
    playlist_id = playlist_id or youtube.extract_playlist_id_from_url(url)
    url_final = canon or url.strip()
    if playlist_id and not thumbnail:
        meta = youtube.get_playlist_meta(playlist_id)
        thumbnail = meta.get("thumbnail", "") if meta else ""
    if playlist_id:
        _, _ = UserPlaylist.objects.update_or_create(
            user=request.user,
            playlist_id=playlist_id,
            defaults={
                "youtube_url": url_final,
                "title": title,
                "thumbnail": thumbnail,
                "source_query": request.POST.get("query", ""),
                "is_saved_explicit": True,
                "last_opened_at": timezone.now(),
            },
        )
    else:
        _, _ = UserPlaylist.objects.update_or_create(
            user=request.user,
            youtube_url=url_final,
            defaults={
                "title": title,
                "thumbnail": thumbnail,
                "source_query": request.POST.get("query", ""),
                "is_saved_explicit": True,
                "last_opened_at": timezone.now(),
            },
        )
    messages.success(request, "Saved to your library & history.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("library:my_library"))


@login_required
@require_POST
def save_book(request):
    UserLibraryItem.objects.create(
        user=request.user,
        item_type="book",
        title=request.POST.get("title", ""),
        url=request.POST.get("url", ""),
        field_slug=request.POST.get("field_slug", ""),
    )
    messages.success(request, "Book saved.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("library:my_library"))


def _sanitize_download_name(name: str) -> str:
    safe = re.sub(r'[\\/*?:"<>|\n\r\t]', "", name or "video")
    return safe.strip().replace(" ", "_")[:100] or "video"


def _stream_downloaded_file(file_path: Path, temp_dir: Path, filename: str):
    def stream():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    content_type, _ = mimetypes.guess_type(str(file_path))
    response = StreamingHttpResponse(stream(), content_type=content_type or "application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, max-age=0, no-cache"
    return response


def _build_zip_archive(source_dir: Path, archive_name: str) -> Path:
    archive_path = source_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.iterdir()):
            if not file_path.is_file() or file_path.name.endswith(".part"):
                continue
            archive.write(file_path, arcname=file_path.name)
    return archive_path


def _stream_local_file(file_path: Path, title: str, want_download: bool) -> StreamingHttpResponse:
    def stream():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk
    content_type, _ = mimetypes.guess_type(str(file_path))
    response = StreamingHttpResponse(stream(), content_type=content_type or "application/pdf")
    fname = title or file_path.name
    if not fname.lower().endswith(".pdf"):
        fname = f"{fname}.pdf"
    disp = "attachment" if want_download else "inline"
    response["Content-Disposition"] = f'{disp}; filename="{fname}"'
    response["Cache-Control"] = "private, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def start_download_view(request):
    url = request.POST.get("url", "").strip()
    title = request.POST.get("title", "Course")
    single_video = request.POST.get("video_id", "").strip()
    direct_download = request.POST.get("direct") == "1"

    if single_video:
        title = request.POST.get("video_title", title)
        video_url = f"https://www.youtube.com/watch?v={single_video}"
        temp_dir = Path(tempfile.mkdtemp(prefix="elgolearnx_dl_"))
        try:
            import yt_dlp

            outtmpl = str(temp_dir / "%(title).80s.%(ext)s")
            opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

            downloaded_files = [p for p in temp_dir.iterdir() if p.is_file() and not p.name.endswith(".part")]
            if not downloaded_files:
                raise RuntimeError("No downloaded file found")
            file_path = downloaded_files[0]
            filename = _sanitize_download_name(title or info.get("title", single_video)) + file_path.suffix
            return _stream_downloaded_file(file_path, temp_dir, filename)
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            messages.error(request, f"Download failed: {str(exc)[:200]}")
            return redirect(request.META.get("HTTP_REFERER") or reverse("library:search"))

    if direct_download and url:
        temp_dir = Path(tempfile.mkdtemp(prefix="elgolearnx_dl_"))
        try:
            import yt_dlp

            outtmpl = str(temp_dir / "%(playlist_index)02d - %(title).80s.%(ext)s")
            opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": outtmpl,
                "noplaylist": False,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            downloaded_files = [p for p in temp_dir.iterdir() if p.is_file() and not p.name.endswith(".part")]
            if not downloaded_files:
                raise RuntimeError("No downloaded files found")

            zip_path = _build_zip_archive(temp_dir, "playlist.zip")
            filename = _sanitize_download_name(title or "playlist") + ".zip"
            return _stream_downloaded_file(zip_path, temp_dir, filename)
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            messages.error(request, f"Download failed: {str(exc)[:200]}")
            return redirect(request.META.get("HTTP_REFERER") or reverse("library:search"))

    if not url:
        messages.error(request, "Invalid URL.")
        return redirect("library:search")
    job = DownloadJob.objects.create(user=request.user, title=title, source_url=url)
    download.start_download(job.pk)
    messages.info(request, "Download started — check My Library.")
    return redirect("library:my_library")


@login_required
@require_POST
def cancel_download_view(request, job_id):
    job = get_object_or_404(DownloadJob, pk=job_id, user=request.user)
    if job.status in ("pending", "running"):
        job.status = "cancelled"
        job.save(update_fields=["status", "updated_at"])
        messages.info(request, "تم طلب إلغاء التحميل؛ ستُزال الملفات الجزئية عند توقف العملية.")
    return redirect("library:my_library")


@login_required
@require_POST
def delete_download_job_view(request, job_id):
    job = get_object_or_404(DownloadJob, pk=job_id, user=request.user)
    download.cleanup_job_files(job)
    job.delete()
    messages.success(request, "تم حذف التحميل من القائمة والمجلد المرتبط به.")
    return redirect("library:my_library")


@login_required
def download_status(request, job_id):
    job = get_object_or_404(DownloadJob, pk=job_id, user=request.user)
    return JsonResponse({
        "status": job.status,
        "progress_pct": job.progress_pct,
        "file_path": job.file_path,
        "error": job.error_message,
        "estimated_bytes": job.estimated_bytes,
        "estimated_label_ar": job.estimated_size_label_ar(),
    })


def read_remote_pdf(request):
    """Stream PDFs through the app. Use ?disposition=attachment to force download."""
    book_id = request.GET.get("book_id", "").strip()
    raw = request.GET.get("url", "").strip()
    title = request.GET.get("title", "").strip()
    source = request.GET.get("source", "").strip()
    want_download = request.GET.get("disposition", "").lower() == "attachment"

    book = None
    if book_id and book_id.lower() != "none":
        try:
            book = Book.objects.get(pk=book_id, is_active=True)
        except (Book.DoesNotExist, ValueError):
            return HttpResponse("Invalid book ID", status=400)

        if book.cache_exists() and not cache.is_cache_expired(book):
            cache.refresh_book_metadata(book)
            return _stream_local_file(Path(book.cache_path()), title or book.title, want_download)

        if book.cache_exists() and cache.is_cache_expired(book):
            cache.remove_book_cache(book)

        if book.pdf_file and Path(book.pdf_file.path).is_file():
            local_pdf = cache.create_book_cache(book, book.pdf_file.path)
            if local_pdf and local_pdf.is_file():
                return _stream_local_file(local_pdf, title or book.title, want_download)

        if book.url and book.url.lower().endswith(".pdf"):
            raw = book.url

    if not raw or not books.is_safe_remote_book_url(raw):
        return HttpResponse("Invalid URL", status=400)

    if request.user.is_authenticated:
        try:
            UserLibraryItem.objects.update_or_create(
                user=request.user,
                item_type="book",
                url=raw,
                defaults={
                    "title": title or raw,
                    "field_slug": "",
                    "meta": {"source": source},
                },
            )
        except Exception:
            pass

    logger.info("read_remote_pdf -> raw=%s title=%s book_id=%s", raw, title, book_id or "none")

    # Try to use a cached local copy first.
    local_pdf = books.cache_remote_pdf(raw)
    if local_pdf and local_pdf.is_file():
        return _stream_local_file(local_pdf, title, want_download)

    resolved = books.resolve_openlibrary_pdf_url(raw)
    if resolved and resolved != raw:
        raw = resolved

    local_pdf = books.cache_remote_pdf(raw)
    if local_pdf and local_pdf.is_file():
        return _stream_local_file(local_pdf, title, want_download)

    alternative_url = None
    alternative_is_pdf = False

    try:
        from urllib.parse import urlparse

        origin = ""
        try:
            origin = f"{urlparse(raw).scheme}://{urlparse(raw).netloc}/"
        except Exception:
            origin = ""

        req_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": origin or "https://archive.org/",
        }

        stream_resp = requests.get(
            raw,
            timeout=90,
            stream=True,
            allow_redirects=True,
            headers=req_headers,
        )
        if stream_resp.status_code == 403 and "archive.org" in raw.lower():
            fallback = books.resolve_openlibrary_pdf_url(raw)
            if fallback and fallback != raw:
                stream_resp.close()
                raw = fallback
                if not books.is_safe_remote_book_url(raw):
                    return HttpResponse("Invalid URL", status=400)
                stream_resp = requests.get(
                    raw,
                    timeout=90,
                    stream=True,
                    allow_redirects=True,
                    headers=req_headers,
                )
        if stream_resp.status_code >= 400:
            stream_resp.close()
            if title:
                alternative_url, alternative_is_pdf = books.find_alternative_book_url(title)
                if alternative_url and alternative_url != raw:
                    if alternative_is_pdf:
                        return redirect(
                            f"{reverse('library:read_pdf')}?url={requests.utils.quote(alternative_url, safe='')}&title={requests.utils.quote(title, safe='')}&disposition={request.GET.get('disposition','')}"
                        )
                    return redirect(
                        f"{reverse('library:read_book')}?url={requests.utils.quote(alternative_url, safe='')}&title={requests.utils.quote(title, safe='')}&is_pdf=0"
                    )
            return HttpResponse(
                "Resource not available from the remote source. قد يكون الخادم منع الوصول أو لا يسمح بالعرض المباشر.",
                status=404,
                content_type="text/plain; charset=utf-8",
            )

        declared = (stream_resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        iterator = stream_resp.iter_content(chunk_size=65536)

        try:
            first_chunk = next(iterator)
        except StopIteration:
            stream_resp.close()
            return HttpResponse("Empty response from host", status=502)

        is_pdf = first_chunk[:4] == b"%PDF"
        if not is_pdf:
            stream_resp.close()
            if title:
                alternative_url, alternative_is_pdf = books.find_alternative_book_url(title)
                if alternative_url and alternative_url != raw:
                    if alternative_is_pdf:
                        alt_cached = books.cache_remote_pdf(alternative_url)
                        if alt_cached and alt_cached.is_file():
                            return _stream_local_file(alt_cached, title, want_download)
                        return redirect(
                            f"{reverse('library:read_pdf')}?url={requests.utils.quote(alternative_url, safe='')}&title={requests.utils.quote(title, safe='')}&disposition={request.GET.get('disposition','')}"
                        )
                    return redirect(
                        f"{reverse('library:read_book')}?url={requests.utils.quote(alternative_url, safe='')}&title={requests.utils.quote(title, safe='')}&is_pdf=0"
                    )
            return HttpResponse(
                "الخادم لم يُرجع ملف PDF صالحاً. حاول من مصدر آخر أو استخدم زر التحميل.",
                status=415,
                content_type="text/plain; charset=utf-8",
            )

        # Cache successful PDF responses locally for later reuse.
        temp_pdf = books.cached_pdf_path(raw).with_suffix(".tmp")
        try:
            with temp_pdf.open("wb") as out_file:
                out_file.write(first_chunk)
                for chunk in iterator:
                    if chunk:
                        out_file.write(chunk)
            if temp_pdf.stat().st_size > 1024:
                pdf_path = books.cached_pdf_path(raw)
                temp_pdf.rename(pdf_path)
                return _stream_local_file(pdf_path, title, want_download)
            temp_pdf.unlink(missing_ok=True)
        except Exception:
            temp_pdf.unlink(missing_ok=True)

        # Stream the PDF directly if caching unexpectedly failed.
        def stream_from_first():
            yield first_chunk
            for chunk in iterator:
                if chunk:
                    yield chunk
            stream_resp.close()

        out = StreamingHttpResponse(
            stream_from_first(),
            content_type="application/pdf",
        )
        fname = raw.split("/")[-1].split("?")[0][:120] or "document.pdf"
        if not fname.lower().endswith(".pdf"):
            fname = "document.pdf"
        disp = "attachment" if want_download else "inline"
        out["Content-Disposition"] = f'{disp}; filename="{fname}"'
        out["Cache-Control"] = "private, max-age=300"
        out["X-Content-Type-Options"] = "nosniff"
        return out
    except requests.RequestException:
        return HttpResponse("Failed to fetch document", status=502)


def download_book(request):
    """Try to download a book from Open Library / archive.org"""
    book_url = request.GET.get("url", "").strip()
    title = request.GET.get("title", "book").strip()
    
    if not book_url or not books.is_safe_remote_book_url(book_url):
        return HttpResponse("Invalid URL", status=400)
    
    # Try to resolve the PDF from Open Library work URL
    pdf_url = None
    
    # Extract work ID from URL: /works/OL...W
    import re
    match = re.search(r'/works/(OL\d+W)', book_url)
    if match:
        work_id = match.group(1)
        # Try to find archive.org ID via editions
        try:
            ed_url = f"https://openlibrary.org/works/{work_id}/editions.json"
            resp = requests.get(ed_url, headers=books.HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for entry in data.get('entries', [])[:50]:
                    ia_id = entry.get('ocaid') or entry.get('ia')
                    if ia_id:
                        # Try to resolve and check if accessible
                        test_url = books._archive_resolve_pdf(ia_id)
                        if books._is_url_accessible(test_url, timeout=5):
                            pdf_url = test_url
                            break
        except Exception:
            pass
    
    if pdf_url:
        # Redirect to our PDF reader with attachment disposition
        return redirect(f"{reverse('library:read_pdf')}?url={requests.utils.quote(pdf_url)}&title={requests.utils.quote(title)}&disposition=attachment")
    
    return HttpResponse(
        "⚠️ هذا الكتاب من Open Library غالباً لا يحتوي على نسخة PDF متاحة للتحميل.\n\n👈 جرب زرار 'معاينة' لقراءة الكتاب أونلاين من Open Library مجاناً.",
        status=404,
        content_type="text/plain; charset=utf-8"
    )

