"""test_audio_facade.py — Pattern Facade: AudioManager (AUD_01...12)."""
import unittest
import base_setup  # noqa: F401 — headless SDL + sys.path
from game.audio.audio_manager import AudioManager


class TestAudioFacade(unittest.TestCase):

    def setUp(self):
        self.audio = AudioManager()
        self.audio.initialize()

    def tearDown(self):
        try:
            self.audio.shutdown()
        except Exception:
            pass

    def test_AUD_01_initialize_sets_mixer_ready(self):
        """AUD_01 — AudioManager.initialize() Mixer pronto."""
        am = AudioManager()
        am.initialize()
        self.assertTrue(am._mixer_ready)
        am.shutdown()

    def test_AUD_02_play_music_registered_key(self):
        """AUD_02 — play_music su traccia registrata, nessuna eccezione."""
        self.audio.load_music("explore", "/fake/explore.ogg")
        self.audio.play_music("explore")

    def test_AUD_03_play_music_unknown_key_no_raise(self):
        """AUD_03 — play_music(nonexistent) nessuna eccezione."""
        self.audio.play_music("nonexistent")

    def test_AUD_04_stop_music_no_raise(self):
        """AUD_04 — stop_music() nessuna eccezione."""
        self.audio.stop_music(fade_ms=0)

    def test_AUD_05_play_sound_unknown_key_no_raise(self):
        """AUD_05 — play_sound(shot) nessuna eccezione."""
        self.audio.play_sound("shot")

    def test_AUD_06_stop_sound_no_raise(self):
        """AUD_06 — stop_sound(shot) nessuna eccezione."""
        self.audio.stop_sound("shot")

    def test_AUD_07_stop_all_sounds_no_raise(self):
        """AUD_07 — stop_all_sounds() nessuna eccezione."""
        self.audio.stop_all_sounds()

    def test_AUD_08_stop_all_no_raise(self):
        """AUD_08 — stop_all() nessuna eccezione."""
        self.audio.stop_all(fade_ms=0)

    def test_AUD_09_set_music_volume(self):
        """AUD_09 — set_music_volume(0.5) music_volume==0.5."""
        try:
            self.audio.set_music_volume(0.5)
        except Exception:
            pass
        self.assertEqual(self.audio.music_volume, 0.5)

    def test_AUD_10_set_sfx_volume(self):
        """AUD_10 — set_sfx_volume(0.3) sfx_volume==0.3."""
        self.audio.set_sfx_volume(0.3)
        self.assertEqual(self.audio.sfx_volume, 0.3)

    def test_AUD_11_apply_for_screen_battle_no_raise(self):
        """AUD_11 — apply_for_screen(battle) nessuna eccezione."""
        self.audio.apply_for_screen("battle")

    def test_AUD_12_shutdown_clears_mixer_ready(self):
        """AUD_12 — AudioManager.shutdown() mixer_ready==False."""
        self.audio.shutdown()
        self.assertFalse(self.audio._mixer_ready)


if __name__ == "__main__":
    unittest.main()