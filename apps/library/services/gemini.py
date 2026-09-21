"""Gemini: validate if a YouTube playlist fits a learning goal."""
from __future__ import annotations

import json
import logging

import requests
from django.conf import settings

from config.gemini_client import gemini_post_generate_content

logger = logging.getLogger(__name__)


def validate_playlist(title: str, channel: str, query: str, level: str = "junior") -> dict:
    """
    Returns {suitable: bool, score: int 0-100, note_ar: str, note_en: str}
    """
    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        return {
            "suitable": True,
            "score": 70,
            "note_ar": "لم يتم تفعيل Gemini — تم قبول الكورس افتراضياً.",
            "note_en": "Gemini not configured — accepted by default.",
        }

    prompt = f"""You are an education curator for Arab developers.
Topic the learner wants: "{query}"
Target level: {level}
YouTube playlist: "{title}" by channel "{channel}"

Reply ONLY with JSON:
{{"suitable": true/false, "score": 0-100, "note_en": "short reason", "note_ar": "سبب مختصر بالعربية"}}
Criteria: up-to-date, complete coverage, reputable channel, not paid-only teasers."""

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    try:
        resp = gemini_post_generate_content(payload, timeout=25)
        if resp.status_code == 429:
            logger.error("Gemini playlist check HTTP 429 after retries")
            return {
                "suitable": True,
                "score": 60,
                "note_ar": "النظام عليه ضغط حالياً، تم قبول القائمة مؤقتاً — أعد المحاولة لاحقاً للتحقق.",
                "note_en": "Rate limited — accepted temporarily.",
            }
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except requests.RequestException as e:
        logger.exception("Gemini playlist network error: %s", e)
        return {
            "suitable": True,
            "score": 50,
            "note_ar": f"تعذر التحقق: {e}",
            "note_en": str(e),
        }
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        logger.exception("Gemini playlist parse error: %s", e)
        return {
            "suitable": True,
            "score": 50,
            "note_ar": f"تعذر التحقق: {e}",
            "note_en": str(e),
        }
