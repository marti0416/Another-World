"""test_supplemental.py — Test supplementari per completare la copertura a 240.

Copre gli ID mancanti nelle aree:
  OBS_13
  TMP_06 / TMP_08 / TMP_10 / TMP_20…21 / TMP_26…35
  BLD_06 / BLD_07 / BLD_10
  COR_01 / COR_03…07
"""
import unittest
import base_setup  # noqa: F401
import pygame
from game.events.event_bus import EventBus
from game.events.event_types import EventType


# ══ OBS_13 ══════════════════════════════════════════════════════════════════

class TestObserver(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()

    def test_OBS_13_unsubscribe_then_publish_not_called(self):
        """OBS_13 — dopo unsubscribe, la callback non riceve più eventi."""
        results = []
        cb = lambda d: results.append(d)
        self.bus.subscribe(EventType.ITEM_PICKUP, cb)
        self.bus.unsubscribe(EventType.ITEM_PICKUP, cb)
        self.bus.publish(EventType.ITEM_PICKUP, {"item": "key"})
        self.assertEqual(results, [])


# ══ TMP_06 / TMP_08 / TMP_10 — HackingSystem ════════════════════════════════

class TestHackingSystem(unittest.TestCase):

    def setUp(self):
        from game.systems.hacking_system import HackingSystem
        self.hs = HackingSystem()
        self.hs.initialize(EventBus())

    def tearDown(self):
        self.hs.cleanup()

    def test_TMP_06_hacking_initialize_no_error(self):
        """TMP_06 — HackingSystem.initialize() non solleva eccezioni."""
        from game.systems.hacking_system import HackingSystem
        h = HackingSystem()
        h.initialize(EventBus())
        h.cleanup()

    def test_TMP_08_can_hack_returns_tuple(self):
        """TMP_08 — can_hack() restituisce una tupla (bool, str)."""
        result = self.hs.can_hack("terminal_01")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], str)

    def test_TMP_10_failed_attempts_tracking(self):
        """TMP_10 — failed_attempts è un intero accessibile e parte da 0."""
        self.assertIsInstance(self.hs.failed_attempts, int)
        self.assertEqual(self.hs.failed_attempts, 0)


# ══ TMP_20 / TMP_21 — MovementSystem ════════════════════════════════════════

class TestMovementSystem(unittest.TestCase):

    def test_TMP_20_movement_system_initialize(self):
        """TMP_20 — MovementSystem.initialize() non solleva eccezioni."""
        from game.systems.movement_system import MovementSystem
        ms = MovementSystem()
        ms.initialize(EventBus())
        ms.cleanup()

    def test_TMP_21_movement_system_register_player(self):
        """TMP_21 — register_player() aggiunge il giocatore al sistema."""
        from game.systems.movement_system import MovementSystem

        class _FakeChar:
            pass

        ms = MovementSystem()
        ms.initialize(EventBus())
        ms.register_player("Rivet", _FakeChar(), start_col=5, start_row=7)
        self.assertIn("Rivet", ms._players)
        ms.cleanup()


# ══ TMP_26 … TMP_35 — ISystem template (altri sistemi) ══════════════════════

class TestISystems(unittest.TestCase):

    def test_TMP_26_isystem_is_abstract(self):
        """TMP_26 — ISystem è astratta: non può essere istanziata direttamente."""
        from game.events.isystem import ISystem
        with self.assertRaises(TypeError):
            ISystem()

    def test_TMP_27_battle_system_is_isystem(self):
        """TMP_27 — BattleSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.battle_system import BattleSystem
        self.assertTrue(issubclass(BattleSystem, ISystem))

    def test_TMP_28_hacking_system_is_isystem(self):
        """TMP_28 — HackingSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.hacking_system import HackingSystem
        self.assertTrue(issubclass(HackingSystem, ISystem))

    def test_TMP_29_quest_system_is_isystem(self):
        """TMP_29 — QuestSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.quest_system import QuestSystem
        self.assertTrue(issubclass(QuestSystem, ISystem))

    def test_TMP_30_party_system_is_isystem(self):
        """TMP_30 — PartySystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.party_system import PartySystem
        self.assertTrue(issubclass(PartySystem, ISystem))

    def test_TMP_31_movement_system_is_isystem(self):
        """TMP_31 — MovementSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.movement_system import MovementSystem
        self.assertTrue(issubclass(MovementSystem, ISystem))

    def test_TMP_32_crafting_system_initialize(self):
        """TMP_32 — CraftingSystem.initialize() non solleva eccezioni."""
        from game.systems.crafting_system import CraftingSystem
        cs = CraftingSystem()
        cs.initialize(EventBus())
        cs.cleanup()

    def test_TMP_33_crafting_system_is_isystem(self):
        """TMP_33 — CraftingSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.crafting_system import CraftingSystem
        self.assertTrue(issubclass(CraftingSystem, ISystem))

    def test_TMP_34_loot_system_initialize(self):
        """TMP_34 — LootSystem.initialize() non solleva eccezioni."""
        from game.systems.loot_system import LootSystem
        ls = LootSystem()
        ls.initialize(EventBus())
        ls.cleanup()

    def test_TMP_35_loot_system_is_isystem(self):
        """TMP_35 — LootSystem implementa ISystem."""
        from game.events.isystem import ISystem
        from game.systems.loot_system import LootSystem
        self.assertTrue(issubclass(LootSystem, ISystem))


