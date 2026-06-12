import unittest

from speakermic.spotify import SpotifyApiError, SpotifyAuthError, _decode_success_response, needs_spotify_login


class SpotifyResponseTests(unittest.TestCase):
    def test_empty_success_response(self):
        self.assertEqual(_decode_success_response(b""), {})

    def test_whitespace_success_response(self):
        self.assertEqual(_decode_success_response(b"  \n"), {})

    def test_json_success_response(self):
        self.assertEqual(_decode_success_response(b'{"ok": true}'), {"ok": True})

    def test_non_json_success_response(self):
        self.assertEqual(_decode_success_response(b"OK"), {})

    def test_auth_error_needs_login(self):
        self.assertTrue(needs_spotify_login(SpotifyAuthError("Not logged in.")))

    def test_revoked_refresh_token_needs_login(self):
        error = SpotifyApiError(400, "Spotify API error 400: Refresh token revoked")

        self.assertTrue(needs_spotify_login(error))

    def test_restriction_error_does_not_need_login(self):
        error = SpotifyApiError(403, "Spotify API error 403: Restriction violated")

        self.assertFalse(needs_spotify_login(error))


if __name__ == "__main__":
    unittest.main()
