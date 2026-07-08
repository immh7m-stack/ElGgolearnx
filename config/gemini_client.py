"""

Shared Gemini REST helper: retries on HTTP 429 with exponential backoff.

Uses header auth + automatic model fallback when the API returns 404 (common when

a model is retired or not enabled for your API key).

"""



from __future__ import annotations



import logging

import os

import time

from typing import Any



import requests

from django.conf import settings



logger = logging.getLogger(__name__)



MAX_GEMINI_RETRIES = 3



# حسب وثائق Google (2025–2026): يُفضَّل نماذج 2.5؛ gemini-1.5-flash قد يُعاد له 404 لحسابات جديدة.

DEFAULT_MODEL_FALLBACKS: tuple[str, ...] = (

    "gemini-2.5-flash",

    "gemini-flash-latest",

    "gemini-2.0-flash",

    "gemini-1.5-flash",

)





def _parse_fallback_env() -> list[str]:

    raw = (os.getenv("GEMINI_MODEL_FALLBACKS") or "").strip()

    if raw:

        return [x.strip() for x in raw.split(",") if x.strip()]

    return list(DEFAULT_MODEL_FALLBACKS)





def _model_try_chain(preferred: str | None) -> list[str]:

    p = (preferred or "").strip()

    seen: set[str] = set()

    out: list[str] = []

    for m in [p, *_parse_fallback_env()]:

        if not m or m in seen:

            continue

        seen.add(m)

        out.append(m)

    return out or ["gemini-2.5-flash"]





def _post_generate_single(

    api_key: str,

    model: str,

    payload: dict[str, Any],

    *,

    timeout: int,

) -> requests.Response:

    url = (

        "https://generativelanguage.googleapis.com/v1beta/models/"

        f"{model}:generateContent"

    )

    headers = {

        "Content-Type": "application/json",

        "x-goog-api-key": api_key,

    }

    last: requests.Response | None = None

    for attempt in range(MAX_GEMINI_RETRIES):

        last = requests.post(url, json=payload, headers=headers, timeout=timeout)

        if last.status_code != 429:

            return last

        if attempt == MAX_GEMINI_RETRIES - 1:

            break

        wait_s = 2**attempt

        time.sleep(wait_s)

        logger.warning(

            "Gemini 429 — model=%s retry %s/%s after %ss",

            model,

            attempt + 2,

            MAX_GEMINI_RETRIES,

            wait_s,

        )

    return last  # type: ignore[return-value]





def gemini_post_generate_content(

    payload: dict[str, Any], *, timeout: int = 60, model: str | None = None

) -> requests.Response:

    """

    POST to generateContent. Retries on HTTP 429 per model.



    If ``model`` is omitted, uses ``settings.GEMINI_MODEL``.

    On HTTP 404, tries further models from DEFAULT_MODEL_FALLBACKS / GEMINI_MODEL_FALLBACKS.

    """

    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()

    preferred = model if model is not None else getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    chain = _model_try_chain(preferred)



    last: requests.Response | None = None

    for i, m in enumerate(chain):

        last = _post_generate_single(api_key, m, payload, timeout=timeout)

        if last.status_code != 404:

            if i > 0 and last.ok:

                logger.info("Gemini: succeeded with fallback model=%s (after 404 on earlier names)", m)

            return last

        logger.warning(

            "Gemini HTTP 404 for model=%s — trying next in chain (have %s more)",

            m,

            len(chain) - i - 1,

        )

    return last  # type: ignore[return-value]