# ══ BLD_06 / BLD_07 / BLD_10 — EchoBuilder passi individuali ════════════════

class TestEchoBuilder(unittest.TestCase):

    def test_BLD_06_echo_builder_set_stats(self):
        """BLD_06 — EchoBuilder.set_stats() non solleva eccezioni."""
        from game.model.character_builder import EchoBuilder
        eb = EchoBuilder()
        eb.reset()
        eb.set_stats()

    def test_BLD_07_echo_builder_set_skills(self):
        """BLD_07 — EchoBuilder.set_skills() non solleva eccezioni."""
        from game.model.character_builder import EchoBuilder
        eb = EchoBuilder()
        eb.reset()
        eb.set_stats()
        eb.set_skills()

    def test_BLD_10_echo_builder_set_inventory(self):
        """BLD_10 — EchoBuilder.set_inventory() non solleva eccezioni."""
        from game.model.character_builder import EchoBuilder
        eb = EchoBuilder()
        eb.reset()
        eb.set_stats()
        eb.set_inventory()
        char = eb.get_result()
        self.assertIsNotNone(char.inventory)


# ══ COR_01 / COR_03 … COR_07 — handler concreti ═════════════════════════════

class TestEventChainHandlers(unittest.TestCase):

    def test_COR_01_quit_handler_is_event_handler(self):
        """COR_01 — QuitHandler è sottoclasse di EventHandler."""
        from game.controller.event_chain import QuitHandler, EventHandler
        self.assertTrue(issubclass(QuitHandler, EventHandler))

    def test_COR_03_video_resize_handler_is_event_handler(self):
        """COR_03 — VideoResizeHandler è sottoclasse di EventHandler."""
        from game.controller.event_chain import VideoResizeHandler, EventHandler
        self.assertTrue(issubclass(VideoResizeHandler, EventHandler))

    def test_COR_04_save_menu_handler_is_event_handler(self):
        """COR_04 — SaveMenuHandler è sottoclasse di EventHandler."""
        from game.controller.event_chain import SaveMenuHandler, EventHandler
        self.assertTrue(issubclass(SaveMenuHandler, EventHandler))

    def test_COR_05_screen_handler_is_event_handler(self):
        """COR_05 — ScreenHandler è sottoclasse di EventHandler."""
        from game.controller.event_chain import ScreenHandler, EventHandler
        self.assertTrue(issubclass(ScreenHandler, EventHandler))

    def test_COR_06_video_resize_handler_passes_non_resize(self):
        """COR_06 — VideoResizeHandler propaga l'evento se non è VIDEORESIZE."""
        from game.controller.event_chain import VideoResizeHandler
        called = []

        class _Next:
            def handle(self, e):
                called.append(e.type)
                return True

        state_ref = {"surf": None, "scale_x": 1.0, "scale_y": 1.0, "W": 640, "H": 480}
        h = VideoResizeHandler(state_ref)
        nxt = _Next()
        h.set_next(nxt)

        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0,
                                unicode='a', scancode=0)
        h.handle(ev)
        self.assertIn(pygame.KEYDOWN, called)

    def test_COR_07_build_event_chain_returns_event_handler(self):
        """COR_07 — build_event_chain() restituisce un EventHandler."""
        from game.controller.event_chain import build_event_chain, EventHandler
        from game.controller.game_manager import GameManager

        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()

        state_ref = {"surf": pygame.display.get_surface(),
                     "scale_x": 1.0, "scale_y": 1.0, "W": 640, "H": 480}
        screens_ref = {}
        chain = build_event_chain(gm, state_ref, screens_ref)
        self.assertIsInstance(chain, EventHandler)

        GameManager.reset()


if __name__ == "__main__":
    unittest.main()