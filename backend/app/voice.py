"""Voice bridge for Temur: OpenAI Whisper (speech-to-text) + OpenAI TTS (a nice
male voice, "onyx"). Temur stays the local brain — OpenAI is only the ears & voice.

The API key is read from the OPENAI_API_KEY env var or from storage/openai.key
(one line). It is never printed or returned to the client.

Stdlib only (urllib) — no openai SDK needed.
"""
from __future__ import annotations
import os
import json
import uuid
import urllib.request
from pathlib import Path

from app import config

KEY_FILE = config.STORAGE / "openai.key"
STT_URL = "https://api.openai.com/v1/audio/transcriptions"
TTS_URL = "https://api.openai.com/v1/audio/speech"

# Models & voice (override via env if needed).
# Pipeline: 🎤 mic → gpt-4o-transcribe → Ollama (Temur) → gpt-4o-mini-tts → 🔊
STT_MODEL = os.environ.get("OPENAI_STT_MODEL", "gpt-4o-transcribe")
TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "onyx")           # male, warm


def get_key() -> str | None:
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k.strip()
    try:
        k = KEY_FILE.read_text("utf-8").strip()
        return k or None
    except Exception:
        return None


def set_key(key: str) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(key.strip(), "utf-8")


def has_key() -> bool:
    return bool(get_key())


# --------------------------------------------------------------------------- #
#  multipart helper (Whisper needs multipart/form-data)
# --------------------------------------------------------------------------- #
def _multipart(fields: dict, file_field: str, filename: str, file_bytes: bytes,
               file_ct: str) -> tuple[bytes, str]:
    boundary = "----ProjectNest" + uuid.uuid4().hex
    nl = b"\r\n"
    buf = bytearray()
    for name, val in fields.items():
        buf += b"--" + boundary.encode() + nl
        buf += f'Content-Disposition: form-data; name="{name}"'.encode() + nl + nl
        buf += str(val).encode("utf-8") + nl
    buf += b"--" + boundary.encode() + nl
    buf += (f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"').encode() + nl
    buf += f"Content-Type: {file_ct}".encode() + nl + nl
    buf += file_bytes + nl
    buf += b"--" + boundary.encode() + b"--" + nl
    return bytes(buf), boundary


# --------------------------------------------------------------------------- #
#  speech-to-text
# --------------------------------------------------------------------------- #
def transcribe(audio: bytes, filename: str = "audio.webm", lang: str | None = None) -> str | None:
    key = get_key()
    if not key or not audio:
        return None
    fields = {"model": STT_MODEL}
    if lang in ("en", "ru", "uz"):
        fields["language"] = lang
    ct = "audio/webm" if filename.endswith(".webm") else "audio/wav" if filename.endswith(".wav") else "application/octet-stream"
    body, boundary = _multipart(fields, "file", filename, audio, ct)
    try:
        req = urllib.request.Request(
            STT_URL, data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("text", "").strip()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  text-to-speech (returns mp3 bytes)
# --------------------------------------------------------------------------- #
def synthesize(text: str, voice: str | None = None) -> bytes | None:
    key = get_key()
    if not key or not text:
        return None
    try:
        req = urllib.request.Request(
            TTS_URL,
            data=json.dumps({"model": TTS_MODEL, "voice": voice or TTS_VOICE,
                             "input": text[:4000], "response_format": "mp3"}).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception:
        return None
