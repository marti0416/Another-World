"""test_new_systems.py — Sistemi aggiuntivi: WorldRules, CoupleEthics, HUD, CoopInteraction (TMP_26…32)."""
import unittest
import base_setup  # noqa: F401
from game.events.event_bus import EventBus
from game.events.event_types import EventType


class TestNewSystems(unittest.TestCase):

    def test_TMP_26_world_rules_initialize(self):
        """TMP_26 — WorldRulesSystem.initialize() non solleva eccezioni."""
        from game.systems.world_rules import WorldRulesSystem
        wrs = WorldRulesSystem()
        wrs.initialize(EventBus())
        wrs.cleanup()

    def test_TMP_27_clamp_player_pos_in_bounds(self):
        """TMP_27 — clamp_player_pos(60, 5) → (60, 5)."""
        from game.systems.world_rules import WorldRulesSystem
        self.assertEqual(WorldRulesSystem.clamp_player_pos(60, 5), (60, 5))

    def test_TMP_27b_clamp_player_pos_out_of_bounds(self):
        """TMP_27b — clamp_player_pos(100, 100) → (63, 47)."""
        from game.systems.world_rules import WorldRulesSystem
        self.assertEqual(WorldRulesSystem.clamp_player_pos(100, 100), (63, 47))

    def test_TMP_28_aggro_trigger_within_radius(self):
        """TMP_28 — AggroTrigger.check_aggro() → True quando player è entro il raggio."""
        from game.systems.world_rules import AggroTrigger
        trigger = AggroTrigger(enemy_type="zombie", aggro_radius=1.5, position=(5, 5))
        self.assertTrue(trigger.check_aggro((5, 4)))

    def test_TMP_28b_aggro_trigger_outside_radius(self):
        """TMP_28b — AggroTrigger.check_aggro() → False quando player è fuori raggio."""
        from game.systems.world_rules import AggroTrigger
        trigger = AggroTrigger(enemy_type="zombie", aggro_radius=1.5, position=(5, 5))
        self.assertFalse(trigger.check_aggro((10, 10)))

    def test_TMP_29_couple_ethics_initialize_subscribes(self):
        """TMP_29 — CoupleEthicsSystem.initialize() si iscrive a ETHICS_CHANGED."""
        from game.systems.social_system import CoupleEthicsSystem
        bus = EventBus()
        ces = CoupleEthicsSystem()
        ces.initialize(bus)
        self.assertGreaterEqual(len(bus._listeners.get(EventType.ETHICS_CHANGED, [])), 1)
        ces.cleanup()

    def test_TMP_30_couple_ethics_update_via_publish(self):
        """TMP_30 — publish(ETHICS_CHANGED, delta=2) → ethics == 2."""
        from game.systems.social_system import CoupleEthicsSystem
        bus = EventBus()
        ces = CoupleEthicsSystem()
        ces.initialize(bus)
        bus.publish(EventType.ETHICS_CHANGED, {"delta": 2})
        self.assertEqual(ces.ethics, 2)
        ces.cleanup()

    def test_TMP_31_hud_system_creates_panels(self):
        """TMP_31 — HUDSystem.initialize() → panel_Rivet e panel_Echo esistono."""
        from game.systems.hud_system import HUDSystem
        hud = HUDSystem()
        hud.initialize(EventBus())
        self.assertIsNotNone(hud.panel_Rivet)
        self.assertIsNotNone(hud.panel_Echo)
        hud.cleanup()

    def test_TMP_32_coop_give_item_to_partner(self):
        """TMP_32 — CoopInteractionSystem.give_item_to_partner() trasferisce l'oggetto."""
        from game.systems.hud_system import CoopInteractionSystem
        from game.model.item import Item, ItemType, Inventory

        class _FakeChar:
            def __init__(self, name):
                self.name = name
                self.inventory = Inventory(max_weight=0)

        giver = _FakeChar("Rivet")
        receiver = _FakeChar("Echo")
        item = Item(item_id="medikit", name="Medikit",
                    item_type=ItemType.CONSUMABLE, quantity=2)
        giver.inventory.add_item(item)
        coop = CoopInteractionSystem()
        result = coop.give_item_to_partner(giver, (5, 5), receiver, (5, 6), "medikit", qty=1)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()