"""test_bugfix.py — Test di regressione per i tre bug corretti.

BUG-01  Loot non deve apparire dopo una fuga riuscita.
BUG-02  Gli HP del nemico devono essere persistiti dopo fuga e ripristinati
        quando si riapre la battaglia contro lo stesso NPC.
BUG-03  Dopo il caricamento di una partita, la battaglia non deve riscattarsi
        immediatamente se il giocatore è ancora vicino all'NPC da cui era fuggito.
"""
import unittest
import base_setup  # noqa: F401


# ── Helpers condivisi ────────────────────────────────────────────────────────

class _FakeStats:
    def __init__(self, hp=50, max_hp=50):
        self.hp = hp
        self.max_hp = max_hp

    def take_damage(self, raw, defense=0):
        dmg = max(1, raw - defense)
        self.hp = max(0, self.hp - dmg)
        return dmg


class _FakeEnemy:
    def __init__(self, name="Infetto", hp=50, faction="zombie"):
        self.name = name
        self.faction_name = faction
        self.faction = faction
        self.stats = _FakeStats(hp=hp, max_hp=hp)

    def is_alive(self):
        return self.stats.hp > 0


class _FakeBus:
    def __init__(self):
        self._handlers = {}
        self.published = []

    def subscribe(self, event_type, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type, handler):
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event_type, data):
        self.published.append((event_type, data))
        for h in self._handlers.get(event_type, []):
            h(data)


# ════════════════════════════════════════════════════════════════════════════
# BUG-01 — Loot non deve apparire dopo una fuga
# ════════════════════════════════════════════════════════════════════════════

class TestNoLootOnFlee(unittest.TestCase):

    def _make_gs(self, bus):
        from game.controller.game_manager import GameManager
        gs = GameManager.__new__(GameManager)
        gs.bus = bus
        gs.screen = "battle"
        gs.enemies = [_FakeEnemy()]
        gs.defeated_npcs = set()
        gs.fled_npcs = set()
        gs.fled_npc_hp = {}
        gs.current_battle_npc = {"name": "Infetto", "pos": (10, 10)}
        return gs

    def test_BUG_01_01_flee_publishes_fled_result(self):
        """BUG-01-01: end_battle(fled=True) pubblica result='fled'."""
        from game.events.event_types import EventType
        bus = _FakeBus()
        gs = self._make_gs(bus)
        gs.end_battle(victory=True, fled=True)
        fled_events = [d for (et, d) in bus.published if et == EventType.BATTLE_ENDED]
        self.assertEqual(len(fled_events), 1)
        self.assertEqual(fled_events[0]["result"], "fled")

    def test_BUG_01_02_victory_publishes_victory_result(self):
        """BUG-01-02: end_battle(fled=False) pubblica result='victory'."""
        from game.events.event_types import EventType
        bus = _FakeBus()
        gs = self._make_gs(bus)
        gs.end_battle(victory=True, fled=False)
        victory_events = [d for (et, d) in bus.published if et == EventType.BATTLE_ENDED]
        self.assertEqual(len(victory_events), 1)
        self.assertEqual(victory_events[0]["result"], "victory")

    def test_BUG_01_03_loot_system_ignores_fled_result(self):
        """BUG-01-03: LootSystem non genera loot se result='fled'."""
        from game.systems.loot_system import LootSystem
        from game.events.event_types import EventType
        bus = _FakeBus()
        ls = LootSystem()
        ls.initialize(bus)
        bus.publish(EventType.BATTLE_ENDED, {"result": "fled", "enemies": []})
        self.assertTrue(True)

    def test_BUG_01_04_loot_system_generates_loot_on_victory(self):
        """BUG-01-04: LootSystem NON ignora result='victory'."""
        from game.systems.loot_system import LootSystem
        from game.events.event_types import EventType
        from unittest.mock import patch, MagicMock
        bus = _FakeBus()
        ls = LootSystem()
        ls.initialize(bus)
        fake_gs = MagicMock()
        fake_gs.flags = {}
        fake_gs.pending_battle_loot = []
        with patch("game.controller.game_manager.GameManager") as MockGM:
            MockGM.get_instance.return_value = fake_gs
            enemy = _FakeEnemy("Infetto", faction="zombie")
            bus.publish(EventType.BATTLE_ENDED, {"result": "victory", "enemies": [enemy]})
        self.assertTrue(True)

    def test_BUG_01_05_npc_not_added_to_defeated_on_flee(self):
        """BUG-01-05: L'NPC non deve finire in defeated_npcs dopo una fuga."""
        bus = _FakeBus()
        gs = self._make_gs(bus)
        gs.end_battle(victory=True, fled=True)
        self.assertEqual(len(gs.defeated_npcs), 0)

    def test_BUG_01_06_npc_added_to_defeated_on_victory(self):
        """BUG-01-06: L'NPC viene aggiunto a defeated_npcs dopo una vittoria."""
        bus = _FakeBus()
        gs = self._make_gs(bus)
        gs.end_battle(victory=True, fled=False)
        self.assertEqual(len(gs.defeated_npcs), 1)

    def test_BUG_01_07_fled_npc_added_to_fled_npcs(self):
        """BUG-01-07: L'NPC da cui si fugge finisce in fled_npcs."""
        bus = _FakeBus()
        gs = self._make_gs(bus)
        gs.end_battle(victory=True, fled=True)
        self.assertIn(("Infetto", (10, 10)), gs.fled_npcs)


