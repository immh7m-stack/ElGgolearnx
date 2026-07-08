from django.urls import path

from . import api_views

urlpatterns = [
    path("chat/start/", api_views.StartChatAPI.as_view(), name="api-chat-start"),
    path("chat/<int:session_id>/message/", api_views.SendMessageAPI.as_view(), name="api-chat-message"),
    path(
        "chat/<int:session_id>/retry-assistant/",
        api_views.RetryLastAssistantAPI.as_view(),
        name="api-chat-retry-assistant",
    ),
    path("chat/<int:session_id>/history/", api_views.ChatHistoryAPI.as_view(), name="api-chat-history"),
]
