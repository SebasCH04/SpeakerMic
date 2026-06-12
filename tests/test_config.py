from pathlib import Path
import tempfile
import unittest

from speakermic.config import load_config


class ConfigTests(unittest.TestCase):
    def test_missing_config_uses_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")

        self.assertEqual(config.app.hotkey, "<ctrl>+<alt>+<space>")
        self.assertEqual(config.spotify.redirect_uri, "http://127.0.0.1:8888/callback")
        self.assertTrue(config.speech.enabled)
        self.assertEqual(config.speech.voice_name_contains, "latin")
        self.assertFalse(config.activation.wake_word_enabled)
        self.assertEqual(config.activation.wake_word, "consola")

    def test_config_file_overrides_values(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.toml"
            config_path.write_text(
                """
[app]
hotkey = "<ctrl>+<shift>+m"
voice_model_path = "models/es"
volume_step = 5

[spotify]
client_id = "abc123"
preferred_device_name = "Speakers"

[speech]
enabled = false
voice_name_contains = "Sabina"
rate = 150
volume = 0.8

[activation]
wake_word_enabled = true
wake_word = "computadora"
""",
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.app.hotkey, "<ctrl>+<shift>+m")
        self.assertEqual(config.app.voice_model_path, Path("models/es"))
        self.assertEqual(config.app.volume_step, 5)
        self.assertEqual(config.spotify.client_id, "abc123")
        self.assertEqual(config.spotify.preferred_device_name, "Speakers")
        self.assertFalse(config.speech.enabled)
        self.assertEqual(config.speech.voice_name_contains, "Sabina")
        self.assertEqual(config.speech.rate, 150)
        self.assertEqual(config.speech.volume, 0.8)
        self.assertTrue(config.activation.wake_word_enabled)
        self.assertEqual(config.activation.wake_word, "computadora")


if __name__ == "__main__":
    unittest.main()
