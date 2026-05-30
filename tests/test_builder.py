"""test_builder.py — Pattern Builder: GameSystemBuilder, CharacterBuilder, FactionAssembler (BLD_01…16)."""
import unittest
import base_setup  # noqa: F401
from game.events.event_bus import EventBus


class TestGameSystemBuilder(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()

    def test_BLD_11_add_returns_self(self):
        """BLD_11 — add() supporta chaining (restituisce self)."""
        from game.controller.game_manager import GameSystemBuilder
        from game.systems.battle_system import BattleSystem
        gsb = GameSystemBuilder(self.bus)
        self.assertIs(gsb.add(BattleSystem()), gsb)

    def test_BLD_12_build_returns_list(self):
        """BLD_12 — build() restituisce la lista dei sistemi aggiunti."""
        from game.controller.game_manager import GameSystemBuilder
        from game.systems.battle_system import BattleSystem
        from game.systems.quest_system import QuestSystem
        gsb = GameSystemBuilder(self.bus)
        gsb.add(BattleSystem()).add(QuestSystem())
        systems, _refs = gsb.build()
        self.assertEqual(len(systems), 2)

    def test_BLD_13_build_empty(self):
        """BLD_13 — build() con nessun sistema restituisce lista vuota."""
        from game.controller.game_manager import GameSystemBuilder
        gsb = GameSystemBuilder(self.bus)
        systems, _refs = gsb.build()
        self.assertEqual(systems, [])


class TestRivetBuilder(unittest.TestCase):

    def test_BLD_05_get_result(self):
        """BLD_05 — RivetBuilder.get_result() restituisce un Character valido."""
        from game.model.character_builder import RivetBuilder, CharacterDirector, Character
        char = CharacterDirector(RivetBuilder()).construct()
        self.assertIsInstance(char, Character)
        self.assertEqual(char.name, "Rivet")

    def test_BLD_01_reset(self):
        """BLD_01 — reset() non solleva eccezioni."""
        from game.model.character_builder import RivetBuilder
        rb = RivetBuilder()
        rb.set_stats()
        rb.reset()

    def test_BLD_02_03_04_full_sequence(self):
        """BLD_02+03+04 — set_stats → set_skills → set_inventory eseguiti in sequenza."""
        from game.model.character_builder import RivetBuilder
        rb = RivetBuilder()
        rb.reset()
        rb.set_stats()
        rb.set_skills()
        rb.set_inventory()
        char = rb.get_result()
        self.assertIsNotNone(char)
        self.assertIsNotNone(char.stats)
        self.assertIsNotNone(char.skill_wheel)
        self.assertIsNotNone(char.inventory)


class TestEchoBuilder(unittest.TestCase):

    def test_BLD_08_get_result(self):
        """BLD_08 — EchoBuilder.get_result() restituisce un Character 'Echo'."""
        from game.model.character_builder import EchoBuilder, CharacterDirector, Character
        char = CharacterDirector(EchoBuilder()).construct()
        self.assertIsInstance(char, Character)
        self.assertEqual(char.name, "Echo")

    def test_BLD_08b_rivet_echo_different_names(self):
        """BLD_08b — Rivet e Echo hanno nomi diversi."""
        from game.model.character_builder import RivetBuilder, EchoBuilder, CharacterDirector
        rivet = CharacterDirector(RivetBuilder()).construct()
        echo = CharacterDirector(EchoBuilder()).construct()
        self.assertNotEqual(rivet.name, echo.name)


class TestCharacterDirector(unittest.TestCase):

    def test_BLD_09_construct(self):
        """BLD_09 — CharacterDirector.construct() produce personaggio completo."""
        from game.model.character_builder import RivetBuilder, CharacterDirector
        char = CharacterDirector(RivetBuilder()).construct()
        self.assertIsNotNone(char.stats)
        self.assertIsNotNone(char.inventory)
        self.assertIsNotNone(char.skill_wheel)


class TestFactionAssembler(unittest.TestCase):

    def test_BLD_14_build(self):
        """BLD_14 — FactionAssembler.build() restituisce un oggetto non None."""
        from game.model.faction_factory import FactionAssembler
        result = FactionAssembler.build("Dannati", "Scout")
        self.assertIsNotNone(result)

    def test_BLD_15_build_enemy(self):
        """BLD_15 — FactionAssembler.build_enemy() restituisce un Enemy."""
        from game.model.faction_factory import FactionAssembler
        from game.model.enemy import Enemy
        enemy = FactionAssembler.build_enemy("Razziatori", "Raider")
        self.assertIsInstance(enemy, Enemy)

    def test_BLD_16_build_zombie_group(self):
        """BLD_16 — FactionAssembler.build_zombie_group() restituisce un oggetto."""
        from game.model.faction_factory import FactionAssembler
        result = FactionAssembler.build_zombie_group("Horde")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()