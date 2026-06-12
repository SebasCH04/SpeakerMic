import unittest

from speakermic.spotify import _decode_success_response


class SpotifyResponseTests(unittest.TestCase):
    def test_empty_success_response(self):
        self.assertEqual(_decode_success_response(b""), {})

    def test_whitespace_success_response(self):
        self.assertEqual(_decode_success_response(b"  \n"), {})

    def test_json_success_response(self):
        self.assertEqual(_decode_success_response(b'{"ok": true}'), {"ok": True})

    def test_non_json_success_response(self):
        self.assertEqual(_decode_success_response(b"OK"), {})


if __name__ == "__main__":
    unittest.main()
