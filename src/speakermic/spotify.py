from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import webbrowser


SPOTIFY_ACCOUNTS_URL = "https://accounts.spotify.com"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
TOKEN_CACHE_PATH = Path(".speakermic_tokens.json")
SCOPES = (
    "user-read-private",
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
)


@dataclass(frozen=True)
class SpotifyDevice:
    id: str
    name: str
    is_active: bool


class SpotifyAuthError(RuntimeError):
    pass


class SpotifyApiError(RuntimeError):
    def __init__(self, status_code: int | None, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


class SpotifyClient:
    def __init__(
        self,
        client_id: str,
        redirect_uri: str,
        token_cache_path: Path = TOKEN_CACHE_PATH,
    ) -> None:
        if not client_id or "paste-your" in client_id:
            raise SpotifyAuthError("Missing Spotify client_id in config.toml.")

        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.token_cache_path = token_cache_path

    def login(self) -> None:
        verifier = _code_verifier()
        challenge = _code_challenge(verifier)
        state = secrets.token_urlsafe(24)
        callback = _LocalCallbackServer(self.redirect_uri, state)

        params = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "scope": " ".join(SCOPES),
                "redirect_uri": self.redirect_uri,
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": challenge,
            }
        )
        webbrowser.open(f"{SPOTIFY_ACCOUNTS_URL}/authorize?{params}")
        code = callback.wait_for_code()
        tokens = self._token_request(
            {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": verifier,
            }
        )
        self._save_tokens(tokens)

    def pause(self, device_id: str | None = None) -> None:
        self._api_request("PUT", "/me/player/pause", query=_device_query(device_id))

    def play(self, device_id: str | None = None, payload: dict[str, Any] | None = None) -> None:
        self._api_request("PUT", "/me/player/play", query=_device_query(device_id), payload=payload)

    def next_track(self, device_id: str | None = None) -> None:
        self._api_request("POST", "/me/player/next", query=_device_query(device_id))

    def previous_track(self, device_id: str | None = None) -> None:
        self._api_request("POST", "/me/player/previous", query=_device_query(device_id))

    def set_volume(self, percent: int, device_id: str | None = None) -> None:
        percent = max(0, min(100, percent))
        query = {"volume_percent": str(percent), **_device_query(device_id)}
        self._api_request("PUT", "/me/player/volume", query=query)

    def playback_state(self) -> dict[str, Any]:
        return self._api_request("GET", "/me/player")

    def current_user(self) -> dict[str, Any]:
        return self._api_request("GET", "/me")

    def devices(self) -> list[SpotifyDevice]:
        data = self._api_request("GET", "/me/player/devices")
        return [
            SpotifyDevice(id=item["id"], name=item["name"], is_active=item["is_active"])
            for item in data.get("devices", [])
        ]

    def search_first_uri(self, query: str, item_type: str) -> str | None:
        data = self._api_request("GET", "/search", query={"q": query, "type": item_type, "limit": "1"})
        items = data.get(f"{item_type}s", {}).get("items", [])
        if not items:
            return None
        return items[0].get("uri")

    def _api_request(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = self._access_token()
        url = f"{SPOTIFY_API_URL}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {token}"}
        if body is not None:
            headers["Content-Type"] = "application/json"

        request = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                content = response.read()
                return _decode_success_response(content)
        except HTTPError as error:
            raise _spotify_http_error(error) from error
        except URLError as error:
            raise SpotifyApiError(None, f"Could not reach Spotify: {error.reason}") from error

    def preferred_or_active_device_id(self, preferred_name: str = "") -> str | None:
        devices = self.devices()
        if preferred_name:
            preferred_name = preferred_name.lower()
            for device in devices:
                if preferred_name in device.name.lower():
                    return device.id

        for device in devices:
            if device.is_active:
                return device.id

        return devices[0].id if devices else None

    def _access_token(self) -> str:
        tokens = self._load_tokens()
        expires_at = float(tokens.get("expires_at", 0))
        if time.time() >= expires_at - 60:
            tokens = self._refresh_tokens(tokens)
        return tokens["access_token"]

    def _refresh_tokens(self, tokens: dict[str, Any]) -> dict[str, Any]:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise SpotifyAuthError("Missing refresh token. Run login again.")
        refreshed = self._token_request(
            {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )
        refreshed.setdefault("refresh_token", refresh_token)
        self._save_tokens(refreshed)
        return refreshed

    def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{SPOTIFY_ACCOUNTS_URL}/api/token",
            data=urlencode(form).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                tokens = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise _spotify_http_error(error) from error
        except URLError as error:
            raise SpotifyApiError(None, f"Could not reach Spotify: {error.reason}") from error
        tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 3600))
        return tokens

    def _load_tokens(self) -> dict[str, Any]:
        if not self.token_cache_path.exists():
            raise SpotifyAuthError("Not logged in. Run `python -m speakermic spotify-login`.")
        return json.loads(self.token_cache_path.read_text(encoding="utf-8"))

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        self.token_cache_path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


class _LocalCallbackServer:
    def __init__(self, redirect_uri: str, expected_state: str) -> None:
        parsed = urlparse(redirect_uri)
        self.expected_state = expected_state
        self.code: str | None = None
        self.error: str | None = None
        self.server = HTTPServer((parsed.hostname or "127.0.0.1", parsed.port or 8888), self._handler())

    def wait_for_code(self) -> str:
        thread = Thread(target=self.server.handle_request, daemon=True)
        thread.start()
        thread.join(timeout=120)
        self.server.server_close()

        if self.error:
            raise SpotifyAuthError(self.error)
        if not self.code:
            raise SpotifyAuthError("Timed out waiting for Spotify login callback.")
        return self.code

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                params = parse_qs(urlparse(self.path).query)
                state = params.get("state", [""])[0]
                if state != parent.expected_state:
                    parent.error = "Spotify callback state did not match."
                    self._respond("SpeakerMic login failed. You can close this tab.")
                    return

                parent.code = params.get("code", [""])[0]
                parent.error = params.get("error", [None])[0]
                self._respond("SpeakerMic login complete. You can close this tab.")

            def log_message(self, format: str, *args: object) -> None:
                return

            def _respond(self, message: str) -> None:
                body = message.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return CallbackHandler


def _device_query(device_id: str | None) -> dict[str, str]:
    return {} if not device_id else {"device_id": device_id}


def _code_verifier() -> str:
    return secrets.token_urlsafe(64)[:96]


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _spotify_http_error(error: HTTPError) -> SpotifyApiError:
    body = error.read().decode("utf-8", errors="replace")
    message = body or error.reason
    try:
        data = json.loads(body)
        api_error = data.get("error", {})
        if isinstance(api_error, dict):
            message = api_error.get("message") or message
        elif isinstance(api_error, str):
            message = data.get("error_description") or api_error
    except json.JSONDecodeError:
        pass

    return SpotifyApiError(error.code, f"Spotify API error {error.code}: {message}")


def _decode_success_response(content: bytes) -> dict[str, Any]:
    if not content or not content.strip():
        return {}

    text = content.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def needs_spotify_login(error: Exception) -> bool:
    if isinstance(error, SpotifyAuthError):
        return True
    if not isinstance(error, SpotifyApiError):
        return False

    message = str(error).lower()
    return (
        error.status_code in {400, 401}
        and (
            "refresh token" in message
            or "invalid_grant" in message
            or "token expired" in message
            or "not logged in" in message
        )
    )
