from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import queue
import shutil
import time
from threading import Event
from urllib.request import urlretrieve
import zipfile

from .commands import normalize_text


logger = logging.getLogger(__name__)
DEFAULT_SPANISH_MODEL_NAME = "vosk-model-small-es-0.42"
DEFAULT_SPANISH_MODEL_URL = f"https://alphacephei.com/vosk/models/{DEFAULT_SPANISH_MODEL_NAME}.zip"


class VoiceRecognitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class VoiceCaptureConfig:
    model_path: Path
    sample_rate: int = 16000
    timeout_seconds: int = 8


class VoskVoiceRecognizer:
    def __init__(self, config: VoiceCaptureConfig) -> None:
        self.config = config

    def listen_once(self) -> str:
        logger.info("listen_once starting; model_path=%s", self.config.model_path)
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            raise VoiceRecognitionError(
                "Voice dependencies are not installed. Run `python -m pip install -r requirements.txt`."
            ) from error

        if not self.config.model_path.exists():
            raise VoiceRecognitionError(f"Vosk model not found: {self.config.model_path}")

        audio_queue: queue.Queue[bytes] = queue.Queue()
        model = Model(str(self.config.model_path))
        recognizer = KaldiRecognizer(model, self.config.sample_rate)

        def callback(indata, frames, time_info, status) -> None:
            if status:
                return
            audio_queue.put(bytes(indata))

        deadline = time.monotonic() + self.config.timeout_seconds
        with sd.RawInputStream(
            samplerate=self.config.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            logger.info("listen_once audio stream opened")
            while time.monotonic() < deadline:
                try:
                    data = audio_queue.get(timeout=0.25)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    logger.info("listen_once final result=%r", text)
                    if text:
                        return text

        final = json.loads(recognizer.FinalResult())
        text = final.get("text", "").strip()
        logger.info("listen_once timeout result=%r", text)
        return text

    def listen_until_activation(
        self,
        wake_word: str,
        stop_event: Event,
        manual_event: Event,
    ) -> str | None:
        logger.info("listen_until_activation starting; wake_word=%r model_path=%s", wake_word, self.config.model_path)
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError as error:
            raise VoiceRecognitionError(
                "Voice dependencies are not installed. Run `python -m pip install -r requirements.txt`."
            ) from error

        if not self.config.model_path.exists():
            raise VoiceRecognitionError(f"Vosk model not found: {self.config.model_path}")

        audio_queue: queue.Queue[bytes] = queue.Queue()
        model = Model(str(self.config.model_path))
        recognizer = KaldiRecognizer(model, self.config.sample_rate)
        normalized_wake_word = normalize_text(wake_word)

        def callback(indata, frames, time_info, status) -> None:
            if status:
                return
            audio_queue.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=self.config.sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            logger.info("wake audio stream opened")
            while not stop_event.is_set():
                if manual_event.is_set():
                    manual_event.clear()
                    logger.info("wake listener manually activated")
                    return ""

                try:
                    data = audio_queue.get(timeout=0.25)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    logger.info("wake final result=%r", text)
                    if _contains_wake_word(text, normalized_wake_word):
                        return text
                else:
                    partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                    if _contains_wake_word(partial, normalized_wake_word):
                        logger.info("wake partial result=%r", partial)
                        return partial

        logger.info("wake listener stopped")
        return None


def download_spanish_model(
    model_path: Path,
    url: str = DEFAULT_SPANISH_MODEL_URL,
    force: bool = False,
) -> Path:
    if model_path.exists() and not force:
        return model_path

    if model_path.exists() and force:
        shutil.rmtree(model_path)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = model_path.parent / f"{DEFAULT_SPANISH_MODEL_NAME}.zip"
    extract_root = model_path.parent / ".download"

    if extract_root.exists():
        shutil.rmtree(extract_root)

    try:
        urlretrieve(url, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_root)

        extracted_model = extract_root / DEFAULT_SPANISH_MODEL_NAME
        if not extracted_model.exists():
            raise VoiceRecognitionError(f"Downloaded archive did not contain {DEFAULT_SPANISH_MODEL_NAME}.")

        if model_path.exists():
            shutil.rmtree(model_path)
        shutil.move(str(extracted_model), str(model_path))
        return model_path
    finally:
        if archive_path.exists():
            archive_path.unlink()
        if extract_root.exists():
            shutil.rmtree(extract_root)


def command_after_wake_word(text: str, wake_word: str) -> str:
    normalized = normalize_text(text)
    normalized_wake_word = normalize_text(wake_word)
    if not normalized or not normalized_wake_word:
        return ""

    parts = normalized.split(normalized_wake_word, 1)
    if len(parts) != 2:
        return ""
    return parts[1].strip()


def _contains_wake_word(text: str, normalized_wake_word: str) -> bool:
    return bool(normalized_wake_word and normalized_wake_word in normalize_text(text))
