import unittest

from speakermic.config import SpeechConfig
from speakermic.speech import (
    NullSpeaker,
    SystemSpeaker,
    WindowsPowerShellSpeaker,
    _select_voice,
    _powershell_single_quoted,
    _powershell_speech_command,
    spoken_message,
    voice_preference_terms,
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


class FakeVoice:
    def __init__(self, voice_id, name, languages=None):
        self.id = voice_id
        self.name = name
        self.languages = languages or []


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
        command = _powershell_speech_command("No entendi", 175, 1.0, "latin")
        self.assertIn("$message = 'No entendi'", command)
        self.assertIn("$speaker.Speak($message)", command)

    def test_latin_voice_terms_prefer_mexican_spanish(self):
        terms = voice_preference_terms("latin")

        self.assertLess(terms.index("es-mx"), terms.index("spanish"))

    def test_specific_modern_voice_line_prefers_voice_name(self):
        terms = voice_preference_terms("Microsoft Raul [es-MX] Male (modern)")

        self.assertLess(terms.index("raul"), terms.index("es-mx"))

    def test_select_voice_prefers_latin_before_generic_spanish(self):
        engine = FakeEngine()
        engine.voices = [
            FakeVoice("generic", "Microsoft Spanish Voice", ["es-ES"]),
            FakeVoice("sabina", "Microsoft Sabina", ["es-MX"]),
        ]

        _select_voice(engine, "latin")

        self.assertEqual(engine.properties["voice"], "sabina")

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
