from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path("config.toml")


@dataclass(frozen=True)
class AppConfig:
    hotkey: str = "<ctrl>+<alt>+<space>"
    voice_language: str = "es"
    voice_model_path: Path = Path("models/vosk-model-small-es-0.42")
    volume_step: int = 10


@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str = ""
    redirect_uri: str = "http://127.0.0.1:8888/callback"
    preferred_device_name: str = ""


@dataclass(frozen=True)
class SpeechConfig:
    enabled: bool = True
    voice_name_contains: str = "spanish"
    rate: int = 175
    volume: float = 1.0


@dataclass(frozen=True)
class ActivationConfig:
    wake_word_enabled: bool = False
    wake_word: str = "consola"


@dataclass(frozen=True)
class SpeakerMicConfig:
    app: AppConfig
    spotify: SpotifyConfig
    speech: SpeechConfig
    activation: ActivationConfig


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SpeakerMicConfig:
    data = _read_toml(path)
    app_data = data.get("app", {})
    spotify_data = data.get("spotify", {})
    speech_data = data.get("speech", {})
    activation_data = data.get("activation", {})

    return SpeakerMicConfig(
        app=AppConfig(
            hotkey=app_data.get("hotkey", AppConfig.hotkey),
            voice_language=app_data.get("voice_language", AppConfig.voice_language),
            voice_model_path=Path(app_data.get("voice_model_path", AppConfig.voice_model_path)),
            volume_step=int(app_data.get("volume_step", AppConfig.volume_step)),
        ),
        spotify=SpotifyConfig(
            client_id=spotify_data.get("client_id", SpotifyConfig.client_id),
            redirect_uri=spotify_data.get("redirect_uri", SpotifyConfig.redirect_uri),
            preferred_device_name=spotify_data.get(
                "preferred_device_name",
                SpotifyConfig.preferred_device_name,
            ),
        ),
        speech=SpeechConfig(
            enabled=bool(speech_data.get("enabled", SpeechConfig.enabled)),
            voice_name_contains=speech_data.get(
                "voice_name_contains",
                SpeechConfig.voice_name_contains,
            ),
            rate=int(speech_data.get("rate", SpeechConfig.rate)),
            volume=float(speech_data.get("volume", SpeechConfig.volume)),
        ),
        activation=ActivationConfig(
            wake_word_enabled=bool(
                activation_data.get(
                    "wake_word_enabled",
                    ActivationConfig.wake_word_enabled,
                )
            ),
            wake_word=activation_data.get("wake_word", ActivationConfig.wake_word),
        ),
    )


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}

    with path.open("rb") as file:
        return tomllib.load(file)
