from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import Event, Lock, Thread

from .actions import execute_command
from .commands import parse_command
from .config import SpeakerMicConfig
from .speech import create_speaker, spoken_message
from .spotify import SpotifyApiError, SpotifyAuthError, SpotifyClient, needs_spotify_login
from .voice import VoiceCaptureConfig, VoiceRecognitionError, VoskVoiceRecognizer, command_after_wake_word


class TrayAppError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


@dataclass
class SpeakerMicTrayApp:
    config: SpeakerMicConfig

    def run(self) -> None:
        try:
            from PIL import Image, ImageDraw
            import pystray
            from pynput import keyboard
        except ImportError as error:
            raise TrayAppError(
                "Tray dependencies are not installed. Run `python -m pip install -r requirements.txt`."
            ) from error

        lock = Lock()
        logger.info(
            "Tray starting; wake_word_enabled=%s wake_word=%r hotkey=%s",
            self.config.activation.wake_word_enabled,
            self.config.activation.wake_word,
            self.config.app.hotkey,
        )
        client = SpotifyClient(
            self.config.spotify.client_id,
            self.config.spotify.redirect_uri,
        )
        recognizer = VoskVoiceRecognizer(VoiceCaptureConfig(self.config.app.voice_model_path))
        speaker = create_speaker(self.config.speech)
        wake_controller = WakeWordController(lock, recognizer, client, self.config, speaker)
        hotkey_action = (
            wake_controller.activate_manually
            if self.config.activation.wake_word_enabled
            else lambda: _listen_and_execute(lock, recognizer, client, self.config, speaker)
        )
        listen_menu_action = (
            wake_controller.activate_manually
            if self.config.activation.wake_word_enabled
            else lambda: _listen_and_execute(lock, recognizer, client, self.config, speaker)
        )
        icon = pystray.Icon(
            "SpeakerMic",
            _icon_image(Image, ImageDraw),
            "SpeakerMic",
            menu=pystray.Menu(
                pystray.MenuItem("Login Spotify", lambda icon, item: _safe_login(client)),
                pystray.MenuItem(
                    "Listen once",
                    lambda icon, item: listen_menu_action(),
                ),
                pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
            ),
        )

        hotkey = keyboard.GlobalHotKeys(
            {
                self.config.app.hotkey: hotkey_action
            }
        )
        try:
            hotkey.start()
            if self.config.activation.wake_word_enabled:
                wake_controller.start()
            icon.run()
        finally:
            wake_controller.stop()
            hotkey.stop()
            speaker.close()


@dataclass
class WakeWordController:
    lock: Lock
    recognizer: VoskVoiceRecognizer
    client: SpotifyClient
    config: SpeakerMicConfig
    speaker: object

    def __post_init__(self) -> None:
        self._stop_event = Event()
        self._manual_event = Event()
        self._thread = Thread(target=self._run, name="SpeakerMicWakeWord", daemon=True)

    def start(self) -> None:
        print(f"Wake word enabled: {self.config.activation.wake_word}")
        logger.info("WakeWordController starting")
        self._thread.start()

    def stop(self) -> None:
        logger.info("WakeWordController stopping")
        self._stop_event.set()
        self._manual_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def activate_manually(self) -> None:
        logger.info("WakeWordController manual activation requested")
        self._manual_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                activation_text = self.recognizer.listen_until_activation(
                    self.config.activation.wake_word,
                    self._stop_event,
                    self._manual_event,
                )
                if activation_text is None or self._stop_event.is_set():
                    logger.info("WakeWordController activation loop exiting")
                    return

                command_text = command_after_wake_word(
                    activation_text,
                    self.config.activation.wake_word,
                )
                if activation_text:
                    print(f"Wake word heard: {activation_text}")
                    logger.info("Wake word heard=%r command_text=%r", activation_text, command_text)
                    if not command_text:
                        self.speaker.say("Te escucho.")

                _listen_and_execute(
                    self.lock,
                    self.recognizer,
                    self.client,
                    self.config,
                    self.speaker,
                    initial_text=command_text,
                )
            except VoiceRecognitionError as error:
                print(f"Wake word error: {error}")
                logger.exception("Wake word error")
                self.speaker.say("Tuve un problema con el microfono.")
                return


def _listen_and_execute(
    lock: Lock,
    recognizer: VoskVoiceRecognizer,
    client: SpotifyClient,
    config: SpeakerMicConfig,
    speaker,
    initial_text: str = "",
) -> None:
    if not lock.acquire(blocking=False):
        print("SpeakerMic is already listening.")
        speaker.say("Ya estoy escuchando.")
        return

    try:
        text = initial_text or recognizer.listen_once()
        print(f"Heard: {text or '(nothing)'}")
        logger.info("Command heard=%r initial_text=%r", text, initial_text)
        command = parse_command(text)
        if not command:
            print(f"No command recognized from: {text}")
            logger.info("No command recognized from=%r", text)
            speaker.say("No entendi el comando.")
            return

        device_id = client.preferred_or_active_device_id(config.spotify.preferred_device_name)
        message = execute_command(client, command, device_id, config.app.volume_step)
        print(message)
        logger.info("Command executed; message=%r", message)
        speaker.say(spoken_message(message))
    except (SpotifyApiError, SpotifyAuthError, VoiceRecognitionError) as error:
        print(f"SpeakerMic error: {error}")
        logger.exception("SpeakerMic command error")
        if needs_spotify_login(error):
            speaker.say("Necesito iniciar sesion en Spotify otra vez.")
        else:
            speaker.say("Tuve un problema ejecutando el comando.")
    finally:
        lock.release()


def _safe_login(client: SpotifyClient) -> None:
    try:
        client.login()
        print("Spotify login complete.")
    except (SpotifyApiError, SpotifyAuthError) as error:
        print(f"Spotify error: {error}")


def _icon_image(Image, ImageDraw):
    image = Image.new("RGB", (64, 64), "#1db954")
    draw = ImageDraw.Draw(image)
    draw.ellipse((18, 12, 46, 40), fill="white")
    draw.rectangle((28, 38, 36, 50), fill="white")
    draw.rectangle((20, 50, 44, 56), fill="white")
    return image
