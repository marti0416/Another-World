"""test_quest_system.py — QuestSystem (QST_01…07, TMP_13…19)."""
import unittest
import base_setup  # noqa: F401
from game.systems.quest_system import (
    QuestSystem, QuestDef, QuestTrigger, QuestTriggerType,
    Objective, ObjectiveType, QuestStatus, QuestState,
)
from game.events.event_bus import EventBus
from game.events.event_types import EventType


def _make_quest(qid, trigger_type=QuestTriggerType.MANUAL):
    return QuestDef(
        quest_id=qid,
        title=f"Test Quest {qid}",
        description="Una quest di test.",
        trigger=QuestTrigger(trigger_type=trigger_type),
        objectives=[
            Objective(obj_id="obj1", description="Uccidi 1 nemico",
                      obj_type=ObjectiveType.KILL_ENEMIES, required=1)
        ],
    )


class TestQuestSystem(unittest.TestCase):

    def setUp(self):
        self.qs = QuestSystem()
        self.qs.initialize(EventBus())

    def tearDown(self):
        self.qs.cleanup()

    def test_TMP_13_initialize_creates_system(self):
        """TMP_13 — initialize() non solleva eccezioni."""
        self.assertIsNotNone(self.qs)

    def test_TMP_14_register_quest(self):
        """TMP_14 — register_quest() registra la quest nel sistema."""
        self.qs.register_quest(_make_quest("Q01"))
        self.assertIn("Q01", self.qs._defs)

    def test_TMP_15_activate_and_accept_quest(self):
        """TMP_15 + QST_01+02 — activate → accept rende la quest ACTIVE."""
        self.qs.register_quest(_make_quest("Q01"))
        self.qs.activate_quest("Q01")
        result = self.qs.accept_quest("Q01")
        self.assertTrue(result)
        self.assertEqual(self.qs._states["Q01"].status, QuestStatus.ACTIVE)

    def test_TMP_16_get_active_quests(self):
        """TMP_16 — get_active_quests() include la quest accettata."""
        self.qs.register_quest(_make_quest("Q01"))
        self.qs.activate_quest("Q01")
        self.qs.accept_quest("Q01")
        ids = [s.quest_id for s in self.qs.get_active_quests()]
        self.assertIn("Q01", ids)

    def test_TMP_17_advance_objective(self):
        """TMP_17 + QST_03 — advance_objective() incrementa il contatore."""
        self.qs.register_quest(_make_quest("Q01"))
        self.qs.activate_quest("Q01")
        self.qs.accept_quest("Q01")
        self.qs.advance_objective("Q01", "obj1", 1)
        obj = self.qs._states["Q01"].get_objective("obj1")
        self.assertGreaterEqual(obj.progress, 1)

    def test_TMP_18_is_completed_after_objective_met(self):
        """TMP_18 + QST_04 — is_completed() True dopo aver soddisfatto l'obiettivo."""
        self.qs.register_quest(_make_quest("Q01"))
        self.qs.activate_quest("Q01")
        self.qs.accept_quest("Q01")
        self.qs.advance_objective("Q01", "obj1", 1)
        self.assertTrue(self.qs.is_completed("Q01"))

    def test_TMP_19_to_dict_serializable(self):
        """TMP_19 — to_dict() restituisce un dict."""
        self.qs.register_quest(_make_quest("Q01"))
        self.assertIsInstance(self.qs.to_dict(), dict)

    def test_QST_05_accept_craft_explosive(self):
        """QST_05 — Q05_craft_explosive: accept restituisce True."""
        quest = QuestDef(
            quest_id="Q05_craft_explosive",
            title="Artigiano del Caos",
            description="Costruisci una molotov.",
            trigger=QuestTrigger(trigger_type=QuestTriggerType.MANUAL),
            objectives=[
                Objective(obj_id="craft_molotov", description="Crafta 1 molotov",
                          obj_type=ObjectiveType.CRAFT_ITEM, required=1)
            ],
        )
        self.qs.register_quest(quest)
        self.qs.activate_quest("Q05_craft_explosive")
        self.assertTrue(self.qs.accept_quest("Q05_craft_explosive"))

    def test_QST_06_get_available_quests(self):
        """QST_06 — get_available_quests() include quest in stato AVAILABLE."""
        self.qs.register_quest(_make_quest("Q02"))
        self.qs.activate_quest("Q02")
        ids = [s.quest_id for s in self.qs.get_available_quests()]
        self.assertIn("Q02", ids)

    def test_QST_07_item_crafted_event_advances_craft_objective(self):
        """QST_07 — evento ITEM_CRAFTED avanza l'obiettivo di tipo CRAFT_ITEM."""
        bus = EventBus()
        qs2 = QuestSystem()
        qs2.initialize(bus)
        quest = QuestDef(
            quest_id="Q05_craft_explosive",
            title="Artigiano del Caos",
            description="Costruisci una molotov.",
            trigger=QuestTrigger(trigger_type=QuestTriggerType.MANUAL),
            objectives=[
                Objective(obj_id="craft_molotov", description="Crafta 1 molotov",
                          obj_type=ObjectiveType.CRAFT_ITEM, required=1,
                          item_id="molotov")
            ],
        )
        qs2.register_quest(quest)
        qs2.activate_quest("Q05_craft_explosive")
        qs2.accept_quest("Q05_craft_explosive")

        class _FakeItem:
            item_id = "molotov"

        bus.publish(EventType.ITEM_CRAFTED, {"item": _FakeItem()})
        self.assertTrue(qs2.is_completed("Q05_craft_explosive"))
        qs2.cleanup()

    def test_cleanup_no_error(self):
        """cleanup() non solleva eccezioni."""
        self.qs.cleanup()


if __name__ == "__main__":
    unittest.main()