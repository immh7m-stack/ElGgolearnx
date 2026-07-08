from django.conf import settings
from django.db import models


class EducationalSite(models.Model):
    CATEGORY_CHOICES = [
        ("courses", "Courses & Tutorials"),
        ("practice", "Practice & Challenges"),
        ("community", "Community & Q&A"),
        ("docs", "Documentation"),
        ("tools", "Tools & IDE"),
        ("news", "News & Trends"),
        ("paid", "Paid Platforms"),
        ("books", "Books & Reading"),
    ]
    name = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=500)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="courses")
    is_free = models.BooleanField(default=True)
    description_en = models.TextField()
    description_ar = models.TextField(blank=True)
    fields_tags = models.JSONField(default=list, blank=True, help_text="e.g. ['python','frontend']")
    icon = models.CharField(max_length=10, default="🔗")
    order_rank = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order_rank", "name"]

    def __str__(self):
        return self.name


class CuratedBook(models.Model):
    """Admin-curated books per field."""
    field_slug = models.SlugField(max_length=100, db_index=True)
    title = models.CharField(max_length=300)
    title_ar = models.CharField(max_length=300, blank=True)
    author = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=500)
    is_free = models.BooleanField(default=True)
    level = models.CharField(
        max_length=20,
        choices=[("junior", "Junior"), ("mid", "Mid"), ("senior", "Senior"), ("all", "All")],
        default="all",
    )
    order_rank = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["field_slug", "order_rank"]

    def __str__(self):
        return f"{self.field_slug}: {self.title}"


class UserPlaylist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField(max_length=500)
    youtube_url = models.URLField(max_length=500)
    playlist_id = models.CharField(max_length=50, blank=True, db_index=True)
    thumbnail = models.URLField(max_length=500, blank=True)
    field_slug = models.CharField(max_length=100, blank=True)
    career_level = models.CharField(max_length=20, blank=True)
    source_query = models.CharField(max_length=300, blank=True)
    gemini_verified = models.BooleanField(null=True, blank=True)
    gemini_note = models.TextField(blank=True)
    is_saved_explicit = models.BooleanField(
        default=True,
        help_text="True if user clicked Save; False if row was created from opening a playlist only.",
    )
    last_opened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_opened_at", "-created_at"]

    def __str__(self):
        return f"{self.user} — {self.title[:40]}"


class UserLibraryItem(models.Model):
    TYPE_CHOICES = [("book", "Book"), ("video", "Video"), ("playlist", "Playlist")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_items")
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=500)
    local_path = models.CharField(max_length=500, blank=True)
    field_slug = models.CharField(max_length=100, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_at"]

    def __str__(self):
        return self.title


class SearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_history", null=True, blank=True
    )
    query = models.CharField(max_length=300)
    search_type = models.CharField(max_length=20, default="all")  # all, youtube, books
    results_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Search histories"

    def __str__(self):
        return self.query


class DownloadJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads")
    title = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress_pct = models.PositiveSmallIntegerField(default=0)
    file_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    estimated_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Rough total size from yt-dlp metadata before/during download.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def estimated_size_label_ar(self) -> str:
        """Human-readable approximate disk usage for UI."""
        b = self.estimated_bytes
        if not b:
            return ""
        gb = b / (1024**3)
        if gb >= 1:
            return f"≈ {gb:.1f} جيجابايت"
        mb = b / (1024**2)
        return f"≈ {mb:.0f} ميجابايت"
