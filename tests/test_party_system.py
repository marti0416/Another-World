"""test_party_system.py — PartySystem (TMP_22…25)."""
import unittest
import base_setup  # noqa: F401
from game.systems.party_system import PartySystem
from game.events.event_bus import EventBus


class _FakeChar:
    def __init__(self, alive=True):
        class _S:
            hp = 100 if alive else 0
        self.stats = _S()

    def is_alive(self):
        return self.stats.hp > 0


class TestPartySystem(unittest.TestCase):

    def setUp(self):
        self.ps = PartySystem()
        self.ps.initialize(EventBus())

    def test_TMP_22_add_member(self):
        """TMP_22 — add_member aggiunge il personaggio."""
        c = _FakeChar()
        self.ps.add_member(c)
        self.assertIn(c, self.ps._members)

    def test_TMP_23_all_alive_true(self):
        """TMP_23 — all_alive() True quando tutti sono vivi."""
        self.ps.add_member(_FakeChar(alive=True))
        self.ps.add_member(_FakeChar(alive=True))
        self.assertTrue(self.ps.all_alive())

    def test_TMP_23b_all_alive_false(self):
        """TMP_23b — all_alive() False se almeno uno è morto."""
        self.ps.add_member(_FakeChar(alive=True))
        self.ps.add_member(_FakeChar(alive=False))
        self.assertFalse(self.ps.all_alive())

    def test_TMP_24_any_alive_false(self):
        """TMP_24 — any_alive() False quando tutti sono morti."""
        self.ps.add_member(_FakeChar(alive=False))
        self.assertFalse(self.ps.any_alive())

    def test_TMP_24b_any_alive_true(self):
        """TMP_24b — any_alive() True se almeno uno è vivo."""
        self.ps.add_member(_FakeChar(alive=False))
        self.ps.add_member(_FakeChar(alive=True))
        self.assertTrue(self.ps.any_alive())

    def test_TMP_25_update_ethics_positive(self):
        """TMP_25 — update_ethics(+2) incrementa couple_ethics."""
        self.ps.couple_ethics = 0
        self.ps.update_ethics(2)
        self.assertEqual(self.ps.couple_ethics, 2)

    def test_TMP_25b_update_ethics_clamped_max(self):
        """TMP_25b — update_ethics non supera +10."""
        self.ps.couple_ethics = 9
        self.ps.update_ethics(5)
        self.assertEqual(self.ps.couple_ethics, 10)

    def test_TMP_25c_update_ethics_clamped_min(self):
        """TMP_25c — update_ethics non scende sotto -10."""
        self.ps.couple_ethics = -9
        self.ps.update_ethics(-5)
        self.assertEqual(self.ps.couple_ethics, -10)

    def test_TMP_25d_couple_ethics_default(self):
        """TMP_25d — couple_ethics inizialmente 0."""
        self.assertEqual(self.ps.couple_ethics, 0)


if __name__ == "__main__":
    unittest.main()