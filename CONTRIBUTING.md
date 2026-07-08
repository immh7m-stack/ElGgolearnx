# المساهمة في ElGgolearn

## كيف تضيف مساراً جديداً؟

1. انسخ `data/roadmaps/_template.json`
2. سمّه بـ slug المجال (مثال: `golang.json`)
3. أضف على الأقل:
   - 3 وحدات (modules) لكل مستوى junior
   - 3 مشاريع لـ junior، 2 لـ mid، 1 لـ senior
4. تأكد أن روابط يوتيوب تعمل
5. شغّل `python manage.py load_roadmaps`
6. افتح Pull Request

## معايير قبول الكورسات

- سنة النشر 2022 أو أحدث
- +100k مشاهدة عربي، +500k إنجليزي
- يغطي مفاهيم المستوى
- لا كورسات مدفوعة أو ناقصة

## مخطط JSON

راجع `ELGGOLEARN_DOCS.md` القسم 5 — `$schema: elggolearn-roadmap-v1`
