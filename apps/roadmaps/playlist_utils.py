from apps.library.services import youtube

from .models import Playlist


def attach_playlist_meta(playlists: list[Playlist]) -> list[Playlist]:
    """Fill missing thumbnails/view counts from YouTube API."""
    ids = [p.playlist_id for p in playlists if p.playlist_id and not p.thumbnail_url]
    if not ids:
        ids = [p.playlist_id for p in playlists if p.playlist_id]
    if not ids:
        return playlists
    meta = {m["playlist_id"]: m for m in youtube.enrich_playlists(ids)}
    for p in playlists:
        m = meta.get(p.playlist_id)
        if not m:
            continue
        if not p.thumbnail_url:
            p.thumbnail_url = m.get("thumbnail", "")
        if not p.approx_views and m.get("view_count"):
            p.approx_views = m["view_count"]
        if not p.channel_name:
            p.channel_name = m.get("channel", "")
    return playlists
