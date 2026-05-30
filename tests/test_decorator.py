"""test_decorator.py — Pattern Decorator: CharacterDecorator chain (DEC_01 … DEC_12)."""
import unittest
import base_setup  # noqa: F401
from game.model.character_decorator import (
    StatsComponent, CharacterDecorator,
    CorrosioneDecorator, FuocoDecorator, ShockDecorator,
    SoluzionePiranhaDec, MucillagineDecorator,
)


class TestDecorator(unittest.TestCase):

    def setUp(self):
        class _FakeStats:
            hp = 100
            atk = 5
            defense = 10
        self.fake_stats = _FakeStats()
        self.stats_component = StatsComponent(self.fake_stats)

    def test_DEC_01_take_damage_base(self):
        """DEC_01 — take_damage base: danno = raw - difesa, minimo 1."""
        self.fake_stats.hp = 100
        dmg = self.stats_component.take_damage(20)  # 20 - 10 = 10
        self.assertEqual(dmg, 10)
        self.assertEqual(self.fake_stats.hp, 90)

    def test_DEC_02_effective_defense(self):
        """DEC_02 — effective_defense() restituisce il valore base della difesa."""
        self.fake_stats.defense = 15
        self.assertEqual(self.stats_component.effective_defense(), 15)

    def test_DEC_03_corrosione_reduces_defense(self):
        """DEC_03 — CorrosioneDecorator riduce la difesa di 5 punti."""
        self.fake_stats.defense = 20
        dec = CorrosioneDecorator(self.stats_component)
        self.assertEqual(dec.effective_defense(), 15)

    def test_DEC_04_fuoco_amplifies_damage(self):
        """DEC_04 — FuocoDecorator aggiunge 3 al danno grezzo."""
        self.fake_stats.hp = 100
        dec = FuocoDecorator(self.stats_component)
        dmg = dec.take_damage(10)  # (10 + 3) - 10 = 3
        self.assertEqual(dmg, 3)
        self.assertEqual(self.fake_stats.hp, 97)

    def test_DEC_05_shock_sets_defense_to_zero(self):
        """DEC_05 — ShockDecorator azzera la difesa."""
        self.fake_stats.defense = 20
        dec = ShockDecorator(self.stats_component)
        self.assertEqual(dec.effective_defense(), 0)

    def test_DEC_06_piranhas_scales_with_turns(self):
        """DEC_06 — SoluzionePiranhaDec aggiunge turns_active * 10 al danno."""
        self.fake_stats.hp = 200
        self.fake_stats.defense = 0
        dec = SoluzionePiranhaDec(self.stats_component, turns_active=3)
        dmg = dec.take_damage(10)  # 10 + 3*10 = 40
        self.assertEqual(dmg, 40)

    def test_DEC_07_mucillagine_reduces_defense(self):
        """DEC_07 — MucillagineDecorator riduce la difesa di 3 punti."""
        self.fake_stats.defense = 20
        dec = MucillagineDecorator(self.stats_component)
        self.assertEqual(dec.effective_defense(), 17)

    def test_DEC_08_decorator_delegates_effective_defense(self):
        """DEC_08 — Decorator astratto delega effective_defense al wrapped."""
        dec = CorrosioneDecorator(self.stats_component)
        self.assertEqual(dec.effective_defense(), self.fake_stats.defense - 5)

    def test_DEC_09_decorator_delegates_take_damage(self):
        """DEC_09 — MucillagineDecorator (non override take_damage) delega al wrapped."""
        self.fake_stats.hp = 100
        dec = MucillagineDecorator(self.stats_component)
        dmg = dec.take_damage(15)  # 15 - 10 = 5
        self.assertEqual(dmg, 5)

    def test_DEC_10_stacking_corrosione_then_fuoco(self):
        """DEC_10 — Corrosione + Fuoco combinati: difesa ridotta E danno amplificato."""
        self.fake_stats.defense = 20
        self.fake_stats.hp = 100
        chain = FuocoDecorator(CorrosioneDecorator(self.stats_component))
        self.assertEqual(chain.effective_defense(), 15)
        dmg = chain.take_damage(10)
        self.assertGreaterEqual(dmg, 1)

    def test_DEC_11_stacking_fuoco_then_shock(self):
        """DEC_11 — Fuoco + Shock: difesa a 0, danno = raw + amplify (min 1)."""
        self.fake_stats.defense = 15
        self.fake_stats.hp = 100
        chain = FuocoDecorator(ShockDecorator(self.stats_component))
        self.assertEqual(chain.effective_defense(), 0)
        dmg = chain.take_damage(5)
        self.assertGreaterEqual(dmg, 1)

    def test_DEC_12_piranhas_turns_zero_no_extra_damage(self):
        """DEC_12 — SoluzionePiranhaDec con turns_active=0 non aggiunge danno."""
        self.fake_stats.hp = 100
        self.fake_stats.defense = 0
        dec = SoluzionePiranhaDec(self.stats_component, turns_active=0)
        dmg = dec.take_damage(10)  # 10 + 0*10 = 10
        self.assertEqual(dmg, 10)


if __name__ == "__main__":
    unittest.main()