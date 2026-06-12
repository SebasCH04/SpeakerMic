from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata


class CommandType(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    NEXT = "next"
    PREVIOUS = "previous"
    SET_VOLUME = "set_volume"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    PLAY_TRACK = "play_track"
    PLAY_PLAYLIST = "play_playlist"


@dataclass(frozen=True)
class VoiceCommand:
    type: CommandType
    value: str | int | None = None
    raw_text: str = ""


_NUMBER_WORDS = {
    "cero": 0,
    "diez": 10,
    "veinte": 20,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
}


def normalize_text(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in without_accents if not unicodedata.combining(ch))
    lowered = without_accents.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_command(text: str) -> VoiceCommand | None:
    normalized = normalize_text(text)
    if not normalized:
        return None

    playlist = _extract_after(normalized, ("pon playlist", "reproduce playlist", "pon la playlist"))
    if playlist:
        return VoiceCommand(CommandType.PLAY_PLAYLIST, playlist, raw_text=text)

    if _matches_any(normalized, ("pausa", "pausar", "deten", "detener", "para", "parar")):
        return VoiceCommand(CommandType.PAUSE, raw_text=text)

    if _matches_any(normalized, ("sigue", "seguir", "continua", "continuar", "reproduce", "play")):
        return VoiceCommand(CommandType.PLAY, raw_text=text)

    if _matches_any(normalized, ("siguiente", "proxima", "otra cancion", "cambia cancion", "salta")):
        return VoiceCommand(CommandType.NEXT, raw_text=text)

    if _matches_any(normalized, ("anterior", "previa", "cancion anterior", "regresa")):
        return VoiceCommand(CommandType.PREVIOUS, raw_text=text)

    volume = _parse_volume(normalized)
    if volume is not None:
        return VoiceCommand(CommandType.SET_VOLUME, volume, raw_text=text)

    if "sube volumen" in normalized or "subir volumen" in normalized or normalized == "sube":
        return VoiceCommand(CommandType.VOLUME_UP, raw_text=text)

    if "baja volumen" in normalized or "bajar volumen" in normalized or normalized == "baja":
        return VoiceCommand(CommandType.VOLUME_DOWN, raw_text=text)

    track = _extract_after(normalized, ("pon cancion", "reproduce cancion", "pon la cancion", "reproduce la cancion", "pon"))
    if track:
        return VoiceCommand(CommandType.PLAY_TRACK, track, raw_text=text)

    return None


def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(text == phrase or phrase in text for phrase in phrases)


def _extract_after(text: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        if text.startswith(prefix + " "):
            value = text.removeprefix(prefix).strip()
            return value or None
    return None


def _parse_volume(text: str) -> int | None:
    match = re.search(r"\bvolumen\s+(?:a\s+)?(\d{1,3})\b", text)
    if match:
        return _clamp_volume(int(match.group(1)))

    for word, value in _NUMBER_WORDS.items():
        if f"volumen {word}" in text or f"volumen a {word}" in text:
            return value

    return None


def _clamp_volume(value: int) -> int:
    return max(0, min(100, value))
