import json
from pathlib import Path

STUBS = [
    ("frontend", "واجهات الويب", "Frontend", "🌐", "#61dafb"),
    ("machine_learning", "تعلم الآلة", "Machine Learning", "🤖", "#10b981"),
    ("deep_learning", "التعلم العميق", "Deep Learning", "🧠", "#8b5cf6"),
    ("cybersecurity", "الأمن السيبراني", "Cybersecurity", "🔐", "#ef4444"),
    ("backend_node", "Node.js Backend", "Node.js Backend", "⚡", "#339933"),
    ("data_science", "علم البيانات", "Data Science", "📊", "#0ea5e9"),
    ("mobile_flutter", "Flutter", "Mobile Flutter", "📱", "#02569b"),
    ("devops", "DevOps", "DevOps", "☁️", "#f97316"),
    ("digital_marketing", "التسويق الرقمي", "Digital Marketing", "📈", "#ec4899"),
]

PLAYLIST = {
    "youtube_url": "https://www.youtube.com/playlist?list=PLDoPjvoNmBAyE_gei5d18qkfIe-Z8mocs",
    "playlist_id": "PLDoPjvoNmBAyE_gei5d18qkfIe-Z8mocs",
    "channel": "Elzero Web School",
    "title": "Placeholder Playlist",
    "approx_views": 100000,
    "verified_year": 2024,
}


def make_track(level, months, projects, name_ar, name_en):
    return {
        "goal_ar": f"إتقان مستوى {level}",
        "goal_en": f"Master {level} level",
        "duration_months": months,
        "projects_required": projects,
        "can_do": {"ar": ["يتعلم بشكل مستقل"], "en": ["Learn independently"]},
        "job_requirements": [],
        "playlists": {"ar": {"primary": PLAYLIST}},
        "modules": [
            {
                "id": 1,
                "order": 1,
                "title_ar": f"أساسيات {name_ar}",
                "title_en": f"{name_en} fundamentals",
                "summary_ar": "مقدمة",
                "summary_en": "Introduction",
                "duration_days": 14,
                "icon": "📦",
                "eng_query": name_en,
                "skills": [
                    {
                        "id": f"{level}_1_1",
                        "order": 1,
                        "title_ar": "المفاهيم الأساسية",
                        "title_en": "Core concepts",
                        "description_ar": "فهم الأساسيات",
                        "description_en": "Understand basics",
                        "duration_days": 3,
                        "skill_type": "concept",
                        "resources": {"docs": [], "free_books": [], "practice_urls": []},
                    }
                ],
            }
        ],
        "required_projects": [
            {
                "id": f"{level}p1",
                "order": 1,
                "title_ar": f"مشروع {level}",
                "title_en": f"{level} project",
                "description_ar": "مشروع تطبيقي على GitHub",
                "description_en": "Hands-on GitHub project",
                "difficulty": 2,
                "estimated_days": 5,
                "skills_covered": [],
                "requirements": ["رفع على GitHub"],
                "bonus_features": [],
                "example_repo": "",
            }
        ],
    }


out = Path(__file__).resolve().parent.parent / "roadmaps"
for slug, name_ar, name_en, icon, color in STUBS:
    data = {
        "$schema": "elggolearn-roadmap-v1",
        "meta": {
            "slug": slug,
            "name_ar": name_ar,
            "name_en": name_en,
            "icon": icon,
            "color": color,
            "description_ar": name_ar,
            "description_en": name_en,
            "last_updated": "2025-01-01",
            "contributors": [],
        },
        "career_tracks": {
            "junior": make_track("junior", 3, 3, name_ar, name_en),
            "mid": make_track("mid", 6, 2, name_ar, name_en),
            "senior": make_track("senior", 12, 1, name_ar, name_en),
        },
    }
    (out / f"{slug}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", slug)
