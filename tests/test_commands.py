import unittest

from speakermic.commands import CommandType, parse_command


class CommandParserTests(unittest.TestCase):
    def test_pause_variants(self):
        self.assertEqual(parse_command("pausa").type, CommandType.PAUSE)
        self.assertEqual(parse_command("por favor detener musica").type, CommandType.PAUSE)
        self.assertEqual(parse_command("silencio").type, CommandType.PAUSE)
        self.assertEqual(parse_command("alto").type, CommandType.PAUSE)
        self.assertEqual(parse_command("pausalo").type, CommandType.PAUSE)

    def test_transport_commands(self):
        self.assertEqual(parse_command("siguiente cancion").type, CommandType.NEXT)
        self.assertEqual(parse_command("cancion anterior").type, CommandType.PREVIOUS)
        self.assertEqual(parse_command("continua").type, CommandType.PLAY)
        self.assertEqual(parse_command("quita pausa").type, CommandType.PLAY)
        self.assertEqual(parse_command("pon musica").type, CommandType.PLAY)
        self.assertEqual(parse_command("pasala").type, CommandType.NEXT)
        self.assertEqual(parse_command("devuelve").type, CommandType.PREVIOUS)

    def test_english_transport_commands(self):
        self.assertEqual(parse_command("play").type, CommandType.PLAY)
        self.assertEqual(parse_command("resume music").type, CommandType.PLAY)
        self.assertEqual(parse_command("pause").type, CommandType.PAUSE)
        self.assertEqual(parse_command("stop music").type, CommandType.PAUSE)
        self.assertEqual(parse_command("next song").type, CommandType.NEXT)
        self.assertEqual(parse_command("skip track").type, CommandType.NEXT)
        self.assertEqual(parse_command("previous song").type, CommandType.PREVIOUS)
        self.assertEqual(parse_command("go back").type, CommandType.PREVIOUS)

    def test_common_transcription_errors(self):
        self.assertEqual(parse_command("produir").type, CommandType.PLAY)
        self.assertEqual(parse_command("repoducir").type, CommandType.PLAY)
        self.assertEqual(parse_command("sigiente").type, CommandType.NEXT)
        self.assertEqual(parse_command("proxina").type, CommandType.NEXT)

    def test_volume_number(self):
        command = parse_command("volumen a 35")
        self.assertEqual(command.type, CommandType.SET_VOLUME)
        self.assertEqual(command.value, 35)

    def test_volume_word(self):
        command = parse_command("pon volumen cincuenta")
        self.assertEqual(command.type, CommandType.SET_VOLUME)
        self.assertEqual(command.value, 50)

    def test_relative_volume_variants(self):
        self.assertEqual(parse_command("aumenta volumen").type, CommandType.VOLUME_UP)
        self.assertEqual(parse_command("subir volumen").type, CommandType.VOLUME_UP)
        self.assertEqual(parse_command("disminuye volumen").type, CommandType.VOLUME_DOWN)
        self.assertEqual(parse_command("bajar volumen").type, CommandType.VOLUME_DOWN)
        self.assertEqual(parse_command("volume up").type, CommandType.VOLUME_UP)
        self.assertEqual(parse_command("lower volume").type, CommandType.VOLUME_DOWN)

    def test_english_volume_word(self):
        command = parse_command("set volume to fifty")
        self.assertEqual(command.type, CommandType.SET_VOLUME)
        self.assertEqual(command.value, 50)

    def test_volume_is_clamped(self):
        command = parse_command("volumen 500")
        self.assertEqual(command.value, 100)

    def test_track_request(self):
        command = parse_command("pon cancion blinding lights")
        self.assertEqual(command.type, CommandType.PLAY_TRACK)
        self.assertEqual(command.value, "blinding lights")

    def test_english_track_request(self):
        command = parse_command("play song blinding lights")
        self.assertEqual(command.type, CommandType.PLAY_TRACK)
        self.assertEqual(command.value, "blinding lights")

    def test_playlist_request(self):
        command = parse_command("pon playlist rock clasico")
        self.assertEqual(command.type, CommandType.PLAY_PLAYLIST)
        self.assertEqual(command.value, "rock clasico")

    def test_english_playlist_request(self):
        command = parse_command("play playlist rock classics")
        self.assertEqual(command.type, CommandType.PLAY_PLAYLIST)
        self.assertEqual(command.value, "rock classics")

    def test_unknown_command(self):
        self.assertIsNone(parse_command("hola como estas"))


if __name__ == "__main__":
    unittest.main()
