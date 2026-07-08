"""YouTube Data API v3 — playlist search sorted by views."""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)
PL_RE = re.compile(r"^PL[\w-]+$")
LIST_RE = re.compile(r"(?:^|[?&])list=([^&]+)", re.I)


def extract_playlist_id_from_url(url: str) -> str:
    """Return YouTube playlist id from playlist or watch URL."""
    if not url:
        return ""
    s = url.strip()
    m = LIST_RE.search(s)
    if m:
        parsed = urllib.parse.unquote(m.group(1).strip())
        if parsed and len(parsed) >= 10:
            return parsed
    return ""


def canonical_playlist_url(url: str, playlist_id: str = "") -> tuple[str, str]:
    """Normalize to https://www.youtube.com/playlist?list=PL... when possible."""
    pid = (playlist_id or "").strip() or extract_playlist_id_from_url(url)
    if pid:
        return f"https://www.youtube.com/playlist?list={pid}", pid
    return (url.strip() if url else "", pid)


def _api_key() -> str:
    return (getattr(settings, "YOUTUBE_API_KEY", "") or "").strip()


def _api_get(path: str, params: dict) -> dict:
    key = _api_key()
    if not key:
        return {}
    params = {k: v for k, v in params.items() if v is not None}
    params["key"] = key
    url = f"https://www.googleapis.com/youtube/v3/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def enrich_playlists(playlist_ids: list[str]) -> list[dict]:
    valid = [pid for pid in playlist_ids if pid and PL_RE.match(pid)]
    if not valid or not _api_key():
        return []
    out = []
    for i in range(0, len(valid), 20):
        chunk = valid[i : i + 20]
        try:
            data = _api_get(
                "playlists",
                {"part": "snippet,contentDetails", "id": ",".join(chunk)},
            )
        except Exception as e:
            logger.warning("playlists.list failed: %s", e)
            continue
        for item in data.get("items", []):
            pid = item["id"]
            snip = item.get("snippet", {})
            thumbs = snip.get("thumbnails", {})
            thumb = (
                thumbs.get("maxres", {}).get("url")
                or thumbs.get("high", {}).get("url")
                or thumbs.get("medium", {}).get("url")
                or ""
            )
            out.append({
                "playlist_id": pid,
                "title": snip.get("title", ""),
                "channel": snip.get("channelTitle", ""),
                "thumbnail": thumb,
                "url": f"https://www.youtube.com/playlist?list={pid}",
                "view_count": 0,
                "video_count": int(item.get("contentDetails", {}).get("itemCount", 0)),
            })
    # Optional: fetch view counts via search is unreliable; keep order from search
    return out


def search_playlists(query: str, max_results: int = 8) -> list[dict]:
    key = _api_key()
    if not key:
        logger.warning("YOUTUBE_API_KEY missing")
        return _scrape_playlists(query, max_results)

    try:
        data = _api_get(
            "search",
            {
                "part": "snippet",
                "q": f"{query} full course",
                "type": "playlist",
                "maxResults": min(max_results * 2, 25),
                "order": "relevance",
            },
        )
        ids = []
        for item in data.get("items", []):
            pid = item.get("id", {}).get("playlistId")
            if pid and PL_RE.match(pid):
                ids.append(pid)
        if not ids:
            return _scrape_playlists(query, max_results)
        enriched = enrich_playlists(ids)
        return enriched[:max_results] if enriched else _fallback_from_search_items(data, max_results)
    except Exception as e:
        logger.exception("YouTube search failed: %s", e)
        return _scrape_playlists(query, max_results)


def _fallback_from_search_items(data: dict, max_results: int) -> list[dict]:
    out = []
    for item in data.get("items", []):
        pid = item.get("id", {}).get("playlistId")
        if not pid:
            continue
        snip = item.get("snippet", {})
        thumbs = snip.get("thumbnails", {})
        thumb = thumbs.get("high", {}).get("url") or thumbs.get("medium", {}).get("url") or ""
        out.append({
            "playlist_id": pid,
            "title": snip.get("title", ""),
            "channel": snip.get("channelTitle", ""),
            "thumbnail": thumb,
            "url": f"https://www.youtube.com/playlist?list={pid}",
            "view_count": 0,
            "video_count": 0,
        })
        if len(out) >= max_results:
            break
    return out


def _scrape_playlists(query: str, max_results: int) -> list[dict]:
    try:
        enc = urllib.parse.quote(f"{query} full course playlist")
        url = f"https://www.youtube.com/results?search_query={enc}&sp=EgIQAw%253D%253D"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        seen, ids = set(), []
        for m in re.finditer(r'"playlistId":"(PL[\w-]+)"', html):
            pid = m.group(1)
            if pid in seen:
                continue
            seen.add(pid)
            ids.append(pid)
            if len(ids) >= max_results:
                break
        if ids:
            enriched = enrich_playlists(ids)
            if enriched:
                return enriched
        return [
            {
                "playlist_id": pid,
                "title": query,
                "channel": "",
                "thumbnail": "",
                "url": f"https://www.youtube.com/playlist?list={pid}",
                "view_count": 0,
                "video_count": 0,
            }
            for pid in ids
        ]
    except Exception as e:
        logger.exception("Scrape failed: %s", e)
        return []


def get_playlist_meta(playlist_id: str) -> dict | None:
    rows = enrich_playlists([playlist_id])
    return rows[0] if rows else None


def get_playlist_videos(playlist_url: str) -> list[dict]:
    if "list=" not in playlist_url:
        return []
    playlist_id = playlist_url.split("list=")[1].split("&")[0]
    key = _api_key()
    if key and PL_RE.match(playlist_id):
        videos = _videos_via_api(playlist_id, key)
        if videos:
            return videos
    return _videos_via_ytdlp(playlist_url)


def _videos_via_api(playlist_id: str, key: str) -> list[dict]:
    try:
        data = _api_get(
            "playlistItems",
            {"part": "snippet", "playlistId": playlist_id, "maxResults": 50},
        )
        videos = []
        for item in data.get("items", []):
            snip = item.get("snippet", {})
            vid = snip.get("resourceId", {}).get("videoId")
            if not vid:
                continue
            thumbs = snip.get("thumbnails", {})
            thumb = thumbs.get("medium", {}).get("url") or f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"
            videos.append({"title": snip.get("title", ""), "video_id": vid, "thumbnail": thumb})
        return videos
    except Exception:
        return []


def _videos_via_ytdlp(playlist_url: str) -> list[dict]:
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        videos = []
        for entry in (info.get("entries") or [])[:50]:
            vid = entry.get("id", "")
            if vid:
                videos.append({
                    "title": entry.get("title", ""),
                    "video_id": vid,
                    "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg",
                })
        return videos
    except Exception:
        return []
