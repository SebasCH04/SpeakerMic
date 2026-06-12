from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from difflib import SequenceMatcher
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
    "zero": 0,
    "diez": 10,
    "ten": 10,
    "veinte": 20,
    "twenty": 20,
    "treinta": 30,
    "thirty": 30,
    "cuarenta": 40,
    "forty": 40,
    "cincuenta": 50,
    "fifty": 50,
    "sesenta": 60,
    "sixty": 60,
    "setenta": 70,
    "seventy": 70,
    "ochenta": 80,
    "eighty": 80,
    "noventa": 90,
    "ninety": 90,
    "cien": 100,
    "one hundred": 100,
    "hundred": 100,
}

_PLAYLIST_PREFIXES = (
    "pon playlist",
    "reproduce playlist",
    "reproducir playlist",
    "pon la playlist",
    "play playlist",
    "play the playlist",
    "start playlist",
    "start the playlist",
)

_TRACK_PREFIXES = (
    "pon cancion",
    "reproduce cancion",
    "reproducir cancion",
    "pon la cancion",
    "reproduce la cancion",
    "reproducir la cancion",
    "play song",
    "play the song",
    "play track",
    "play the track",
    "start song",
    "start the song",
    "put song",
    "put the song",
)

_GENERIC_TRACK_PREFIXES = ("pon",)

_PLAY_PHRASES = (
    "sigue",
    "seguir",
    "continua",
    "continuar",
    "continue",
    "resume",
    "start",
    "start music",
    "play music",
    "play the music",
    "reanuda",
    "reanudar",
    "reproduce",
    "reproducir",
    "play",
    "dale play",
    "pon musica",
    "pon la musica",
    "quita pausa",
)

_PLAY_WORDS = (
    "sigue",
    "seguir",
    "continua",
    "continuar",
    "continue",
    "reanuda",
    "reanudar",
    "reproduce",
    "reproducir",
    "repoduce",
    "repoducir",
    "produir",
    "producir",
    "produsir",
    "play",
    "pley",
    "resume",
    "resum",
    "start",
)

_PAUSE_PHRASES = (
    "pausa",
    "pausar",
    "deten",
    "detener",
    "para",
    "parar",
    "stop",
    "pause",
    "pause music",
    "pause the music",
    "stop music",
    "stop the music",
    "alto",
    "calla",
    "silencio",
    "deten musica",
    "detener musica",
    "pausa musica",
    "pausa la musica",
)

_PAUSE_WORDS = (
    "pausa",
    "pausar",
    "pausalo",
    "deten",
    "detener",
    "para",
    "parar",
    "stop",
    "pause",
    "paus",
    "alto",
    "calla",
    "silencio",
)

_NEXT_PHRASES = (
    "siguiente",
    "proxima",
    "otra cancion",
    "otra",
    "cambia cancion",
    "cambiar cancion",
    "salta",
    "pasala",
    "pasar cancion",
    "siguiente cancion",
    "next",
    "next song",
    "next track",
    "skip",
    "skip song",
    "skip track",
    "change song",
    "change track",
)

_NEXT_WORDS = (
    "siguiente",
    "sigiente",
    "siguente",
    "proxima",
    "proxina",
    "otra",
    "cambia",
    "cambiar",
    "salta",
    "pasala",
    "pasar",
    "next",
    "skip",
    "change",
)

_PREVIOUS_PHRASES = (
    "anterior",
    "previa",
    "cancion anterior",
    "regresa",
    "regresar",
    "devuelve",
    "devuelvete",
    "vuelve",
    "atras",
    "previous",
    "previous song",
    "previous track",
    "back",
    "go back",
)

_PREVIOUS_WORDS = (
    "anterior",
    "previa",
    "regresa",
    "regresar",
    "devuelve",
    "devuelvete",
    "vuelve",
    "atras",
    "previous",
    "prev",
    "back",
)

_VOLUME_WORDS_UP = ("sube", "subir", "aumenta", "aumentar", "mas", "alto", "up", "raise", "increase", "louder")
_VOLUME_WORDS_DOWN = ("baja", "bajar", "disminuye", "disminuir", "menos", "down", "lower", "decrease", "quieter")


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

    playlist = _extract_after(normalized, _PLAYLIST_PREFIXES)
    if playlist:
        return VoiceCommand(CommandType.PLAY_PLAYLIST, playlist, raw_text=text)

    track = _extract_after(normalized, _TRACK_PREFIXES)
    if track:
        return VoiceCommand(CommandType.PLAY_TRACK, track, raw_text=text)

    if _matches_command(normalized, _PLAY_PHRASES, _PLAY_WORDS):
        return VoiceCommand(CommandType.PLAY, raw_text=text)

    if _matches_command(normalized, _PAUSE_PHRASES, _PAUSE_WORDS):
        return VoiceCommand(CommandType.PAUSE, raw_text=text)

    if _matches_command(normalized, _NEXT_PHRASES, _NEXT_WORDS):
        return VoiceCommand(CommandType.NEXT, raw_text=text)

    if _matches_command(normalized, _PREVIOUS_PHRASES, _PREVIOUS_WORDS):
        return VoiceCommand(CommandType.PREVIOUS, raw_text=text)

    volume = _parse_volume(normalized)
    if volume is not None:
        return VoiceCommand(CommandType.SET_VOLUME, volume, raw_text=text)

    if _matches_relative_volume(normalized, _VOLUME_WORDS_UP):
        return VoiceCommand(CommandType.VOLUME_UP, raw_text=text)

    if _matches_relative_volume(normalized, _VOLUME_WORDS_DOWN):
        return VoiceCommand(CommandType.VOLUME_DOWN, raw_text=text)

    track = _extract_after(normalized, _GENERIC_TRACK_PREFIXES)
    if track:
        return VoiceCommand(CommandType.PLAY_TRACK, track, raw_text=text)

    return None


def _matches_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(text == phrase or phrase in text for phrase in phrases)


def _matches_command(text: str, phrases: tuple[str, ...], words: tuple[str, ...]) -> bool:
    if _matches_any(text, phrases):
        return True

    text_words = text.split()
    return any(_word_matches(candidate, words) for candidate in text_words)


def _word_matches(candidate: str, words: tuple[str, ...]) -> bool:
    if len(candidate) < 4:
        return candidate in words

    for word in words:
        if candidate == word:
            return True
        if len(word) >= 5 and SequenceMatcher(None, candidate, word).ratio() >= 0.82:
            return True
    return False


def _extract_after(text: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        if text.startswith(prefix + " "):
            value = text.removeprefix(prefix).strip()
            return value or None
    return None


def _parse_volume(text: str) -> int | None:
    match = re.search(r"\b(?:volumen|volume)\s+(?:a|al|to|at)?\s*(\d{1,3})\b", text)
    if match:
        return _clamp_volume(int(match.group(1)))

    for word, value in _NUMBER_WORDS.items():
        if (
            f"volumen {word}" in text
            or f"volumen a {word}" in text
            or f"volume {word}" in text
            or f"volume to {word}" in text
            or f"set volume to {word}" in text
        ):
            return value

    return None


def _matches_relative_volume(text: str, direction_words: tuple[str, ...]) -> bool:
    words = text.split()
    has_direction = any(_word_matches(word, direction_words) for word in words)
    has_volume = any(_word_matches(word, ("volumen", "volume", "volumenes")) for word in words)
    return has_direction and (has_volume or len(words) == 1)


def _clamp_volume(value: int) -> int:
    return max(0, min(100, value))
