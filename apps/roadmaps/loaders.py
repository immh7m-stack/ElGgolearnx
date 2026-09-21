import json
from pathlib import Path

from django.conf import settings
from django.db import transaction

from apps.library.services import youtube

from .models import Field, Module, Playlist, Project, Skill, Track


def load_roadmap_from_file(path: Path) -> Field:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    field, _ = Field.objects.update_or_create(
        slug=meta["slug"],
        defaults={
            "name_ar": meta["name_ar"],
            "name_en": meta["name_en"],
            "icon": meta.get("icon", "📚"),
            "color": meta.get("color", "#6366f1"),
            "description_ar": meta.get("description_ar", ""),
            "description_en": meta.get("description_en", ""),
            "is_active": True,
        },
    )

    for level, track_data in data.get("career_tracks", {}).items():
        track, _ = Track.objects.update_or_create(
            field=field,
            career_level=level,
            defaults={
                "goal_ar": track_data.get("goal_ar", ""),
                "goal_en": track_data.get("goal_en", ""),
                "duration_months": track_data.get("duration_months", 3),
                "projects_needed": track_data.get("projects_required", 0),
                "books_required": track_data.get("books_required", 0),
                "projects_to_advance": track_data.get("projects_to_advance", 0),
                "can_do_ar": track_data.get("can_do", {}).get("ar", []),
                "can_do_en": track_data.get("can_do", {}).get("en", []),
                "ready_when_ar": track_data.get("ready_when_ar", ""),
                "ready_when_en": track_data.get("ready_when_en", ""),
                "job_requirements": track_data.get("job_requirements", []),
                "roadmap_intro": track_data.get("roadmap_intro", {}),
            },
        )

        track.playlists.all().delete()
        curated = track_data.get("curated_playlists", [])
        if curated:
            ids = [p["playlist_id"] for p in curated if p.get("playlist_id")]
            meta_map = {m["playlist_id"]: m for m in youtube.enrich_playlists(ids)}
            for p in sorted(curated, key=lambda x: x.get("order", 0)):
                pid = p.get("playlist_id", "")
                meta = meta_map.get(pid, {})
                Playlist.objects.create(
                    track=track,
                    lang=p.get("lang", "en"),
                    youtube_url=p.get("youtube_url") or f"https://www.youtube.com/playlist?list={pid}",
                    playlist_id=pid,
                    channel_name=p.get("channel") or meta.get("channel", ""),
                    title=p.get("title") or meta.get("title", ""),
                    thumbnail_url=meta.get("thumbnail", ""),
                    role_label=p.get("role", ""),
                    order_num=p.get("order", 0),
                    approx_views=meta.get("view_count") or p.get("approx_views"),
                    verified_year=p.get("verified_year"),
                    is_primary=bool(p.get("is_primary")),
                )
        else:
            for lang, playlists in track_data.get("playlists", {}).items():
                primary = playlists.get("primary", playlists) if isinstance(playlists, dict) else {}
                if primary and "youtube_url" in primary:
                    pid = primary.get("playlist_id", "")
                    enriched = youtube.enrich_playlists([pid]) if pid else []
                    meta = enriched[0] if enriched else {}
                    Playlist.objects.create(
                        track=track,
                        lang=lang,
                        youtube_url=primary["youtube_url"],
                        playlist_id=pid,
                        channel_name=primary.get("channel", meta.get("channel", "")),
                        title=primary.get("title", meta.get("title", "")),
                        thumbnail_url=meta.get("thumbnail", ""),
                        verified_year=primary.get("verified_year"),
                        approx_views=primary.get("approx_views") or meta.get("view_count"),
                        is_primary=True,
                        order_num=1,
                    )

        track.modules.all().delete()
        for mod in track_data.get("modules", []):
            module = Module.objects.create(
                track=track,
                order_num=mod.get("order", mod.get("id", 1)),
                title_ar=mod.get("title_ar") or mod.get("title_en", "Module"),
                title_en=mod.get("title_en", ""),
                summary_ar=mod.get("summary_ar", ""),
                summary_en=mod.get("summary_en", ""),
                duration_days=mod.get("duration_days", 7),
                eng_query=mod.get("eng_query", ""),
                icon=mod.get("icon", "📦"),
            )
            for sk in mod.get("skills", []):
                Skill.objects.create(
                    module=module,
                    external_id=str(sk.get("id", "")),
                    order_num=sk.get("order", 1),
                    title_ar=sk.get("title_ar") or sk.get("title_en", "Skill"),
                    title_en=sk.get("title_en", ""),
                    description_ar=sk.get("description_ar", ""),
                    description_en=sk.get("description_en", ""),
                    duration_days=sk.get("duration_days", 1),
                    skill_type=sk.get("skill_type", "concept"),
                    resources=sk.get("resources", {}),
                )

        track.projects.all().delete()
        combined_projects = list(track_data.get("required_projects", [])) + list(
            track_data.get("suggested_projects", [])
        )
        for proj in combined_projects:
            Project.objects.create(
                track=track,
                external_id=str(proj.get("id", "")),
                order_num=proj.get("order", 1),
                title_ar=proj["title_ar"],
                title_en=proj.get("title_en", ""),
                description_ar=proj.get("description_ar", ""),
                description_en=proj.get("description_en", ""),
                difficulty=proj.get("difficulty", 1),
                estimated_days=proj.get("estimated_days", 3),
                skills_covered=proj.get("skills_covered", []),
                example_repo=proj.get("example_repo", ""),
                requirements=proj.get("requirements", []),
                bonus_features=proj.get("bonus_features", []),
            )

    return field


def load_all_roadmaps(directory: Path | None = None) -> list[Field]:
    directory = directory or Path(settings.ROADMAPS_DATA_DIR)
    loaded = []
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_"):
            continue
        with transaction.atomic():
            loaded.append(load_roadmap_from_file(path))
    return loaded