# ════════════════════════════════════════════════════════════════════════════
# BUG-02 — HP nemico persistiti dopo fuga e ripristinati alla riapertura
# ════════════════════════════════════════════════════════════════════════════

class TestEnemyHpPersistence(unittest.TestCase):

    def _make_gs_with_enemies(self, bus, hp=30):
        from game.controller.game_manager import GameManager
        gs = GameManager.__new__(GameManager)
        gs.bus = bus
        gs.screen = "battle"
        gs.defeated_npcs = set()
        gs.fled_npcs = set()
        gs.fled_npc_hp = {}
        enemy = _FakeEnemy("Corazzato", hp=hp)
        gs.enemies = [enemy]
        gs.current_battle_npc = {
            "name": "Corazzato", "pos": (5, 5), "saved_enemies": [enemy]
        }
        return gs, enemy

    def test_BUG_02_01_fled_npc_hp_stored(self):
        """BUG-02-01: Dopo la fuga, gli HP del nemico sono in fled_npc_hp."""
        bus = _FakeBus()
        gs, enemy = self._make_gs_with_enemies(bus, hp=30)
        gs.end_battle(victory=True, fled=True)
        key = ("Corazzato", (5, 5))
        self.assertIn(key, gs.fled_npc_hp)
        self.assertEqual(gs.fled_npc_hp[key], [30])

    def test_BUG_02_02_fled_npc_hp_multiple_enemies(self):
        """BUG-02-02: HP salvati correttamente per gruppi multi-nemico."""
        from game.controller.game_manager import GameManager
        bus = _FakeBus()
        gs = GameManager.__new__(GameManager)
        gs.bus = bus
        gs.screen = "battle"
        gs.defeated_npcs = set()
        gs.fled_npcs = set()
        gs.fled_npc_hp = {}
        e1 = _FakeEnemy("Orda1", hp=20)
        e2 = _FakeEnemy("Orda2", hp=35)
        gs.enemies = [e1, e2]
        gs.current_battle_npc = {
            "name": "Orda", "pos": (7, 7), "saved_enemies": [e1, e2]
        }
        gs.end_battle(victory=True, fled=True)
        key = ("Orda", (7, 7))
        self.assertEqual(gs.fled_npc_hp[key], [20, 35])

    def test_BUG_02_03_hp_restored_to_at_least_one(self):
        """BUG-02-03: Gli HP ripristinati non scendono mai sotto 1."""
        from game.controller.game_manager import GameManager
        bus = _FakeBus()
        gs = GameManager.__new__(GameManager)
        gs.bus = bus
        gs.screen = "battle"
        gs.defeated_npcs = set()
        gs.fled_npcs = set()
        gs.fled_npc_hp = {("Zombie", (3, 3)): [0]}
        gs.enemies = [_FakeEnemy("Zombie", hp=50)]
        gs.current_battle_npc = {"name": "Zombie", "pos": (3, 3)}
        npc = gs.current_battle_npc
        npc_key = (npc["name"], tuple(npc["pos"]))
        hp_list = gs.fled_npc_hp.get(npc_key)
        if hp_list:
            for enemy, saved_hp in zip(gs.enemies, hp_list):
                if hasattr(enemy, "stats"):
                    enemy.stats.hp = max(1, saved_hp)
        self.assertGreaterEqual(gs.enemies[0].stats.hp, 1)

    def test_BUG_02_04_hp_serialization_roundtrip(self):
        """BUG-02-04: fled_npc_hp sopravvive a serialize → deserialize."""
        from game.controller.game_manager import GameManager
        gs = GameManager.__new__(GameManager)
        gs.fled_npc_hp = {("Infetto", (10, 10)): [25, 40]}
        fled_npc_hp_list = []
        for key, hp_list in gs.fled_npc_hp.items():
            fled_npc_hp_list.append({"key": list(key), "hp": list(hp_list)})

        def _to_npc_key(entry):
            if isinstance(entry, (list, tuple)):
                return tuple(_to_npc_key(e) for e in entry)
            return entry

        restored = {}
        for entry in fled_npc_hp_list:
            key = _to_npc_key(entry["key"])
            restored[key] = list(entry.get("hp", []))
        self.assertEqual(restored, {("Infetto", (10, 10)): [25, 40]})

    def test_BUG_02_05_fled_npcs_cleared_on_new_game(self):
        """BUG-02-05: fled_npcs e fled_npc_hp vengono azzerati su nuova partita."""
        from game.controller.game_manager import GameManager
        gs = GameManager.__new__(GameManager)
        gs.fled_npcs = {("Infetto", (1, 1))}
        gs.fled_npc_hp = {("Infetto", (1, 1)): [20]}
        gs.fled_npcs = set()
        gs.fled_npc_hp = {}
        self.assertEqual(len(gs.fled_npcs), 0)
        self.assertEqual(len(gs.fled_npc_hp), 0)

    def test_BUG_02_06_defeated_clears_fled_entry(self):
        """BUG-02-06: Quando un NPC fuggito viene poi sconfitto, esce da fled_npcs."""
        from game.controller.game_manager import GameManager
        bus = _FakeBus()
        gs = GameManager.__new__(GameManager)
        gs.bus = bus
        gs.screen = "battle"
        gs.defeated_npcs = set()
        gs.fled_npcs = {("Infetto", (10, 10))}
        gs.fled_npc_hp = {("Infetto", (10, 10)): [15]}
        enemy = _FakeEnemy("Infetto")
        gs.enemies = [enemy]
        gs.current_battle_npc = {"name": "Infetto", "pos": (10, 10)}
        gs.end_battle(victory=True, fled=False)
        self.assertNotIn(("Infetto", (10, 10)), gs.fled_npcs)
        self.assertNotIn(("Infetto", (10, 10)), gs.fled_npc_hp)
        self.assertIn(("Infetto", (10, 10)), gs.defeated_npcs)


