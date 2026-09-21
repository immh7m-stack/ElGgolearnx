from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.accounts.models import LearnerStats
from apps.library.playlist_utils import record_playlist_open
from apps.library.services import youtube as yt
from apps.progress.models import UserSkillProgress

from .models import Field, Module, Track
from .playlist_utils import attach_playlist_meta


def _user_lang(request):
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        return request.user.profile.preferred_lang
    return request.GET.get("lang", "en")


def fields_list(request):
    fields = Field.objects.filter(is_active=True).prefetch_related("tracks")
    q = request.GET.get("q", "").strip()
    if q:
        fields = fields.filter(
            Q(name_ar__icontains=q) | Q(name_en__icontains=q) | Q(slug__icontains=q)
        )
    lang = _user_lang(request)
    return render(request, "roadmaps/fields.html", {"fields": fields, "lang": lang, "q": q})


def track_detail(request, slug, level):
    field = get_object_or_404(Field, slug=slug, is_active=True)
    track = get_object_or_404(Track, field=field, career_level=level)
    modules = track.modules.prefetch_related("skills").all()
    projects = track.projects.all()
    playlists = attach_playlist_meta(list(track.playlists.all()))
    playlist = next((p for p in playlists if p.is_primary), None) or (playlists[0] if playlists else None)

    done_skill_ids = set()
    if request.user.is_authenticated:
        done_skill_ids = set(
            UserSkillProgress.objects.filter(
                user=request.user, is_done=True, skill__module__track=track
            ).values_list("skill_id", flat=True)
        )

    total_skills = sum(m.skills.count() for m in modules)
    done_count = len(done_skill_ids)
    progress_pct = int((done_count / total_skills) * 100) if total_skills else 0

    if request.user.is_authenticated:
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        stats.current_field_slug = field.slug
        stats.current_level = track.career_level
        stats.save(update_fields=["current_field_slug", "current_level"])

    lang = _user_lang(request)
    return render(
        request,
        "roadmaps/track.html",
        {
            "field": field,
            "track": track,
            "modules": modules,
            "projects": projects,
            "playlist": playlist,
            "playlists": playlists,
            "done_skill_ids": done_skill_ids,
            "progress_pct": progress_pct,
            "lang": lang,
        },
    )


def module_detail(request, slug, level, order):
    field = get_object_or_404(Field, slug=slug, is_active=True)
    track = get_object_or_404(Track, field=field, career_level=level)
    module = get_object_or_404(Module, track=track, order_num=order)
    skills = module.skills.all()
    playlist = track.playlists.filter(is_primary=True).first() or track.playlists.first()
    done_skill_ids = set()
    if request.user.is_authenticated:
        done_skill_ids = set(
            UserSkillProgress.objects.filter(
                user=request.user, is_done=True, skill__module__track=track
            ).values_list("skill_id", flat=True)
        )
    lang = _user_lang(request)
    if request.user.is_authenticated:
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        stats.current_field_slug = field.slug
        stats.current_level = track.career_level
        stats.save(update_fields=["current_field_slug", "current_level"])
    return render(
        request,
        "roadmaps/module.html",
        {
            "field": field,
            "track": track,
            "module": module,
            "skills": skills,
            "playlist": playlist,
            "lang": lang,
            "done_skill_ids": done_skill_ids,
        },
    )


@login_required
def watch_playlist(request, slug, level):
    field = get_object_or_404(Field, slug=slug, is_active=True)
    track = get_object_or_404(Track, field=field, career_level=level)
    playlist = track.playlists.filter(is_primary=True).first() or track.playlists.first()
    if not playlist:
        raise Http404("No playlist for this track")
    videos = yt.get_playlist_videos(playlist.youtube_url) if playlist.youtube_url else []
    thumb = playlist.thumbnail_url or ""
    title = playlist.title or ""
    if playlist.playlist_id:
        meta = yt.get_playlist_meta(playlist.playlist_id)
        if meta:
            thumb = thumb or meta.get("thumbnail", "")
            title = title or meta.get("title", field.name_ar)
    record_playlist_open(
        request.user,
        playlist.youtube_url,
        title,
        playlist.playlist_id or "",
        thumb,
    )
    lang = _user_lang(request)
    return render(
        request,
        "roadmaps/watch.html",
        {
            "field": field,
            "track": track,
            "playlist": playlist,
            "videos": videos,
            "watch_title": title,
            "hero_thumb": thumb,
            "lang": lang,
        },
    )
