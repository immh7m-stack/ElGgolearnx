"""User playlist history helpers (library + roadmaps)."""

from django.utils import timezone

from .models import UserPlaylist
from .services import youtube


def record_playlist_open(user, url: str, title: str, playlist_id: str = "", thumbnail: str = "") -> None:
    """Ensure a playlist appears in History after the user opens the watch page."""
    if user is None or getattr(user, "is_authenticated", False) is False:
        return

    canon, pid = youtube.canonical_playlist_url(url, playlist_id or "")
    pid = pid or youtube.extract_playlist_id_from_url(url)
    if not (canon or url).strip():
        return
    base_url = canon or url.strip()
    title = (title or "Playlist").strip()[:500]
    now = timezone.now()
    existing = None
    if pid:
        existing = (
            UserPlaylist.objects.filter(user=user, playlist_id=pid).first()
            or UserPlaylist.objects.filter(user=user, youtube_url__icontains=f"list={pid}").first()
        )
    if not existing and url:
        existing = UserPlaylist.objects.filter(user=user, youtube_url=url.strip()).first()
    if existing:
        existing.title = title or existing.title
        existing.thumbnail = thumbnail or existing.thumbnail
        existing.youtube_url = base_url
        if pid:
            existing.playlist_id = pid
        existing.last_opened_at = now
        existing.save(
            update_fields=[
                "title",
                "thumbnail",
                "youtube_url",
                "playlist_id",
                "last_opened_at",
            ]
        )
        return
    UserPlaylist.objects.create(
        user=user,
        title=title,
        youtube_url=base_url,
        playlist_id=pid,
        thumbnail=thumbnail,
        is_saved_explicit=False,
        last_opened_at=now,
    )
