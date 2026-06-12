import unittest

from speakermic.commands import CommandType, parse_command


class CommandParserTests(unittest.TestCase):
    def test_pause_variants(self):
        self.assertEqual(parse_command("pausa").type, CommandType.PAUSE)
        self.assertEqual(parse_command("por favor detener musica").type, CommandType.PAUSE)

    def test_transport_commands(self):
        self.assertEqual(parse_command("siguiente cancion").type, CommandType.NEXT)
        self.assertEqual(parse_command("cancion anterior").type, CommandType.PREVIOUS)
        self.assertEqual(parse_command("continua").type, CommandType.PLAY)

    def test_volume_number(self):
        command = parse_command("volumen a 35")
        self.assertEqual(command.type, CommandType.SET_VOLUME)
        self.assertEqual(command.value, 35)

    def test_volume_word(self):
        command = parse_command("pon volumen cincuenta")
        self.assertEqual(command.type, CommandType.SET_VOLUME)
        self.assertEqual(command.value, 50)

    def test_volume_is_clamped(self):
        command = parse_command("volumen 500")
        self.assertEqual(command.value, 100)

    def test_track_request(self):
        command = parse_command("pon cancion blinding lights")
        self.assertEqual(command.type, CommandType.PLAY_TRACK)
        self.assertEqual(command.value, "blinding lights")

    def test_playlist_request(self):
        command = parse_command("pon playlist rock clasico")
        self.assertEqual(command.type, CommandType.PLAY_PLAYLIST)
        self.assertEqual(command.value, "rock clasico")

    def test_unknown_command(self):
        self.assertIsNone(parse_command("hola como estas"))


if __name__ == "__main__":
    unittest.main()
