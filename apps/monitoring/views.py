import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .ai import FocusAnalyzer
from .services import MonitoringService


analyzer = None


@login_required
def monitoring_dashboard(request):
    return render(request, "monitoring/dashboard.html")


@csrf_exempt
@login_required
def analyze_focus(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    payload = json.loads(request.body.decode("utf-8"))
    image_base64 = payload.get("image_base64")
    telemetry = payload.get("telemetry", [])
    session_id = payload.get("session_id") or str(request.user.id)

    if not image_base64:
        return JsonResponse({"detail": "image_base64 is required"}, status=400)

    global analyzer
    if analyzer is None:
        try:
            analyzer = FocusAnalyzer()
        except Exception as exc:
            return JsonResponse({"detail": "focus analyzer unavailable", "error": str(exc)}, status=503)

    result = analyzer.analyze_base64(image_base64)
    result["timestamp"] = payload.get("timestamp")
    result["telemetry"] = telemetry

    MonitoringService.save_session(request.user, session_id, result)

    return JsonResponse(result)
