"""Background playlist download via yt-dlp."""
from __future__ import annotations

import re
import shutil
import threading
from pathlib import Path

from django.conf import settings


def _sanitize(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|\n\r\t]', "", name)
    return clean.strip().replace(" ", "_")[:60] or "course"


def job_download_dir(job) -> Path:
    """Directory where this job's files are stored (may not exist)."""
    base = Path(settings.MEDIA_ROOT) / "downloads" / str(job.user_id)
    return base / _sanitize(job.title)


def cleanup_job_files(job) -> None:
    """Remove on-disk folder for this job title (partial or complete)."""
    path = job_download_dir(job)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    if getattr(job, "file_path", None):
        fp = Path(job.file_path)
        if fp.is_dir() and fp.exists():
            shutil.rmtree(fp, ignore_errors=True)


def _entry_bytes_approx(entry: dict) -> int:
    if not entry:
        return 0
    fs = entry.get("filesize") or entry.get("filesize_approx")
    if fs:
        return int(fs)
    best = 0
    for f in entry.get("formats") or []:
        s = f.get("filesize") or f.get("filesize_approx") or 0
        best = max(best, int(s) if s else 0)
    return best


def estimate_download_bytes(source_url: str, *, max_sample: int = 50) -> int | None:
    """
    Rough total size using yt-dlp metadata (matches ~720p mp4 merge intent).
    Large playlists: extrapolate from first ``max_sample`` entries.
    """
    try:
        import yt_dlp

        opts = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": False,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(source_url, download=False)
    except Exception:
        return None

    if not info:
        return None

    entries = [e for e in (info.get("entries") or []) if e]
    if not entries:
        b = _entry_bytes_approx(info)
        return b if b > 0 else None

    n = len(entries)
    sample = entries[:max_sample]
    sample_sum = sum(_entry_bytes_approx(e) for e in sample)
    if sample_sum <= 0:
        return None
    if n > len(sample):
        total = int(sample_sum * (n / len(sample)))
    else:
        total = sample_sum
    return total if total > 0 else None


def _job_cancelled(job_id: int) -> bool:
    from apps.library.models import DownloadJob

    return DownloadJob.objects.filter(pk=job_id, status="cancelled").exists()


def start_download(job_id: int) -> None:
    """Run download in background thread."""
    from apps.library.models import DownloadJob

    class _Cancelled(Exception):
        pass

    def _run():
        job = DownloadJob.objects.get(pk=job_id)
        if _job_cancelled(job_id):
            return
        job.status = "running"
        job.save(update_fields=["status", "updated_at"])
        base = settings.MEDIA_ROOT / "downloads"
        base.mkdir(parents=True, exist_ok=True)
        folder = _sanitize(job.title)
        save_path = base / str(job.user_id) / folder
        save_path.mkdir(parents=True, exist_ok=True)

        try:
            if _job_cancelled(job_id):
                cleanup_job_files(job)
                return
            est = estimate_download_bytes(job.source_url)
            if est is not None:
                DownloadJob.objects.filter(pk=job_id).update(estimated_bytes=est)
            if _job_cancelled(job_id):
                cleanup_job_files(job)
                return

            import yt_dlp

            def hook(d):
                if _job_cancelled(job_id):
                    raise _Cancelled()
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    done = d.get("downloaded_bytes") or 0
                    if total:
                        pct = int(done * 100 / total)
                        DownloadJob.objects.filter(pk=job_id).update(
                            progress_pct=min(pct, 99), status="running"
                        )

            opts = {
                "format": "bestvideo[height<=720][ext=mp4]+bestaudio/best[ext=mp4]/best",
                "outtmpl": str(save_path / "%(playlist_index)02d - %(title).50s.%(ext)s"),
                "noplaylist": False,
                "progress_hooks": [hook],
                "quiet": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([job.source_url])
            if _job_cancelled(job_id):
                return
            DownloadJob.objects.filter(pk=job_id).update(
                status="done", progress_pct=100, file_path=str(save_path)
            )
        except _Cancelled:
            cleanup_job_files(job)
            DownloadJob.objects.filter(pk=job_id).update(
                status="cancelled", progress_pct=0, error_message="", file_path=""
            )
        except Exception as e:
            msg = str(e)[:500]
            DownloadJob.objects.filter(pk=job_id).update(status="failed", error_message=msg)

    threading.Thread(target=_run, daemon=True).start()
