from __future__ import annotations

from .commands import CommandType, VoiceCommand
from .spotify import SpotifyClient


def execute_command(
    client: SpotifyClient,
    command: VoiceCommand,
    device_id: str | None = None,
    volume_step: int = 10,
) -> str:
    match command.type:
        case CommandType.PAUSE:
            client.pause(device_id)
            return "Paused Spotify."
        case CommandType.PLAY:
            client.play(device_id)
            return "Resumed Spotify."
        case CommandType.NEXT:
            client.next_track(device_id)
            return "Skipped to next track."
        case CommandType.PREVIOUS:
            client.previous_track(device_id)
            return "Skipped to previous track."
        case CommandType.SET_VOLUME:
            client.set_volume(int(command.value), device_id)
            return f"Set volume to {command.value}%."
        case CommandType.VOLUME_UP:
            volume = _relative_volume(client, volume_step)
            client.set_volume(volume, device_id)
            return f"Raised volume to {volume}%."
        case CommandType.VOLUME_DOWN:
            volume = _relative_volume(client, -volume_step)
            client.set_volume(volume, device_id)
            return f"Lowered volume to {volume}%."
        case CommandType.PLAY_TRACK:
            uri = client.search_first_uri(str(command.value), "track")
            if not uri:
                return f"No track found for: {command.value}"
            client.play(device_id, {"uris": [uri]})
            return f"Playing track: {command.value}"
        case CommandType.PLAY_PLAYLIST:
            uri = client.search_first_uri(str(command.value), "playlist")
            if not uri:
                return f"No playlist found for: {command.value}"
            client.play(device_id, {"context_uri": uri})
            return f"Playing playlist: {command.value}"

    raise ValueError(f"Unsupported command: {command.type}")


def _relative_volume(client: SpotifyClient, delta: int) -> int:
    playback = client.playback_state()
    current = playback.get("device", {}).get("volume_percent")
    if current is None:
        current = 50
    return max(0, min(100, int(current) + delta))
