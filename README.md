# ElGgolearn

منصة تعليمية مفتوحة المصدر للوطن العربي — مسارات تقنية من Junior إلى Senior مع كورسات يوتيوب موثّقة ومشاريع GitHub.

## التشغيل السريع

```bash
cd e:\101
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py load_roadmaps
python manage.py createsuperuser
python manage.py runserver
```

افتح: http://127.0.0.1:8001/

## التشغيل عبر Docker

يمكنك استخدام إعداد Docker الموجود في `docker/docker-compose.yml` و`docker/Dockerfile` لتشغيل المشروع داخل حاوية.

```bash
docker compose -f docker/docker-compose.yml up --build
```

لمزيد من التفاصيل، راجع `docker/README.md`.

لإيقاف الحاوية:

```bash
docker compose -f docker/docker-compose.yml down
```

## الصفحات الرئيسية

| المسار | الوظيفة |
|--------|---------|
| `/fields/` | Built-in roadmaps (Junior / Mid / Senior) |
| `/library/search/` | بحث YouTube + كتب + تحقق Gemini |
| `/library/sites/` | مواقع تعليمية موثّقة |
| `/library/my/` | قوائمك المحفوظة + التحميلات |
| `/library/history/` | سجل البحث والإنجازات |
| `/dashboard/` | لوحة التقدم |
| `/admin/` | إدارة الكورسات، الكتب، المواقع |

## الأوامر المهمة

| الأمر | الوصف |
|--------|--------|
| `python manage.py load_roadmaps` | تحميل ملفات JSON من `data/roadmaps/` |
| `python manage.py seed_sites` | مواقع تعليمية (W3Schools, GitHub, …) |
| `python manage.py runserver` | تشغيل السيرفر المحلي |

## API Keys (`.env`)

```
GEMINI_API_KEY=...    # من https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.5-flash   # عند 404 جرّب gemini-flash-latest أو احذف السطر ليستخدم المشروع الافتراضي
YOUTUBE_API_KEY=...   # بحث playlists (موصى به)
```

## هيكل المشروع

- `apps/roadmaps` — المجالات والمسارات والمهارات
- `apps/progress` — تتبع التقدم والمشاريع
- `apps/chatbot` — مساعد Gemini (يتطلب `GEMINI_API_KEY`)
- `apps/accounts` — الملف الشخصي والإحصائيات
- `data/roadmaps/*.json` — بيانات المسارات

## API

- `GET /api/fields/` — قائمة المجالات
- `GET /api/fields/{slug}/tracks/{level}/` — تفاصيل المسار
- `POST /api/progress/skill/{id}/` — تبديل حالة المهارة
- `POST /api/chat/start/` — بدء جلسة محادثة

## الترخيص

مفتوح المصدر — المساهمات مرحّب بها (انظر CONTRIBUTING.md).
# ElGgolearnx
