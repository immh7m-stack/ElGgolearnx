from django.conf import settings
from django.db import models
from django.utils import timezone
from pathlib import Path


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
    thumbnail = models.URLField(max_length=500, blank=True, help_text="Book cover image URL")
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


class Book(models.Model):
    title = models.CharField(max_length=300)
    author = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="library/covers/", blank=True, null=True)
    pdf_file = models.FileField(upload_to="library/books/", blank=True, null=True)
    url = models.URLField(max_length=500, blank=True, help_text="Optional external resource URL")
    language = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    is_cached = models.BooleanField(default=False)
    cached_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    cache_size = models.PositiveBigIntegerField(default=0)
    cache_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "title"]

    def __str__(self):
        return self.title

    def cache_path(self) -> str:
        if not self.pk:
            return ""
        filename = f"book_cache_{self.pk}.pdf"
        return str(Path(settings.BOOK_CACHE_PATH) / filename)

    def cache_exists(self) -> bool:
        return bool(self.cache_path() and Path(self.cache_path()).is_file())

    def mark_cached(self, file_size: int):
        self.is_cached = True
        self.cached_at = timezone.now()
        self.cache_size = file_size
        self.cache_expires_at = timezone.now() + settings.BOOK_CACHE_TTL
        self.save(update_fields=["is_cached", "cached_at", "cache_size", "cache_expires_at"])

    def mark_cache_removed(self):
        self.is_cached = False
        self.cached_at = None
        self.cache_size = 0
        self.cache_expires_at = None
        self.save(update_fields=["is_cached", "cached_at", "cache_size", "cache_expires_at"])


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
