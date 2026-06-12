import unittest

from speakermic.config import SpeechConfig
from speakermic.speech import (
    NullSpeaker,
    SystemSpeaker,
    WindowsPowerShellSpeaker,
    _powershell_single_quoted,
    _powershell_speech_command,
    spoken_message,
)


class FakeEngine:
    def __init__(self):
        self.messages = []
        self.properties = {}
        self.voices = []

    def setProperty(self, name, value):  # noqa: N802
        self.properties[name] = value

    def getProperty(self, name):  # noqa: N802
        if name == "voices":
            return self.voices
        return self.properties.get(name)

    def say(self, message):
        self.messages.append(message)

    def runAndWait(self):  # noqa: N802
        return


class SpeechTests(unittest.TestCase):
    def test_null_speaker_does_nothing(self):
        NullSpeaker().say("anything")
        NullSpeaker().close()

    def test_system_speaker_speaks_more_than_once(self):
        engine = FakeEngine()
        speaker = SystemSpeaker(SpeechConfig(enabled=True), engine_factory=lambda: engine)
        try:
            speaker.say("primero")
            speaker.say("segundo")
        finally:
            speaker.close()

        self.assertEqual(engine.messages, ["primero", "segundo"])

    def test_windows_speaker_invokes_runner_each_time(self):
        calls = []
        speaker = WindowsPowerShellSpeaker(SpeechConfig(enabled=True), runner=lambda *args, **kwargs: calls.append(args))

        speaker.say("primero")
        speaker.say("segundo")

        self.assertEqual(len(calls), 2)

    def test_powershell_quote_escapes_single_quotes(self):
        self.assertEqual(_powershell_single_quoted("pa'lante"), "'pa''lante'")

    def test_powershell_command_contains_message(self):
        command = _powershell_speech_command("No entendi", 175, 1.0, "spanish")
        self.assertIn("$speaker.Speak('No entendi')", command)

    def test_transport_messages_are_translated(self):
        self.assertEqual(spoken_message("Paused Spotify."), "Pausado.")
        self.assertEqual(spoken_message("Resumed Spotify."), "Reproduciendo.")
        self.assertEqual(spoken_message("Skipped to next track."), "Siguiente cancion.")

    def test_volume_message_is_translated(self):
        self.assertEqual(spoken_message("Set volume to 40%."), "Volumen en 40 por ciento.")

    def test_track_message_is_translated(self):
        self.assertEqual(spoken_message("Playing track: PIENSALO"), "Reproduciendo PIENSALO.")


if __name__ == "__main__":
    unittest.main()
