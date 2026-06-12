from __future__ import annotations

import argparse
from pathlib import Path
import logging
import shutil

from .actions import execute_command
from .commands import parse_command
from .config import load_config
from .speech import create_speaker, installed_windows_voices, spoken_message
from .spotify import SpotifyApiError, SpotifyAuthError, SpotifyClient
from .tray_app import SpeakerMicTrayApp, TrayAppError
from .voice import VoiceCaptureConfig, VoiceRecognitionError, VoskVoiceRecognizer, download_spanish_model


def main(argv: list[str] | None = None) -> int:
    logging.getLogger(__name__).info("SpeakerMic CLI started with argv=%s", argv)
    parser = argparse.ArgumentParser(prog="speakermic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-config", help="Create config.toml from config.example.toml.")
    subparsers.add_parser("spotify-login", help="Authorize Spotify and cache a local token.")
    subparsers.add_parser("spotify-devices", help="List Spotify playback devices.")
    subparsers.add_parser("spotify-status", help="Show account and playback status.")
    subparsers.add_parser("download-model", help="Download the default offline Spanish Vosk model.")
    subparsers.add_parser("speak-test", help="Speak a short local text-to-speech test.")
    subparsers.add_parser("speech-voices", help="List installed Windows text-to-speech voices.")
    subparsers.add_parser("listen-once", help="Listen through the microphone and print recognized text.")
    subparsers.add_parser("listen-command", help="Listen once, parse the command, and control Spotify.")
    subparsers.add_parser("tray", help="Run the tray app with the configured hotkey.")

    parse_parser = subparsers.add_parser("parse", help="Parse a Spanish voice command.")
    parse_parser.add_argument("text", nargs="+")

    run_parser = subparsers.add_parser("run-text", help="Execute a text command through Spotify.")
    run_parser.add_argument("text", nargs="+")

    args = parser.parse_args(argv)

    if args.command == "init-config":
        return _init_config()

    if args.command == "parse":
        command = parse_command(" ".join(args.text))
        print(command if command else "No command recognized.")
        return 0 if command else 1

    if args.command == "spotify-login":
        config = load_config()
        return _with_spotify(config.spotify.client_id, config.spotify.redirect_uri, _login)

    if args.command == "spotify-devices":
        config = load_config()
        return _with_spotify(config.spotify.client_id, config.spotify.redirect_uri, _print_devices)

    if args.command == "spotify-status":
        config = load_config()
        return _with_spotify(config.spotify.client_id, config.spotify.redirect_uri, _print_status)

    if args.command == "download-model":
        config = load_config()
        try:
            path = download_spanish_model(config.app.voice_model_path)
        except VoiceRecognitionError as error:
            print(f"Voice error: {error}")
            return 1
        print(f"Model ready: {path}")
        return 0

    if args.command == "speak-test":
        config = load_config()
        speaker = create_speaker(config.speech)
        try:
            speaker.say("SpeakerMic esta listo.")
        finally:
            speaker.close()
        print("Speech test complete.")
        return 0

    if args.command == "speech-voices":
        voices = installed_windows_voices()
        if not voices:
            print("No Windows speech voices found.")
            return 1
        for voice in voices:
            print(voice)
        return 0

    if args.command == "listen-once":
        config = load_config()
        recognizer = VoskVoiceRecognizer(VoiceCaptureConfig(config.app.voice_model_path))
        try:
            print(recognizer.listen_once() or "No speech recognized.")
        except VoiceRecognitionError as error:
            print(f"Voice error: {error}")
            return 1
        return 0

    if args.command == "listen-command":
        config = load_config()
        speaker = create_speaker(config.speech)
        recognizer = VoskVoiceRecognizer(VoiceCaptureConfig(config.app.voice_model_path))
        try:
            text = recognizer.listen_once()
        except VoiceRecognitionError as error:
            print(f"Voice error: {error}")
            speaker.say("Tuve un problema con el microfono.")
            speaker.close()
            return 1

        print(f"Heard: {text or '(nothing)'}")
        voice_command = parse_command(text)
        if voice_command is None:
            print("No command recognized.")
            speaker.say("No entendi el comando.")
            speaker.close()
            return 1

        result = _with_spotify(
            config.spotify.client_id,
            config.spotify.redirect_uri,
            lambda client: _execute_and_speak(
                client,
                voice_command,
                config,
                speaker,
            ),
            speaker=speaker,
            spoken_error="Tuve un problema con Spotify.",
        )
        speaker.close()
        return result

    if args.command == "tray":
        config = load_config()
        try:
            print("SpeakerMic tray is running.")
            print(f"Hotkey: {config.app.hotkey}")
            if config.activation.wake_word_enabled:
                print(f"Wake word: {config.activation.wake_word}")
            print("Close it from the tray icon menu, or press Ctrl+C in this terminal.")
            SpeakerMicTrayApp(config).run()
        except KeyboardInterrupt:
            print("SpeakerMic tray stopped.")
            return 0
        except (TrayAppError, SpotifyApiError, SpotifyAuthError) as error:
            print(f"SpeakerMic error: {error}")
            return 1
        return 0

    if args.command == "run-text":
        config = load_config()
        voice_command = parse_command(" ".join(args.text))
        if voice_command is None:
            print("No command recognized.")
            return 1
        return _with_spotify(
            config.spotify.client_id,
            config.spotify.redirect_uri,
            lambda client: print(
                execute_command(
                    client,
                    voice_command,
                    client.preferred_or_active_device_id(config.spotify.preferred_device_name),
                    config.app.volume_step,
                )
            ),
        )

    return 1