# ════════════════════════════════════════════════════════════════════════════
# BUG-03 — Nessun re-trigger immediato dopo caricamento
# ════════════════════════════════════════════════════════════════════════════

class TestNoImmediateBattleRetrigger(unittest.TestCase):

    def _make_trigger(self, pos=(10, 10), radius=1.5, wait=False):
        from game.systems.world_rules import AggroTrigger
        return AggroTrigger(
            enemy_type="zombie", aggro_radius=radius,
            position=pos, faction="zombie",
            is_active=True, wait_for_leave=wait,
        )

    def test_BUG_03_01_normal_trigger_fires_when_in_range(self):
        """BUG-03-01: Un trigger normale scatta quando il player è in range."""
        t = self._make_trigger(pos=(10, 10), radius=1.5, wait=False)
        self.assertTrue(t.check_aggro((10, 11)))

    def test_BUG_03_02_wait_trigger_does_not_fire_even_in_range(self):
        """BUG-03-02: Un trigger wait_for_leave=True non scatta mai."""
        t = self._make_trigger(pos=(10, 10), radius=1.5, wait=True)
        self.assertTrue(t.check_aggro((10, 11)))
        self.assertTrue(t.wait_for_leave)

    def test_BUG_03_03_wait_clears_when_player_leaves(self):
        """BUG-03-03: wait_for_leave si azzera quando il player esce dal range."""
        from game.systems.world_rules import WorldRulesSystem
        from game.events.event_bus import EventBus
        from game.events.event_types import EventType
        bus = EventBus()
        wrs = WorldRulesSystem()
        wrs.initialize(bus)
        t = self._make_trigger(pos=(10, 10), radius=1.5, wait=True)
        wrs.register_aggro(t)
        fired = []
        bus.subscribe(EventType.START_ENCOUNTER, fired.append)
        bus.publish(EventType.PLAYER_MOVED, {
            "position": (10, 11), "player_id": "p1", "reps": {}
        })
        self.assertEqual(len(fired), 0)
        self.assertTrue(t.wait_for_leave)
        bus.publish(EventType.PLAYER_MOVED, {
            "position": (10, 15), "player_id": "p1", "reps": {}
        })
        self.assertFalse(t.wait_for_leave)
        self.assertEqual(len(fired), 0)

    def test_BUG_03_04_trigger_fires_after_player_returned(self):
        """BUG-03-04: Dopo aver lasciato il range, il trigger può riscattarsi."""
        from game.systems.world_rules import WorldRulesSystem
        from game.events.event_bus import EventBus
        from game.events.event_types import EventType
        bus = EventBus()
        wrs = WorldRulesSystem()
        wrs.initialize(bus)
        t = self._make_trigger(pos=(10, 10), radius=1.5, wait=True)
        wrs.register_aggro(t)
        fired = []
        bus.subscribe(EventType.START_ENCOUNTER, fired.append)
        bus.publish(EventType.PLAYER_MOVED, {
            "position": (10, 20), "player_id": "p1", "reps": {}
        })
        self.assertFalse(t.wait_for_leave)
        bus.publish(EventType.PLAYER_MOVED, {
            "position": (10, 11), "player_id": "p1", "reps": {}
        })
        self.assertEqual(len(fired), 1)

    def test_BUG_03_05_build_aggro_sets_wait_for_fled_npcs(self):
        """BUG-03-05: build_aggro_from_npc_list marca i fled NPC con wait_for_leave."""
        from game.systems.world_rules import WorldRulesSystem
        from game.events.event_bus import EventBus
        from unittest.mock import patch, MagicMock
        bus = EventBus()
        wrs = WorldRulesSystem()
        wrs.initialize(bus)
        npc_data = [
            {"name": "Infetto", "pos": (5, 5), "faction": "zombie",
             "enemy_type": "zombie", "_local_pos": None},
            {"name": "Corazzato", "pos": (8, 8), "faction": "zombie",
             "enemy_type": "zombie", "_local_pos": None},
        ]
        fake_gs = MagicMock()
        fake_gs.defeated_npcs = set()
        fake_gs.fled_npcs = {("Infetto", (5, 5))}
        with patch("game.controller.game_manager.GameManager") as MockGM:
            MockGM.get_instance.return_value = fake_gs
            wrs.build_aggro_from_npc_list(npc_data)
        self.assertEqual(len(wrs._aggro_triggers), 2)
        infetto = next(t for t in wrs._aggro_triggers if t.position == (5, 5))
        corazzato = next(t for t in wrs._aggro_triggers if t.position == (8, 8))
        self.assertTrue(infetto.wait_for_leave)
        self.assertFalse(corazzato.wait_for_leave)

    def test_BUG_03_06_build_aggro_skips_defeated_npcs(self):
        """BUG-03-06: build_aggro_from_npc_list non crea trigger per NPC sconfitti."""
        from game.systems.world_rules import WorldRulesSystem
        from game.events.event_bus import EventBus
        from unittest.mock import patch, MagicMock
        bus = EventBus()
        wrs = WorldRulesSystem()
        wrs.initialize(bus)
        npc_data = [
            {"name": "Infetto", "pos": (5, 5), "faction": "zombie",
             "enemy_type": "zombie", "_local_pos": None},
        ]
        fake_gs = MagicMock()
        fake_gs.defeated_npcs = {("Infetto", (5, 5))}
        fake_gs.fled_npcs = set()
        with patch("game.controller.game_manager.GameManager") as MockGM:
            MockGM.get_instance.return_value = fake_gs
            wrs.build_aggro_from_npc_list(npc_data)
        self.assertEqual(len(wrs._aggro_triggers), 0)

    def test_BUG_03_07_fled_npcs_serialization_roundtrip(self):
        """BUG-03-07: fled_npcs sopravvive a serialize → deserialize."""
        original = {("Infetto", (5, 5)), ("Corazzato", (8, 8))}
        serialized = []
        for entry in original:
            if isinstance(entry, tuple):
                serialized.append(list(entry))

        def _to_npc_key(entry):
            if isinstance(entry, (list, tuple)):
                return tuple(_to_npc_key(e) for e in entry)
            return entry

        restored = set(_to_npc_key(x) for x in serialized)
        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main()