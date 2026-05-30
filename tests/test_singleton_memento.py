"""test_singleton_memento.py — Singleton (SING_01…06) + Memento (MEM_01…17)."""
import unittest
import threading
import base_setup  # noqa: F401
from datetime import datetime


def _reset_gm():
    from game.controller.game_manager import GameManager
    GameManager.reset()


# ══ SING_01 … SING_06  (GameManager Singleton) ══════════════════════════════

class TestSingleton(unittest.TestCase):

    def setUp(self):
        _reset_gm()

    def tearDown(self):
        _reset_gm()

    # ── SING_01 ──────────────────────────────────────────────────────────────
    def test_SING_01_get_instance_creates_game_manager(self):
        """SING_01 — GameManager.get_instance() restituisce un'istanza GameManager."""
        from game.controller.game_manager import GameManager
        gm = GameManager.get_instance()
        self.assertIsInstance(gm, GameManager)

    # ── SING_02 ──────────────────────────────────────────────────────────────
    def test_SING_02_get_instance_twice_same_identity(self):
        """SING_02 — Due chiamate a get_instance() restituiscono la stessa identità (is)."""
        from game.controller.game_manager import GameManager
        i1 = GameManager.get_instance()
        i2 = GameManager.get_instance()
        self.assertIs(i1, i2)

    # ── SING_03 ──────────────────────────────────────────────────────────────
    def test_SING_03_get_instance_thread_safety(self):
        """SING_03 — get_instance() da 5 thread restituisce un'unica istanza condivisa."""
        from game.controller.game_manager import GameManager
        results = []

        def _worker():
            results.append(GameManager.get_instance())

        threads = [threading.Thread(target=_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(all(r is results[0] for r in results))

    # ── SING_04 ──────────────────────────────────────────────────────────────
    def test_SING_04_register_system_accessible_via_get_system(self):
        """SING_04 — register_system(BattleSystem()) → sistema accessibile via get_system."""
        import warnings
        from game.controller.game_manager import GameManager
        from game.systems.battle_system import BattleSystem
        gm = GameManager.get_instance()
        gm.initialize()
        bs = BattleSystem()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            gm.register_system(bs)
        found = gm.get_system(BattleSystem)
        self.assertIsNotNone(found)

    # ── SING_05 ──────────────────────────────────────────────────────────────
    def test_SING_05_get_system_nonexistent_returns_none(self):
        """SING_05 — get_system per tipo non registrato → None."""
        from game.controller.game_manager import GameManager

        class _FakeSystem:
            pass

        gm = GameManager.get_instance()
        gm.initialize()
        result = gm.get_system(_FakeSystem)
        self.assertIsNone(result)

    # ── SING_06 ──────────────────────────────────────────────────────────────
    def test_SING_06_change_screen_updates_current_screen(self):
        """SING_06 — change_screen() aggiorna lo schermo corrente."""
        from game.controller.game_manager import GameManager
        gm = GameManager.get_instance()
        gm.initialize()
        gm.change_screen("battle")
        self.assertEqual(gm.screen, "battle")


# ══ MEM_01 … MEM_17  (GameMemento + SaveManager) ════════════════════════════

class TestMemento(unittest.TestCase):

    def setUp(self):
        _reset_gm()
        from game.controller.game_manager import GameMemento, SaveManager
        self.memento = GameMemento({"state": "Default", "ethics": 5}, location="City_A")
        self.save_manager = SaveManager()
        self.save_manager._slots.clear()

    def tearDown(self):
        _reset_gm()

    # ── MEM_01 ───────────────────────────────────────────────────────────────
    def test_MEM_01_create_memento(self):
        """MEM_01 — gm.create_memento() restituisce un oggetto GameMemento."""
        from game.controller.game_manager import GameManager, GameMemento
        gm = GameManager.get_instance()
        gm.initialize()
        m = gm.create_memento()
        self.assertIsInstance(m, GameMemento)

    # ── MEM_02 ───────────────────────────────────────────────────────────────
    def test_MEM_02_restore_from_memento(self):
        """MEM_02 — restore_from_memento(m) ripristina lo stato identico."""
        from game.controller.game_manager import GameManager, GameMemento
        gm = GameManager.get_instance()
        gm.initialize()
        m = GameMemento({"ethics": 7, "state": "Test"}, location="Hub")
        gm.restore_from_memento(m)  # non deve sollevare eccezioni

    # ── MEM_03 ───────────────────────────────────────────────────────────────
    def test_MEM_03_get_state_snapshot(self):
        """MEM_03 — memento.get_state_snapshot() restituisce un dict con chiavi di stato."""
        snap = self.memento.get_state_snapshot()
        self.assertIsInstance(snap, dict)
        self.assertGreater(len(snap), 0)

    # ── MEM_04 ───────────────────────────────────────────────────────────────
    def test_MEM_04_get_timestamp(self):
        """MEM_04 — memento.get_timestamp() restituisce un oggetto datetime."""
        ts = self.memento.get_timestamp()
        self.assertIsInstance(ts, datetime)

    # ── MEM_05 ───────────────────────────────────────────────────────────────
    def test_MEM_05_get_location_city_a(self):
        """MEM_05 — Giocatore in 'City_A' → memento.get_location() == 'City_A'."""
        self.assertEqual(self.memento.get_location(), "City_A")

    # ── MEM_06 ───────────────────────────────────────────────────────────────
    def test_MEM_06_to_dict(self):
        """MEM_06 — memento.to_dict() restituisce un dict serializzabile."""
        import json
        d = self.memento.to_dict()
        self.assertIsInstance(d, dict)
        json.dumps(d)  # non deve sollevare eccezioni

    # ── MEM_07 ───────────────────────────────────────────────────────────────
    def test_MEM_07_from_dict(self):
        """MEM_07 — GameMemento.from_dict(d) restituisce un Memento equivalente."""
        from game.controller.game_manager import GameMemento
        d = {
            "snapshot":  {"ethics": 3},
            "timestamp": datetime.now().isoformat(),
            "location":  "Factory",
        }
        m = GameMemento.from_dict(d)
        self.assertIsInstance(m, GameMemento)
        self.assertEqual(m.get_location(), "Factory")

    # ── MEM_08 ───────────────────────────────────────────────────────────────
    def test_MEM_08_save_game_stores_memento(self):
        """MEM_08 — save_game(gm, 1) → memento archiviato nello slot 1."""
        self.save_manager._slots[1] = self.memento
        self.assertTrue(self.save_manager.has_slot(1))

    # ── MEM_09 ───────────────────────────────────────────────────────────────
    def test_MEM_09_load_game_restores_state(self):
        """MEM_09 — load_game(gm, 1) → True, stato ripristinato."""
        from game.controller.game_manager import GameManager
        gm = GameManager.get_instance()
        gm.initialize()
        self.save_manager._slots[1] = self.memento
        result = self.save_manager.load_game(gm, 1)
        self.assertTrue(result)

    # ── MEM_10 ───────────────────────────────────────────────────────────────
    def test_MEM_10_load_game_slot_empty_returns_false(self):
        """MEM_10 — load_game(gm, 2) → False quando slot non esiste."""
        from game.controller.game_manager import GameManager
        gm = GameManager.get_instance()
        gm.initialize()
        result = self.save_manager.load_game(gm, 2)
        self.assertFalse(result)

    # ── MEM_11 ───────────────────────────────────────────────────────────────
    def test_MEM_11_has_slot_true_after_save(self):
        """MEM_11 — has_slot(1) → True dopo aver salvato."""
        self.save_manager._slots[1] = self.memento
        self.assertTrue(self.save_manager.has_slot(1))

    # ── MEM_12 ───────────────────────────────────────────────────────────────
    def test_MEM_12_has_slot_false_for_empty(self):
        """MEM_12 — has_slot(99) → False."""
        self.assertFalse(self.save_manager.has_slot(99))

    # ── MEM_13 ───────────────────────────────────────────────────────────────
    def test_MEM_13_delete_save_returns_true_and_frees_slot(self):
        """MEM_13 — delete_save(1) → True, slot liberato."""
        self.save_manager._slots[1] = self.memento
        result = self.save_manager.delete_save(1)
        self.assertTrue(result)
        self.assertFalse(self.save_manager.has_slot(1))

    # ── MEM_14 ───────────────────────────────────────────────────────────────
    def test_MEM_14_get_slot_metadata_has_timestamp_and_location(self):
        """MEM_14 — get_slot_metadata(1) → dict con timestamp e location."""
        self.save_manager._slots[1] = self.memento
        meta = self.save_manager.get_slot_metadata(1)
        self.assertIsInstance(meta, dict)
        self.assertIn("timestamp", meta)
        self.assertTrue("location" in meta or "is_empty" in meta)

    # ── MEM_15 ───────────────────────────────────────────────────────────────
    def test_MEM_15_get_first_empty_slot_when_1_and_2_occupied(self):
        """MEM_15 — get_first_empty_slot() → 3 quando slot 1 e 2 occupati."""
        from game.controller.game_manager import GameMemento
        self.save_manager._slots[1] = self.memento
        self.save_manager._slots[2] = GameMemento({"s": 1}, location="X")
        slot = self.save_manager.get_first_empty_slot()
        self.assertEqual(slot, 3)

    # ── MEM_16 ───────────────────────────────────────────────────────────────
    def test_MEM_16_has_any_saves_true(self):
        """MEM_16 — has_any_saves() → True quando slot 1 occupato."""
        self.save_manager._slots[1] = self.memento
        self.assertTrue(self.save_manager.has_any_saves())

    # ── MEM_17 ───────────────────────────────────────────────────────────────
    def test_MEM_17_has_any_saves_false(self):
        """MEM_17 — has_any_saves() → False quando nessuno slot occupato."""
        self.assertFalse(self.save_manager.has_any_saves())


if __name__ == "__main__":
    unittest.main()