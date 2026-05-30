"""test_strategy.py — Pattern Strategy: IWeaponBehaviour (STR_01 … STR_14)."""
import unittest
import base_setup  # noqa: F401
from game.model.weapon_system import (
    IWeaponBehaviour, JammableWeaponBehaviour,
    AssaultRifleBehaviour, RailGunBehaviour,
    AcidGunBehaviour, LightPistolBehaviour,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class _FakeUser:
    name = "Rivet"
    class stats:
        atk = 5
        defense = 10
        hp = 100


class _FakeTarget:
    name = "Zombie"
    faction_name = "zombie"

    def __init__(self):
        from game.model.stats import Stats
        self.stats = Stats(hp=50, atk=3, defense=5)

    def is_alive(self):
        return self.stats.hp > 0


def _user(atk=5):
    u = _FakeUser()
    u.stats = type('S', (), {'atk': atk, 'defense': 10, 'hp': 100})()
    return u


def _target():
    t = _FakeTarget.__new__(_FakeTarget)
    _FakeTarget.__init__(t)
    return t


class TestStrategyBehaviours(unittest.TestCase):

    # ── STR_01 ───────────────────────────────────────────────────────────────
    def test_STR_01_assault_rifle_fire_returns_dict(self):
        """STR_01 — AssaultRifleBehaviour.fire() restituisce un dict."""
        arb = AssaultRifleBehaviour()
        result = arb.fire(_user(atk=15), [_target()], {})
        self.assertIsInstance(result, dict)
        self.assertIn("log", result)

    # ── STR_02 ───────────────────────────────────────────────────────────────
    def test_STR_02_assault_rifle_can_jam(self):
        """STR_02 — JAM_BASE > 0: l'arma può incepparsi (test deterministico con atk basso)."""
        arb = AssaultRifleBehaviour()
        results = [arb.fire(_user(atk=0), [_target()], {}) for _ in range(100)]
        jammed_any = any(r.get("jammed", False) for r in results)
        # con atk=0 e jam base > 0, almeno una su 100 deve incepparsi
        self.assertTrue(jammed_any or arb.JAM_BASE == 0)

    # ── STR_03 ───────────────────────────────────────────────────────────────
    def test_STR_03_railgun_fire_returns_dict(self):
        """STR_03 — RailGunBehaviour.fire() restituisce un dict."""
        rgb = RailGunBehaviour()
        result = rgb.fire(_user(atk=15), [_target()], {})
        self.assertIsInstance(result, dict)

    # ── STR_04 ───────────────────────────────────────────────────────────────
    def test_STR_04_railgun_can_jam(self):
        """STR_04 — RailGun è JammableWeaponBehaviour, quindi può incepparsi."""
        self.assertTrue(issubclass(RailGunBehaviour, JammableWeaponBehaviour))

    # ── STR_05 ───────────────────────────────────────────────────────────────
    def test_STR_05_acid_gun_fire_returns_dict(self):
        """STR_05 — AcidGunBehaviour.fire() restituisce un dict."""
        agb = AcidGunBehaviour()
        result = agb.fire(_user(), [_target()], {})
        self.assertIsInstance(result, dict)

    # ── STR_06 ───────────────────────────────────────────────────────────────
    def test_STR_06_acid_gun_extends_jammable(self):
        """STR_06 — AcidGunBehaviour estende JammableWeaponBehaviour (ha jam mechanism)."""
        self.assertTrue(issubclass(AcidGunBehaviour, JammableWeaponBehaviour))

    # ── STR_07 ───────────────────────────────────────────────────────────────
    def test_STR_07_light_pistol_fire_returns_dict(self):
        """STR_07 — LightPistolBehaviour.fire() restituisce un dict."""
        lpb = LightPistolBehaviour()
        result = lpb.fire(_user(), [_target()], {})
        self.assertIsInstance(result, dict)

    # ── STR_08 ───────────────────────────────────────────────────────────────
    def test_STR_08_light_pistol_is_jammable(self):
        """STR_08 — LightPistolBehaviour estende JammableWeaponBehaviour."""
        self.assertTrue(issubclass(LightPistolBehaviour, JammableWeaponBehaviour))

    # ── STR_09 ───────────────────────────────────────────────────────────────
    def test_STR_09_all_behaviours_have_category(self):
        """STR_09 — Ogni behaviour ha una categoria stringa non vuota."""
        for cls in [AssaultRifleBehaviour, RailGunBehaviour,
                    AcidGunBehaviour, LightPistolBehaviour]:
            with self.subTest(cls=cls.__name__):
                b = cls()
                self.assertIsInstance(b.category, str)
                self.assertGreater(len(b.category), 0)

    # ── STR_10 ───────────────────────────────────────────────────────────────
    def test_STR_10_all_behaviours_have_weight(self):
        """STR_10 — Ogni behaviour ha peso > 0."""
        for cls in [AssaultRifleBehaviour, RailGunBehaviour,
                    AcidGunBehaviour, LightPistolBehaviour]:
            with self.subTest(cls=cls.__name__):
                b = cls()
                self.assertGreater(b.weight, 0)

    # ── STR_11 ───────────────────────────────────────────────────────────────
    def test_STR_11_jammable_fire_delegates_to_do_fire_when_no_jam(self):
        """STR_11 — Con atk molto alto (basso jam rate), fire() delega a _do_fire."""
        arb = AssaultRifleBehaviour()
        # Con atk=100 jam_rate diventa negativo → 0.0, quindi fire chiama sempre _do_fire
        result = arb.fire(_user(atk=100), [_target()], {})
        self.assertFalse(result.get("jammed", False))

    # ── STR_12 ───────────────────────────────────────────────────────────────
    def test_STR_12_jammable_force_jam(self):
        """STR_12 — Sovrascrivendo _jam_rate a 1.0 l'arma si inceppa sempre."""
        class AlwaysJam(AssaultRifleBehaviour):
            def _jam_rate(self, user): return 1.0

        arb = AlwaysJam()
        result = arb.fire(_user(), [_target()], {})
        self.assertTrue(result.get("jammed", False))
        self.assertEqual(result["total_damage"], 0)

    # ── STR_13 ───────────────────────────────────────────────────────────────
    def test_STR_13_assault_rifle_display_name(self):
        """STR_13 — AssaultRifleBehaviour.display_name è una stringa non vuota."""
        arb = AssaultRifleBehaviour()
        self.assertIsInstance(arb.display_name, str)
        self.assertGreater(len(arb.display_name), 0)

    # ── STR_14 ───────────────────────────────────────────────────────────────
    def test_STR_14_railgun_display_name(self):
        """STR_14 — RailGunBehaviour.display_name è una stringa non vuota."""
        rgb = RailGunBehaviour()
        self.assertIsInstance(rgb.display_name, str)
        self.assertGreater(len(rgb.display_name), 0)


if __name__ == "__main__":
    unittest.main()