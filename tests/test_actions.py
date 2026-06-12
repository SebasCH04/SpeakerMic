import unittest

from speakermic.actions import execute_command
from speakermic.commands import CommandType, VoiceCommand


class FakeSpotifyClient:
    def __init__(self):
        self.calls = []
        self.state = {"device": {"volume_percent": 40}}

    def pause(self, device_id=None):
        self.calls.append(("pause", device_id))

    def play(self, device_id=None, payload=None):
        self.calls.append(("play", device_id, payload))

    def next_track(self, device_id=None):
        self.calls.append(("next", device_id))

    def previous_track(self, device_id=None):
        self.calls.append(("previous", device_id))

    def set_volume(self, percent, device_id=None):
        self.calls.append(("volume", percent, device_id))

    def playback_state(self):
        return self.state

    def search_first_uri(self, query, item_type):
        self.calls.append(("search", query, item_type))
        return f"spotify:{item_type}:123"


class ExecuteCommandTests(unittest.TestCase):
    def test_pause(self):
        client = FakeSpotifyClient()
        message = execute_command(client, VoiceCommand(CommandType.PAUSE), "device-1")
        self.assertEqual(message, "Paused Spotify.")
        self.assertEqual(client.calls, [("pause", "device-1")])

    def test_volume_up_uses_current_state(self):
        client = FakeSpotifyClient()
        execute_command(client, VoiceCommand(CommandType.VOLUME_UP), "device-1", volume_step=15)
        self.assertEqual(client.calls, [("volume", 55, "device-1")])

    def test_track_search_and_play(self):
        client = FakeSpotifyClient()
        execute_command(client, VoiceCommand(CommandType.PLAY_TRACK, "test song"), "device-1")
        self.assertEqual(
            client.calls,
            [
                ("search", "test song", "track"),
                ("play", "device-1", {"uris": ["spotify:track:123"]}),
            ],
        )


if __name__ == "__main__":
    unittest.main()
