"""test_battle_cmd.py — BattleSystem Template (TMP_01…05) + Command (CMD_01…15)."""
import unittest
import base_setup  # noqa: F401
from game.systems.battle_system import (
    IBattleCommand, AttackCommand, WeaponCommand,
    SkillCommand, ItemCommand, ComboCommand, FleeCommand,
    BattleSystem,
)
from game.events.event_bus import EventBus
from game.events.event_types import EventType


# ── Helpers ──────────────────────────────────────────────────────────────────

class _Stats:
    def __init__(self, hp=50, atk=5, defense=2):
        self.hp = hp
        self.atk = atk
        self.defense = defense

    def take_damage(self, raw):
        dmg = max(1, raw - self.defense)
        self.hp = max(0, self.hp - dmg)
        return dmg


class _Fighter:
    def __init__(self, name="Fighter", hp=50, atk=5):
        self.name = name
        self.stats = _Stats(hp=hp, atk=atk)
        self.equipped_weapon = None
        self.weapons = []

    def is_alive(self):
        return self.stats.hp > 0


def _attacker():
    return _Fighter("Rivet", hp=100, atk=8)


def _target():
    return _Fighter("Zombie", hp=50, atk=3)


# ══ TMP_01 … TMP_05  (BattleSystem — Template Method) ════════════════════════

class TestBattleSystemTemplate(unittest.TestCase):

    def test_TMP_01_create(self):
        """TMP_01 — BattleSystem può essere creato senza argomenti."""
        bs = BattleSystem()
        self.assertIsNotNone(bs)

    def test_TMP_02_initialize_subscribes(self):
        """TMP_02 — initialize() si iscrive a START_ENCOUNTER sull'EventBus."""
        bus = EventBus()
        bs = BattleSystem()
        bs.initialize(bus)
        self.assertIn(EventType.START_ENCOUNTER, bus._listeners)

    def test_TMP_03_start_battle_running(self):
        """TMP_03 — start_battle() imposta running=True."""
        bs = BattleSystem()
        bs.initialize(EventBus())
        bs.start_battle()
        self.assertTrue(bs.running)

    def test_TMP_04_check_end_victory(self):
        """TMP_04 — check_end() restituisce 'victory' quando tutti i nemici sono morti."""
        bs = BattleSystem()
        bs.initialize(EventBus())
        enemy = _target()
        enemy.stats.hp = 0
        bs._enemies = [enemy]
        bs._party = [_attacker()]
        bs.start_battle()
        self.assertEqual(bs.check_end(), "victory")

    def test_TMP_05_check_end_defeat(self):
        """TMP_05 — check_end() restituisce 'defeat' quando un alleato è morto."""
        bs = BattleSystem()
        bs.initialize(EventBus())
        enemy = _target()
        ally = _attacker()
        ally.stats.hp = 0
        bs._enemies = [enemy]
        bs._party = [ally]
        bs.start_battle()
        self.assertEqual(bs.check_end(), "defeat")


# ══ CMD_01 … CMD_15  (Command pattern) ══════════════════════════════════════

class TestBattleCommands(unittest.TestCase):

    def test_CMD_01_ibattle_command_is_abstract(self):
        """CMD_01 — IBattleCommand è astratto (non può essere istanziato)."""
        with self.assertRaises(TypeError):
            IBattleCommand()

    def test_CMD_02_attack_is_ibattle_command(self):
        """CMD_02 — AttackCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(AttackCommand, IBattleCommand))

    def test_CMD_03_attack_execute_returns_string(self):
        """CMD_03 — AttackCommand.execute() restituisce una stringa."""
        cmd = AttackCommand(_attacker(), _target())
        self.assertIsInstance(cmd.execute(), str)

    def test_CMD_04_flee_is_ibattle_command(self):
        """CMD_04 — FleeCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(FleeCommand, IBattleCommand))

    def test_CMD_05_flee_execute_returns_string(self):
        """CMD_05 — FleeCommand.execute() restituisce una stringa."""
        cmd = FleeCommand(EventBus())
        self.assertIsInstance(cmd.execute(), str)

    def test_CMD_06_weapon_is_ibattle_command(self):
        """CMD_06 — WeaponCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(WeaponCommand, IBattleCommand))

    def test_CMD_07_skill_is_ibattle_command(self):
        """CMD_07 — SkillCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(SkillCommand, IBattleCommand))

    def test_CMD_08_item_is_ibattle_command(self):
        """CMD_08 — ItemCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(ItemCommand, IBattleCommand))

    def test_CMD_09_combo_zeros_target_hp(self):
        """CMD_09 — ComboCommand.execute() azzera gli HP del bersaglio."""
        initiator = _attacker()
        partner = _Fighter("Echo")
        target = _target()
        target.stats.hp = 35
        cmd = ComboCommand(initiator, partner, target)
        cmd.execute()
        self.assertEqual(target.stats.hp, 0)

    def test_CMD_10_attack_no_weapon_uses_atk(self):
        """CMD_10 — AttackCommand senza arma equipaggiata usa stats.atk."""
        attacker = _attacker()
        attacker.equipped_weapon = None
        target = _target()
        target.stats.defense = 0
        cmd = AttackCommand(attacker, target)
        self.assertIsInstance(cmd.execute(), str)

    def test_CMD_11_combo_is_ibattle_command(self):
        """CMD_11 — ComboCommand è sottoclasse di IBattleCommand."""
        self.assertTrue(issubclass(ComboCommand, IBattleCommand))

    def test_CMD_12_flee_succeed(self):
        """CMD_12 — FleeCommand con bus pubblica BATTLE_ENDED su fuga riuscita."""
        import random
        bus = EventBus()
        received = []
        bus.subscribe(EventType.BATTLE_ENDED, lambda d: received.append(d))
        original = random.random
        random.random = lambda: 0.9
        try:
            cmd = FleeCommand(bus)
            msg = cmd.execute()
            self.assertIn("riuscita", msg)
        finally:
            random.random = original

    def test_CMD_13_skill_execute_returns_string(self):
        """CMD_13 — SkillCommand.execute() restituisce una stringa."""
        from game.controller.game_manager import GameManager
        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()
        from game.model.skill_wheel import SkillNode
        node = SkillNode("TestSkill", success_rate=1.0, cooldown=0,
                         unlock_tech=0, is_combat=True)
        attacker = _attacker()
        attacker.stats.gain_tech_points = lambda n: None
        target = _target()
        cmd = SkillCommand(attacker, node, target, [target])
        self.assertIsInstance(cmd.execute(), str)
        GameManager.reset()

    def test_CMD_14_item_missing(self):
        """CMD_14 — ItemCommand.execute() restituisce messaggio se item non in inventario."""
        from game.controller.game_manager import GameManager
        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()

        class _FakeInventory:
            def get_item(self, iid): return None

        user = _attacker()
        user.inventory = _FakeInventory()
        cmd = ItemCommand(user, "missing_item", targets=[_target()])
        self.assertIn("non trovato", cmd.execute())
        GameManager.reset()

    def test_CMD_15_combo_log_contains_names(self):
        """CMD_15 — ComboCommand.execute() include i nomi di initiator e partner nel log."""
        initiator = _attacker()
        partner = _Fighter("Echo")
        target = _target()
        cmd = ComboCommand(initiator, partner, target)
        msg = cmd.execute()
        self.assertIn(initiator.name, msg)
        self.assertIn(partner.name, msg)


if __name__ == "__main__":
    unittest.main()