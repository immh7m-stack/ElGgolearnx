from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

import requests

from apps.roadmaps.models import Field

from .models import DownloadJob, UserLibraryItem, UserPlaylist
from .playlist_utils import record_playlist_open
from .services import books, download, youtube


@login_required
def search_page(request):
    query = request.GET.get("q", "").strip()
    search_type = request.GET.get("type", "courses")
    playlists = []
    book_results = []

    if query:
        if search_type in ("courses", "all"):
            playlists = youtube.search_playlists(query, max_results=8)
        if search_type in ("books", "all"):
            book_results = books.search_books(query, limit=10)

    quick_topics = ["Python", "JavaScript", "React", "Machine Learning", "Cybersecurity", "SQL"]
    return render(
        request,
        "library/search.html",
        {
            "query": query,
            "search_type": search_type,
            "playlists": playlists,
            "book_results": book_results,
            "quick_topics": quick_topics,
        },
    )


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
    return render(
        request,
        "library/history.html",
        {"playlists": playlists},
    )


@login_required
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
    return render(
        request,
        "library/watch.html",
        {
            "playlist_url": url,
            "title": title,
            "videos": videos,
            "hero_thumb": thumb,
            "playlist_id": playlist_id or youtube.extract_playlist_id_from_url(url or ""),
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


@login_required
@require_POST
def start_download_view(request):
    url = request.POST.get("url", "").strip()
    title = request.POST.get("title", "Course")
    single_video = request.POST.get("video_id", "").strip()
    if single_video:
        url = f"https://www.youtube.com/watch?v={single_video}"
        title = request.POST.get("video_title", title)
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


@login_required
def read_remote_pdf(request):
    """Stream PDFs through the app. Use ?disposition=attachment to force download."""
    raw = request.GET.get("url", "").strip()
    want_download = request.GET.get("disposition", "").lower() == "attachment"
    if not raw or not books.is_safe_remote_book_url(raw):
        return HttpResponse("Invalid URL", status=400)
    try:
        from urllib.parse import urlparse

        origin = ""
        try:
            origin = f"{urlparse(raw).scheme}://{urlparse(raw).netloc}/"
        except Exception:
            origin = ""

        req_headers = {
            **books.HEADERS,
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        }
        if origin:
            req_headers["Referer"] = origin

        stream_resp = requests.get(
            raw,
            timeout=90,
            stream=True,
            allow_redirects=True,
            headers=req_headers,
        )
        if stream_resp.status_code >= 400:
            stream_resp.close()
            return HttpResponse("Resource not available", status=404)

        declared = (stream_resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        iterator = stream_resp.iter_content(chunk_size=65536)

        try:
            first_chunk = next(iterator)
        except StopIteration:
            stream_resp.close()
            return HttpResponse("Empty response from host", status=502)

        is_pdf = first_chunk[:4] == b"%PDF"
        if not is_pdf:
            ctype_lower = declared
            allowed = (
                "application/pdf",
                "application/octet-stream",
                "binary/octet-stream",
                "application/x-pdf",
                "text/plain",
                "",
            )
            if ctype_lower not in allowed and ".pdf" not in raw.lower():
                stream_resp.close()
                return HttpResponse(
                    "الخادم لم يُرجع ملف PDF صالحاً. قد يكون الرابط يحتاج تسجيل دخول أو غير مباشر.",
                    status=415,
                    content_type="text/plain; charset=utf-8",
                )

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
