import re

# Common intro, outro and filler expressions in transcripts
FILLER_PATTERNS = [
    r"\b(أهلاً وسهلاً|أهلا وسهلا|مرحباً بكم|مرحبًا بكم|مرحبا بكم|لا تنسى الاشتراك|اشترك في القناة|تفعل الجرس|لايك وكومنت|لايك واشتراك|مثل وشترك|مثل واشتراك)\b",
    r"\b(welcome to|subscribe|like and subscribe|leave a comment|hit the bell|please subscribe|don\'t forget to subscribe)\b",
    r"\[(music|موسيقى|صوت|أصوات)\]",
]


def clean_line_text(text: str) -> str:
    """Strips filler words and normalizes whitespace in transcript text."""
    if not text:
        return ""
    cleaned = text
    for pattern in FILLER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"(?:^|\s)(أهلاً|أهلا|مرحباً|مرحبًا|مرحبا|سلام|Hi|hello|hey)(?:\s|$)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:^|\s)(وسهلاً|وسهلا|بكم|بك|في القناة|في هذا الفيديو|في هذا الدرس)(?:\s|$)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:^|\s)(لا تنسى|لا تنسي|اشتراك|subscribers?|comment|bell)(?:\s|$)", " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^[\W_]+|[\W_]+$", "", cleaned)
    return cleaned


def compress_transcript(transcript_items: list, chunk_duration_seconds: int = 300) -> str:
    """
    Compresses raw transcript items into structured timestamped chunks (e.g. 5-10 min chunks).

    :param transcript_items: List of dicts, e.g. [{'text': '...', 'start': 0.0, 'duration': 2.5}]
    :param chunk_duration_seconds: Duration of each aggregated chunk in seconds (default 300s = 5m).
    :return: Formatted text string with timestamp boundaries.
    """
    if not transcript_items:
        return ""

    chunks = []
    current_chunk_start = 0
    current_chunk_end = chunk_duration_seconds
    current_chunk_lines = []

    for item in transcript_items:
        start_time = float(item.get("start", 0))
        text = clean_line_text(item.get("text", ""))

        if not text:
            continue

        # If line belongs to the next chunk window, commit current chunk
        if start_time >= current_chunk_end and current_chunk_lines:
            chunk_header = f"--- [CHUNK {int(current_chunk_start)}s - {int(current_chunk_end)}s] ---"
            chunk_text = " ".join(current_chunk_lines)
            chunks.append(f"{chunk_header}\n{chunk_text}")

            # Advance window
            current_chunk_start = current_chunk_end
            while start_time >= current_chunk_start + chunk_duration_seconds:
                current_chunk_start += chunk_duration_seconds
            current_chunk_end = current_chunk_start + chunk_duration_seconds
            current_chunk_lines = []

        current_chunk_lines.append(text)

    # Append remaining lines
    if current_chunk_lines:
        chunk_header = f"--- [CHUNK {int(current_chunk_start)}s - {int(current_chunk_end)}s] ---"
        chunk_text = " ".join(current_chunk_lines)
        chunks.append(f"{chunk_header}\n{chunk_text}")

    return "\n\n".join(chunks)