def _init_config() -> int:
    target = Path("config.toml")
    if target.exists():
        print("config.toml already exists.")
        return 0

    shutil.copyfile("config.example.toml", target)
    print("Created config.toml. Paste your Spotify client_id before logging in.")
    return 0


def _with_spotify(client_id: str, redirect_uri: str, action, speaker=None, spoken_error: str = "") -> int:
    try:
        client = SpotifyClient(client_id=client_id, redirect_uri=redirect_uri)
        action(client)
    except (SpotifyApiError, SpotifyAuthError) as error:
        print(f"Spotify error: {error}")
        if speaker is not None and spoken_error:
            speaker.say(spoken_error)
        return 1
    return 0


def _execute_and_speak(client: SpotifyClient, voice_command, config, speaker) -> None:
    message = execute_command(
        client,
        voice_command,
        client.preferred_or_active_device_id(config.spotify.preferred_device_name),
        config.app.volume_step,
    )
    print(message)
    speaker.say(spoken_message(message))


def _print_devices(client: SpotifyClient) -> None:
    devices = client.devices()
    if not devices:
        print("No Spotify devices found. Open Spotify Desktop and start playback once.")
        return

    for device in devices:
        active = "active" if device.is_active else "inactive"
        print(f"{device.name} ({active})")


def _print_status(client: SpotifyClient) -> None:
    user = client.current_user()
    print(f"Account: {user.get('display_name') or user.get('id')}")
    print(f"Product: {user.get('product', 'unknown')}")

    devices = client.devices()
    if not devices:
        print("Devices: none found")
    else:
        print("Devices:")
        for device in devices:
            active = "active" if device.is_active else "inactive"
            print(f"- {device.name} ({active})")

    playback = client.playback_state()
    if not playback:
        print("Playback: none")
        return

    device = playback.get("device") or {}
    item = playback.get("item") or {}
    artists = ", ".join(artist.get("name", "") for artist in item.get("artists", []))
    title = item.get("name", "unknown")
    is_playing = "playing" if playback.get("is_playing") else "paused"
    print(f"Playback: {is_playing}")
    print(f"Playback device: {device.get('name', 'unknown')}")
    print(f"Track: {title}" + (f" - {artists}" if artists else ""))


def _login(client: SpotifyClient) -> None:
    client.login()
    print("Spotify login complete.")
