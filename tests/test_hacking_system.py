"""test_hacking_system.py — HackingSystem (HACK_01…04, TMP_06…12)."""
import unittest
import base_setup  # noqa: F401
from game.systems.hacking_system import HackingSystem
from game.events.event_bus import EventBus

TERMINAL = "terminal_01"


class TestHackingSystem(unittest.TestCase):

    def setUp(self):
        self.hs = HackingSystem()
        self.hs.initialize(EventBus())

    def tearDown(self):
        self.hs.cleanup()

    def test_TMP_07_can_hack_initially_true(self):
        """TMP_07 — can_hack(terminal) True all'avvio."""
        ok, _ = self.hs.can_hack(TERMINAL)
        self.assertTrue(ok)

    def test_TMP_09_force_lockout_blocks_hacking(self):
        """TMP_09 — force_lockout() imposta is_locked_out == True."""
        self.hs.force_lockout()
        self.assertTrue(self.hs.is_locked_out)

    def test_HACK_01_lockout_duration_attribute(self):
        """HACK_01 — LOCKOUT_DURATION è 60 secondi."""
        self.assertEqual(self.hs.LOCKOUT_DURATION, 60.0)

    def test_HACK_03_max_attempts_attribute(self):
        """HACK_03 — MAX_ATTEMPTS è 5."""
        self.assertEqual(self.hs.MAX_ATTEMPTS, 5)

    def test_HACK_01b_can_hack_before_lockout(self):
        """HACK_01b — senza lockout can_hack restituisce True."""
        ok, _ = self.hs.can_hack(TERMINAL)
        self.assertTrue(ok)

    def test_TMP_11_to_dict_returns_dict(self):
        """TMP_11 — to_dict() restituisce un dict."""
        self.assertIsInstance(self.hs.to_dict(), dict)

    def test_TMP_12_restore_from_dict(self):
        """TMP_12 — restore_from_dict() non solleva eccezioni."""
        d = self.hs.to_dict()
        self.hs.restore_from_dict(d)

    def test_TMP_06b_cleanup_no_error(self):
        """TMP_06b — cleanup() non solleva eccezioni."""
        self.hs.cleanup()

    def test_TMP_09b_force_lockout_returns_string(self):
        """TMP_09b — force_lockout() restituisce una stringa."""
        self.assertIsInstance(self.hs.force_lockout(), str)

    def test_HACK_04_failed_attempts_initial_zero(self):
        """HACK_04 — failed_attempts inizialmente 0."""
        self.assertEqual(self.hs.failed_attempts, 0)


if __name__ == "__main__":
    unittest.main()