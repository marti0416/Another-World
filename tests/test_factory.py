"""test_factory.py — Abstract Factory + Factory Method (FAC_01 … FAC_15)."""
import unittest
import base_setup  # noqa: F401
from game.model.faction_factory import (
    DannatiFactory, RazziatoriFactory, ErrantiFactory, ZombieFactory,
)
from game.model.enemy import Enemy, EnemyFactory
from game.model.faction_system import Faction
from game.model.loot_protocols import ILootStrategy


class TestFactory(unittest.TestCase):

    def test_FAC_01_dannati_create_enemy(self):
        """FAC_01 — DannatiFactory.create_enemy() restituisce un Enemy."""
        self.assertIsInstance(DannatiFactory().create_enemy("Brutale"), Enemy)

    def test_FAC_02_dannati_create_faction(self):
        """FAC_02 — DannatiFactory.create_faction() restituisce una Faction."""
        self.assertIsInstance(DannatiFactory().create_faction(), Faction)

    def test_FAC_03_dannati_faction_id(self):
        """FAC_03 — DannatiFactory.faction_id() restituisce un id stringa."""
        fid = DannatiFactory().faction_id()
        self.assertIsInstance(fid, str)
        self.assertGreater(len(fid), 0)

    def test_FAC_04_razziatori_create_enemy(self):
        """FAC_04 — RazziatoriFactory.create_enemy() restituisce un Enemy."""
        self.assertIsInstance(RazziatoriFactory().create_enemy("Raider"), Enemy)

    def test_FAC_05_razziatori_create_faction(self):
        """FAC_05 — RazziatoriFactory.create_faction() restituisce una Faction."""
        self.assertIsInstance(RazziatoriFactory().create_faction(), Faction)

    def test_FAC_06_erranti_create_enemy(self):
        """FAC_06 — ErrantiFactory.create_enemy() restituisce un Enemy."""
        self.assertIsInstance(ErrantiFactory().create_enemy("Wanderer"), Enemy)

    def test_FAC_07_erranti_create_faction(self):
        """FAC_07 — ErrantiFactory.create_faction() restituisce una Faction."""
        self.assertIsInstance(ErrantiFactory().create_faction(), Faction)

    def test_FAC_08_zombie_create_enemy(self):
        """FAC_08 — ZombieFactory.create_enemy() restituisce un Enemy."""
        self.assertIsInstance(ZombieFactory().create_enemy("Infetto"), Enemy)

    def test_FAC_09_zombie_create_faction(self):
        """FAC_09 — ZombieFactory.create_faction() restituisce una Faction."""
        self.assertIsInstance(ZombieFactory().create_faction(), Faction)

    def test_FAC_10_all_factories_have_loot_strategy(self):
        """FAC_10 — Ogni factory concreta ha una strategia loot."""
        for factory_cls in [DannatiFactory, RazziatoriFactory, ErrantiFactory, ZombieFactory]:
            strat = factory_cls().create_loot_strategy()
            self.assertIsInstance(strat, ILootStrategy)

    def test_FAC_11_enemy_factory_create_infetto(self):
        """FAC_11 — EnemyFactory.create_infetto() restituisce un Enemy."""
        self.assertIsInstance(EnemyFactory.create_infetto(), Enemy)

    def test_FAC_12_enemy_factory_create_corazzato(self):
        """FAC_12 — EnemyFactory.create_corazzato() restituisce Enemy con difesa elevata."""
        e = EnemyFactory.create_corazzato()
        self.assertIsInstance(e, Enemy)
        self.assertGreaterEqual(e.stats.defense, 5)

    def test_FAC_13_enemy_factory_create_orda(self):
        """FAC_13 — EnemyFactory.create_orda() restituisce un Enemy."""
        self.assertIsInstance(EnemyFactory.create_orda(None), Enemy)

    def test_FAC_14_enemy_factory_create_meat_giant(self):
        """FAC_14 — EnemyFactory.create_meat_giant() restituisce Enemy con HP elevati."""
        e = EnemyFactory.create_meat_giant()
        self.assertIsInstance(e, Enemy)
        self.assertGreaterEqual(e.stats.hp, 100)

    def test_FAC_15_enemy_factory_create_npc_fazione(self):
        """FAC_15 — EnemyFactory.create_npc_fazione() crea NPC con faction_name corretto."""
        e = EnemyFactory.create_npc_fazione("Scout", "Dannati")
        self.assertIsInstance(e, Enemy)
        self.assertEqual(e.faction_name, "Dannati")


if __name__ == "__main__":
    unittest.main()