from django.contrib import admin

from .models import ChatMessage, ChatSession


class MessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "field_slug", "track_level", "created_at")
    inlines = [MessageInline]
