from __future__ import annotations

from dataclasses import dataclass, field
import os
import queue
import re
import subprocess
from threading import Event, Thread
from typing import Any, Callable

from .config import SpeechConfig


class SpeakerError(RuntimeError):
    pass


@dataclass
class WindowsPowerShellSpeaker:
    config: SpeechConfig
    runner: Callable[..., Any] = subprocess.run

    def say(self, message: str) -> None:
        if not self.config.enabled or not message:
            return

        command = _powershell_speech_command(
            message,
            self.config.rate,
            self.config.volume,
            self.config.voice_name_contains,
        )
        kwargs = {
            "check": False,
            "capture_output": True,
            "text": True,
        }
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        self.runner(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            **kwargs,
        )

    def close(self) -> None:
        return


@dataclass
class SystemSpeaker:
    config: SpeechConfig
    engine_factory: Callable[[], Any] | None = None
    _queue: queue.Queue = field(init=False, repr=False)
    _thread: Thread = field(init=False, repr=False)
    _ready: Event = field(init=False, repr=False)
    _startup_error: SpeakerError | None = field(default=None, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.config.enabled:
            return

        self._queue = queue.Queue()
        self._ready = Event()
        self._thread = Thread(target=self._run, name="SpeakerMicSpeech", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=10)
        if self._startup_error is not None:
            raise self._startup_error

    def say(self, message: str) -> None:
        if not self.config.enabled or not message or self._closed:
            return

        done = Event()
        self._queue.put((message, done))
        done.wait(timeout=20)

    def close(self) -> None:
        if not self.config.enabled or self._closed:
            return

        self._closed = True
        self._queue.put((None, None))
        self._thread.join(timeout=5)

    def _run(self) -> None:
        try:
            engine = self._create_engine()
            engine.setProperty("rate", self.config.rate)
            engine.setProperty("volume", max(0.0, min(1.0, self.config.volume)))
            _select_voice(engine, self.config.voice_name_contains)
        except SpeakerError as error:
            self._startup_error = error
            self._ready.set()
            return

        self._ready.set()
        while True:
            message, done = self._queue.get()
            if message is None:
                return

            try:
                engine.say(message)
                engine.runAndWait()
            finally:
                done.set()

    def _create_engine(self):
        if self.engine_factory is not None:
            return self.engine_factory()

        try:
            import pyttsx3
        except ImportError as error:
            raise SpeakerError("Speech dependency is not installed. Run `python -m pip install -r requirements.txt`.") from error

        return pyttsx3.init()


class NullSpeaker:
    def say(self, message: str) -> None:
        return

    def close(self) -> None:
        return


def create_speaker(config: SpeechConfig) -> SystemSpeaker | NullSpeaker:
    if not config.enabled:
        return NullSpeaker()

    if os.name == "nt":
        return WindowsPowerShellSpeaker(config)

    try:
        return SystemSpeaker(config)
    except SpeakerError as error:
        print(f"Speech disabled: {error}")
        return NullSpeaker()


def spoken_message(message: str) -> str:
    translations = {
        "Paused Spotify.": "Pausado.",
        "Resumed Spotify.": "Reproduciendo.",
        "Skipped to next track.": "Siguiente cancion.",
        "Skipped to previous track.": "Cancion anterior.",
    }
    if message in translations:
        return translations[message]

    if message.startswith("Set volume to "):
        value = message.removeprefix("Set volume to ").removesuffix("%.")
        return f"Volumen en {value} por ciento."

    if message.startswith("Raised volume to "):
        value = message.removeprefix("Raised volume to ").removesuffix("%.")
        return f"Subi el volumen a {value} por ciento."

    if message.startswith("Lowered volume to "):
        value = message.removeprefix("Lowered volume to ").removesuffix("%.")
        return f"Baje el volumen a {value} por ciento."

    if message.startswith("Playing track: "):
        return f"Reproduciendo {message.removeprefix('Playing track: ')}."

    if message.startswith("Playing playlist: "):
        return f"Reproduciendo playlist {message.removeprefix('Playing playlist: ')}."

    if message.startswith("No track found for: "):
        return f"No encontre la cancion {message.removeprefix('No track found for: ')}."

    if message.startswith("No playlist found for: "):
        return f"No encontre la playlist {message.removeprefix('No playlist found for: ')}."

    return message


def voice_preference_terms(preferred_name: str) -> list[str]:
    preferred_name = preferred_name.lower().strip()
    latin_terms = [
        "es-mx",
        "mexico",
        "mexican",
        "sabina",
        "es-cr",
        "costa rica",
        "es-co",
        "colombia",
        "es-ar",
        "argentina",
        "es-cl",
        "chile",
        "es-pe",
        "peru",
        "es-ve",
        "venezuela",
        "es-us",
        "united states",
        "helena",
        "pablo",
        "laura",
        "latin",
        "latam",
        "latino",
        "latina",
    ]

    if not preferred_name:
        return []

    if preferred_name in {"spanish", "espanol", "español", "latin", "latam", "latino", "latina"}:
        return latin_terms + ["spanish", "es-"]

    specific_terms = [
        term
        for term in re.findall(r"[a-z]+(?:-[a-z]+)?", preferred_name)
        if term not in {"microsoft", "desktop", "modern", "male", "female", "voice"}
    ]
    return _unique_terms([preferred_name] + specific_terms + latin_terms + ["spanish", "es-"])


def _unique_terms(terms: list[str]) -> list[str]:
    unique = []
    for term in terms:
        if term and term not in unique:
            unique.append(term)
    return unique


def installed_windows_voices() -> list[str]:
    command = (
        "$voices = @(); "
        "try { "
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]; "
        "$voices += [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | "
        "ForEach-Object { \"$($_.DisplayName) [$($_.Language)] $($_.Gender) (modern)\" }; "
        "} catch {} "
        "try { "
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voices += $speaker.GetInstalledVoices() | ForEach-Object { "
        "\"$($_.VoiceInfo.Name) [$($_.VoiceInfo.Culture.Name)] (desktop)\" "
        "}; "
        "$speaker.Dispose(); "
        "} catch {} "
        "$voices | Select-Object -Unique;"
    )
    kwargs = {
        "check": False,
        "capture_output": True,
        "text": True,
    }
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        **kwargs,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _select_voice(engine, preferred_name: str) -> None:
    preferred_terms = voice_preference_terms(preferred_name)
    if not preferred_terms:
        return

    voices = engine.getProperty("voices")
    for preferred_term in preferred_terms:
        for voice in voices:
            name = getattr(voice, "name", "").lower()
            voice_id = getattr(voice, "id", "").lower()
            languages = " ".join(str(language).lower() for language in getattr(voice, "languages", []))
            if preferred_term in name or preferred_term in voice_id or preferred_term in languages:
                engine.setProperty("voice", voice.id)
                return


def _powershell_speech_command(message: str, rate: int, volume: float, preferred_name: str) -> str:
    escaped_message = _powershell_single_quoted(message)
    escaped_preferred_terms = ", ".join(_powershell_single_quoted(term) for term in voice_preference_terms(preferred_name))
    sapi_rate = max(-10, min(10, round((rate - 175) / 20)))
    sapi_volume = max(0, min(100, round(volume * 100)))

    return (
        "$ErrorActionPreference = 'Stop'; "
        f"$message = {escaped_message}; "
        f"$preferredTerms = @({escaped_preferred_terms}); "
        f"$sapiRate = {sapi_rate}; "
        f"$sapiVolume = {sapi_volume}; "
        "try { "
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]; "
        "$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]; "
        "$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { "
        "$_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and "
        "$_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 "
        "} | Select-Object -First 1; "
        "$voice = $null; "
        "foreach ($preferred in $preferredTerms) { "
        "$voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { "
        "$_.DisplayName.ToLower().Contains($preferred) -or "
        "$_.Language.ToLower().Contains($preferred) -or "
        "$_.Gender.ToString().ToLower().Contains($preferred) "
        "} | Select-Object -First 1; "
        "if ($voice) { break } "
        "} "
        "if ($voice) { "
        "$synth = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new(); "
        "$synth.Voice = $voice; "
        "$speechTask = $asTask.MakeGenericMethod([Windows.Media.SpeechSynthesis.SpeechSynthesisStream]).Invoke("
        "$null, @($synth.SynthesizeTextToStreamAsync($message))); "
        "$speechStream = $speechTask.GetAwaiter().GetResult(); "
        "$reader = [Windows.Storage.Streams.DataReader]::new($speechStream.GetInputStreamAt(0)); "
        "$size = [uint32]$speechStream.Size; "
        "$loadTask = $asTask.MakeGenericMethod([uint32]).Invoke($null, @($reader.LoadAsync($size))); "
        "$loadTask.GetAwaiter().GetResult() | Out-Null; "
        "$bytes = New-Object byte[] $size; "
        "$reader.ReadBytes($bytes); "
        "$temp = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), 'wav'); "
        "[System.IO.File]::WriteAllBytes($temp, $bytes); "
        "$player = New-Object System.Media.SoundPlayer($temp); "
        "$player.PlaySync(); "
        "$reader.Dispose(); "
        "$speechStream.Dispose(); "
        "$synth.Dispose(); "
        "Remove-Item -LiteralPath $temp -Force; "
        "exit 0; "
        "} "
        "} catch {} "
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speaker.Rate = $sapiRate; "
        "$speaker.Volume = $sapiVolume; "
        "foreach ($preferred in $preferredTerms) { "
        "$voice = $speaker.GetInstalledVoices() | Where-Object { "
        "$_.VoiceInfo.Name.ToLower().Contains($preferred) -or "
        "$_.VoiceInfo.Culture.Name.ToLower().Contains($preferred) "
        "} | Select-Object -First 1; "
        "if ($voice) { $speaker.SelectVoice($voice.VoiceInfo.Name); break } "
        "} "
        "$speaker.Speak($message); "
        "$speaker.Dispose();"
    )


def _powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
