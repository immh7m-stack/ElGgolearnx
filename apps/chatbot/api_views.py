from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .gemini import chat_with_gemini
from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatSessionSerializer, StartChatSerializer


class StartChatAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StartChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            field_slug=data.get("field_slug", ""),
            track_level=data.get("track_level", ""),
            module_title=data.get("module_title", ""),
            page_path=(data.get("page_path") or "").strip()[:512],
        )
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SendMessageAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, pk=session_id)
        content = request.data.get("content", "").strip()
        if not content:
            return Response({"error": "content required"}, status=status.HTTP_400_BAD_REQUEST)

        ChatMessage.objects.create(session=session, role="user", content=content)
        history = [{"role": m.role, "content": m.content} for m in session.messages.all()]
        result = chat_with_gemini(
            history,
            {
                "field_slug": session.field_slug,
                "track_level": session.track_level,
                "module_title": session.module_title,
                "page_path": session.page_path,
            },
        )
        msg = ChatMessage.objects.create(session=session, role="assistant", content=result.text)
        data = dict(ChatMessageSerializer(msg).data)
        data["rate_limit_exhausted"] = result.rate_limit_exhausted
        return Response(data)


class RetryLastAssistantAPI(APIView):
    """يحذف آخر رد مساعد ويعيد طلب Gemini دون تكرار رسالة المستخدم."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, pk=session_id)
        last = session.messages.order_by("-created_at").first()
        if not last or last.role != "assistant":
            return Response(
                {"detail": "لا يوجد رد مساعد لإعادة توليده."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        last.delete()
        history = [{"role": m.role, "content": m.content} for m in session.messages.all()]
        result = chat_with_gemini(
            history,
            {
                "field_slug": session.field_slug,
                "track_level": session.track_level,
                "module_title": session.module_title,
                "page_path": session.page_path,
            },
        )
        msg = ChatMessage.objects.create(session=session, role="assistant", content=result.text)
        data = dict(ChatMessageSerializer(msg).data)
        data["rate_limit_exhausted"] = result.rate_limit_exhausted
        return Response(data)


class ChatHistoryAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, pk=session_id)
        messages = session.messages.all()
        return Response(ChatMessageSerializer(messages, many=True).data)
