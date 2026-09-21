from django.contrib import admin

from .models import Field, Module, Playlist, Project, Skill, Track


class PlaylistInline(admin.TabularInline):
    model = Playlist
    extra = 0


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    show_change_link = True


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_ar", "name_en", "order_rank", "is_active")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("field", "career_level", "duration_months", "projects_needed")
    list_filter = ("career_level", "field")
    inlines = [PlaylistInline, ModuleInline, ProjectInline]


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("track", "order_num", "title_ar", "duration_days")
    inlines = [SkillInline]
