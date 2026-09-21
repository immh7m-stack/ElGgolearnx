from django.db import models


class Field(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, default="📚")
    color = models.CharField(max_length=7, default="#6366f1")
    description_ar = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order_rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order_rank", "slug"]

    def __str__(self):
        return self.name_ar


class Track(models.Model):
    LEVEL_CHOICES = [
        ("junior", "Junior"),
        ("mid", "Mid"),
        ("senior", "Senior"),
    ]
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name="tracks")
    career_level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    goal_ar = models.TextField(blank=True)
    goal_en = models.TextField(blank=True)
    duration_months = models.PositiveIntegerField(default=3)
    projects_needed = models.PositiveIntegerField(default=0)
    books_required = models.PositiveIntegerField(
        default=0, help_text="Minimum books to read before completing this level"
    )
    projects_to_advance = models.PositiveIntegerField(
        default=0, help_text="Projects needed to unlock next level (e.g. 40 for Junior→Mid)"
    )
    can_do_ar = models.JSONField(default=list, blank=True)
    can_do_en = models.JSONField(default=list, blank=True)
    ready_when_ar = models.TextField(blank=True)
    ready_when_en = models.TextField(blank=True)
    job_requirements = models.JSONField(default=list, blank=True)
    roadmap_intro = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional: skills_ar/en, tips_ar/en lists for track intro / notes.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("field", "career_level")]
        ordering = ["field", "career_level"]

    def __str__(self):
        return f"{self.field.slug} — {self.career_level}"


class Playlist(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="playlists")
    lang = models.CharField(max_length=5, choices=[("ar", "ar"), ("en", "en")], default="en")
    youtube_url = models.URLField(max_length=500)
    playlist_id = models.CharField(max_length=50, blank=True)
    channel_name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=500, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    role_label = models.CharField(max_length=80, blank=True, help_text="e.g. Core course, Projects")
    order_num = models.PositiveIntegerField(default=0)
    verified_year = models.PositiveIntegerField(null=True, blank=True)
    approx_views = models.BigIntegerField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    last_verified = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["order_num", "id"]

    def __str__(self):
        return f"{self.track} [{self.lang}]"


class Module(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="modules")
    order_num = models.PositiveIntegerField(default=1)
    title_ar = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True)
    summary_ar = models.TextField(blank=True)
    summary_en = models.TextField(blank=True)
    duration_days = models.PositiveIntegerField(default=7)
    eng_query = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=10, default="📦")

    class Meta:
        ordering = ["order_num"]
        unique_together = [("track", "order_num")]

    def __str__(self):
        return self.title_ar


class Skill(models.Model):
    TYPE_CHOICES = [
        ("concept", "Concept"),
        ("tool", "Tool"),
        ("practice", "Practice"),
    ]
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="skills")
    external_id = models.CharField(max_length=50, blank=True)
    order_num = models.PositiveIntegerField(default=1)
    title_ar = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True)
    description_ar = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    duration_days = models.PositiveIntegerField(default=1)
    skill_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="concept")
    resources = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order_num"]

    def __str__(self):
        return self.title_ar


class Project(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="projects")
    external_id = models.CharField(max_length=50, blank=True)
    order_num = models.PositiveIntegerField(default=1)
    title_ar = models.CharField(max_length=300)
    title_en = models.CharField(max_length=300, blank=True)
    description_ar = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(default=1)
    estimated_days = models.PositiveIntegerField(default=3)
    skills_covered = models.JSONField(default=list, blank=True)
    example_repo = models.URLField(max_length=500, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    bonus_features = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["order_num"]

    def __str__(self):
        return self.title_ar
