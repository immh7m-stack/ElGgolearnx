from django.contrib import admin

from .models import CuratedBook, DownloadJob, EducationalSite, SearchHistory, UserLibraryItem, UserPlaylist


@admin.register(EducationalSite)
class EducationalSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_free", "order_rank", "is_active")
    list_filter = ("category", "is_free", "is_active")
    search_fields = ("name", "name_ar", "description_en")
    list_editable = ("order_rank", "is_active")


@admin.register(CuratedBook)
class CuratedBookAdmin(admin.ModelAdmin):
    list_display = ("field_slug", "title", "author", "level", "is_free", "order_rank")
    list_filter = ("field_slug", "level", "is_free")
    search_fields = ("title", "author")
    list_editable = ("order_rank",)


@admin.register(UserPlaylist)
class UserPlaylistAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "field_slug", "career_level", "gemini_verified", "created_at")
    list_filter = ("field_slug", "career_level")


@admin.register(UserLibraryItem)
class UserLibraryItemAdmin(admin.ModelAdmin):
    list_display = ("user", "item_type", "title", "field_slug", "saved_at")
    list_filter = ("item_type",)


@admin.register(DownloadJob)
class DownloadJobAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "status", "progress_pct", "created_at")
    list_filter = ("status",)


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("query", "user", "search_type", "created_at")
    list_filter = ("search_type",)
