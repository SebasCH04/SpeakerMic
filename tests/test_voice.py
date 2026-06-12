from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from speakermic.voice import DEFAULT_SPANISH_MODEL_NAME, command_after_wake_word, download_spanish_model


class VoiceModelDownloadTests(unittest.TestCase):
    def test_existing_model_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / DEFAULT_SPANISH_MODEL_NAME
            model_path.mkdir()

            with patch("speakermic.voice.urlretrieve") as urlretrieve:
                result = download_spanish_model(model_path)

            self.assertEqual(result, model_path)
            urlretrieve.assert_not_called()

    def test_downloaded_model_is_extracted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_zip = root / "source.zip"
            model_path = root / "models" / DEFAULT_SPANISH_MODEL_NAME

            with zipfile.ZipFile(source_zip, "w") as archive:
                archive.writestr(f"{DEFAULT_SPANISH_MODEL_NAME}/README", "model")

            def fake_urlretrieve(url, filename):
                Path(filename).write_bytes(source_zip.read_bytes())
                return filename, None

            with patch("speakermic.voice.urlretrieve", side_effect=fake_urlretrieve):
                result = download_spanish_model(model_path)

            self.assertEqual(result, model_path)
            self.assertTrue((model_path / "README").exists())


class WakeWordTests(unittest.TestCase):
    def test_command_after_wake_word(self):
        self.assertEqual(command_after_wake_word("consola pausa", "consola"), "pausa")

    def test_command_after_wake_word_handles_accents(self):
        self.assertEqual(command_after_wake_word("c\u00f3nsola volumen a cuarenta", "consola"), "volumen a cuarenta")

    def test_command_after_wake_word_returns_empty_when_missing(self):
        self.assertEqual(command_after_wake_word("pausa", "consola"), "")


if __name__ == "__main__":
    unittest.main()
