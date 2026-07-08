from django.contrib import admin

from .models import Review, RoadmapContribution


@admin.register(RoadmapContribution)
class RoadmapContributionAdmin(admin.ModelAdmin):
    list_display = ("field_slug", "contributor", "status", "created_at")
    list_filter = ("status",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("contribution", "reviewer", "approved", "created_at")
