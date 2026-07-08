from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ["id", "field_slug", "track_level", "module_title", "page_path", "created_at"]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]


class StartChatSerializer(serializers.Serializer):
    field_slug = serializers.CharField(required=False, allow_blank=True)
    track_level = serializers.CharField(required=False, allow_blank=True)
    module_title = serializers.CharField(required=False, allow_blank=True)
    page_path = serializers.CharField(required=False, allow_blank=True, max_length=512)
