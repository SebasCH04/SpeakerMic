# SpeakerMic

SpeakerMic lets you control Spotify on Windows with your headset microphone. It can run
as a tray app, react to a hotkey, or listen for a wake word like `consola`.

It uses Spotify's official API, offline voice recognition with Vosk, and local Windows
text-to-speech. There is no paid speech API and no paid API usage, but Spotify playback
control requires a Spotify Premium account.

## What It Can Do

- Pause, resume, skip, go back, and change Spotify volume.
- Play a song or playlist by voice.
- Listen with `Ctrl+Alt+Space`.
- Optionally listen for a wake word like `consola`.
- Speak back when it understood, failed, or completed a command.
- Run from source, hidden in the tray, or as a local `SpeakerMic.exe`.

Example voice commands:

```text
pausa
sigue
siguiente
anterior
volumen a cuarenta
sube volumen
baja volumen
pon cancion blinding lights
pon playlist rock clasico
```

## Requirements

- Windows.
- Python 3.11 or newer.
- Spotify Premium.
- Spotify Desktop or Web open at least once so Spotify sees your PC as a playback device.
- A microphone Windows can use as input.
- A speaker/headset Windows can use as output.

## Setup From Source

Open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m speakermic init-config
```

Create a Spotify app:

1. Go to <https://developer.spotify.com/dashboard>.
2. Create an app named `SpeakerMic`.
3. Add this redirect URI:

```text
http://127.0.0.1:8888/callback
```

4. Copy the app's `Client ID`.
5. Paste it into `config.toml`:

```toml
[spotify]
client_id = "paste-your-spotify-client-id-here"
redirect_uri = "http://127.0.0.1:8888/callback"
preferred_device_name = ""
```

Then log in and check Spotify:

```powershell
python -m speakermic spotify-login
python -m speakermic spotify-status
```

Download the offline Spanish voice model:

```powershell
python -m speakermic download-model
```

## First Tests

Test Spotify without the microphone:

```powershell
python -m speakermic run-text "sigue"
python -m speakermic run-text "pausa"
python -m speakermic run-text "siguiente"
python -m speakermic run-text "volumen a 40"
```

Test the microphone:

```powershell
python -m speakermic listen-once
```

Say `pausa` or `volumen a cuarenta`. If it prints what you said, test the full flow:

```powershell
python -m speakermic listen-command
```

Test the spoken response:

```powershell
python -m speakermic speak-test
```

## Use The Tray App

Run:

```powershell
python -m speakermic tray
```

This keeps SpeakerMic running. Use `Ctrl+Alt+Space`, say a command, and Spotify should
react. Quit from the tray icon menu or press `Ctrl+C` in that terminal.

To enable wake word mode, edit `config.toml`:

```toml
[activation]
wake_word_enabled = true
wake_word = "consola"
```

Then start the tray app again. You can say:

```text
consola
```

Wait for `Te escucho`, then say:

```text
pausa
```

You can also say both together:

```text
consola pausa
```

## Run Without A Terminal

After setup works, double-click:

```text
scripts\start_speakermic_hidden.vbs
```

To run with visible logs:

```powershell
.\scripts\start_speakermic_debug.ps1
```

To stop a hidden instance:

```powershell
.\scripts\stop_speakermic.ps1
```

To start SpeakerMic automatically with Windows:

```powershell
.\scripts\install_startup_shortcut.ps1
```

To remove startup:

```powershell
.\scripts\uninstall_startup_shortcut.ps1
```

## Build The EXE

Build a local app folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

The app is created at:

```text
dist\SpeakerMic\SpeakerMic.exe
```

The build copies your local `config.toml`, `.speakermic_tokens.json`, and `models\`
folder next to the exe. Keep the whole `dist\SpeakerMic\` folder together.

Run the built app:

```powershell
.\scripts\run_built_exe.ps1
```

or double-click `dist\SpeakerMic\SpeakerMic.exe`.

To start the built exe automatically with Windows:

```powershell
.\scripts\install_exe_startup_shortcut.ps1
```

## Troubleshooting

- If voice commands do nothing, close other SpeakerMic instances. Only one process should use the mic.
- If `listen-once` does nothing, close the tray app first.
- If Spotify commands fail, open Spotify and play a song manually once.
- If the exe fails silently, check:

```powershell
.\scripts\show_built_log.ps1
```

- If PowerShell blocks a script, run it with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

## Audio Notes

Set your headset microphone as Windows input and your speaker as Windows output. If your
headset has a single combined plug but your PC has separate mic/headphone ports, use a
TRRS splitter and connect the mic side as input.

## Repository Safety

Do not commit local runtime files:

- `config.toml`
- `.speakermic_tokens.json`
- `models\`
- `dist\`
- `.venv\`

These are ignored by `.gitignore`. Share `config.example.toml` and the source files
instead.

## Development Check

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```
