"""test_iterator.py — Pattern Iterator: SkillNode + SkillWheel (ITR_01 … ITR_19)."""
import unittest
import base_setup  # noqa: F401
from game.model.skill_wheel import SkillNode, SkillWheel, SkillWheelIterator


def make_node(name="Test", success_rate=0.9, cooldown=0, unlock_tech=0, is_combat=True):
    return SkillNode(name, success_rate=success_rate, cooldown=cooldown,
                     unlock_tech=unlock_tech, is_combat=is_combat)


def _make_skill_wheel():
    sw = SkillWheel()
    sw.add_skill(SkillNode("Hacking",       success_rate=0.9, cooldown=2, unlock_tech=3, is_combat=False))
    sw.add_skill(SkillNode("Colpo Critico", success_rate=0.7, cooldown=1, unlock_tech=0, is_combat=True))
    sw.add_skill(SkillNode("Raffica",       success_rate=0.8, cooldown=3, unlock_tech=5, is_combat=True))
    return sw


class TestIterator(unittest.TestCase):

    def setUp(self):
        self.skill_wheel = _make_skill_wheel()

    def test_ITR_01_is_available_enough_tp(self):
        """ITR_01 — is_available() True con tech_points sufficienti."""
        node = make_node(unlock_tech=5)
        self.assertTrue(node.is_available(5))

    def test_ITR_02_not_available_insufficient_tp(self):
        """ITR_02 — is_available() False con tech_points insufficienti."""
        node = make_node(unlock_tech=10)
        self.assertFalse(node.is_available(5))

    def test_ITR_03_is_unlocked(self):
        """ITR_03 — is_unlocked() True con punti sufficienti."""
        node = make_node(unlock_tech=3)
        self.assertTrue(node.is_unlocked(3))

    def test_ITR_04_attempt_use_success_rate_one(self):
        """ITR_04 — attempt_use() True con success_rate=1.0."""
        self.assertTrue(make_node(success_rate=1.0).attempt_use())

    def test_ITR_05_attempt_use_success_rate_zero(self):
        """ITR_05 — attempt_use() False con success_rate=0.0."""
        self.assertFalse(make_node(success_rate=0.0).attempt_use())

    def test_ITR_06_add_skill(self):
        """ITR_06 — add_skill() aggiunge il nodo alla ruota."""
        self.assertEqual(len(self.skill_wheel._skills), 3)

    def test_ITR_07_get_skill_by_name(self):
        """ITR_07 — get_skill() trova il nodo per nome."""
        node = self.skill_wheel.get_skill("Hacking")
        self.assertIsNotNone(node)
        self.assertEqual(node.name, "Hacking")

    def test_ITR_08_get_skill_nonexistent_returns_none(self):
        """ITR_08 — get_skill() restituisce None per nomi inesistenti."""
        self.assertIsNone(self.skill_wheel.get_skill("Invisibile"))

    def test_ITR_09_iter_all_skills(self):
        """ITR_09 — iterare la ruota restituisce tutti e 3 i nodi."""
        self.assertEqual(len(list(self.skill_wheel)), 3)

    def test_ITR_10_iter_available_filters(self):
        """ITR_10 — iter_available() filtra skill con unlock_tech troppo alto."""
        available = list(self.skill_wheel.iter_available(tech_points=3))
        names = [n.name for n in available]
        self.assertIn("Hacking", names)
        self.assertIn("Colpo Critico", names)
        self.assertNotIn("Raffica", names)

    def test_ITR_11_iter_combat_filters(self):
        """ITR_11 — iter_combat() include solo nodi is_combat=True."""
        combat = list(self.skill_wheel.iter_combat(tech_points=10))
        self.assertTrue(all(n.is_combat for n in combat))
        self.assertNotIn("Hacking", [n.name for n in combat])

    def test_ITR_12_tick_decrements_cooldown(self):
        """ITR_12 — tick() decrementa il cooldown corrente di ogni nodo."""
        sw = SkillWheel()
        node = make_node(cooldown=2)
        node.current_cooldown = 2
        sw.add_skill(node)
        sw.tick()
        self.assertEqual(node.current_cooldown, 1)

    def test_ITR_13_get_available_skills(self):
        """ITR_13 — get_available_skills() restituisce lista."""
        avail = self.skill_wheel.get_available_skills(tech_points=10)
        self.assertIsInstance(avail, list)
        self.assertGreaterEqual(len(avail), 1)

    def test_ITR_14_to_dict(self):
        """ITR_14 — to_dict() restituisce una lista."""
        d = self.skill_wheel.to_dict()
        self.assertIsInstance(d, list)
        self.assertEqual(len(d), 3)

    def test_ITR_15_restore_from_dict(self):
        """ITR_15 — restore_from_dict() aggiorna il cooldown dei nodi esistenti."""
        self.skill_wheel.get_skill("Colpo Critico").current_cooldown = 2
        d = self.skill_wheel.to_dict()
        sw2 = SkillWheel()
        sw2.add_skill(SkillNode("Hacking",       success_rate=0.9, cooldown=2, unlock_tech=3, is_combat=False))
        sw2.add_skill(SkillNode("Colpo Critico", success_rate=0.7, cooldown=1, unlock_tech=0, is_combat=True))
        sw2.add_skill(SkillNode("Raffica",       success_rate=0.8, cooldown=3, unlock_tech=5, is_combat=True))
        sw2.restore_from_dict(d)
        self.assertEqual(sw2.get_skill("Colpo Critico").current_cooldown, 2)

    def test_ITR_16_iterator_next_returns_first_node(self):
        """ITR_16 — __next__ restituisce il primo nodo."""
        it = iter(self.skill_wheel)
        self.assertIsInstance(next(it), SkillNode)

    def test_ITR_17_iterator_stop_iteration(self):
        """ITR_17 — StopIteration alla fine della ruota."""
        it = iter(self.skill_wheel)
        with self.assertRaises(StopIteration):
            for _ in range(100):
                next(it)

    def test_ITR_18_iterator_len(self):
        """ITR_18 — __len__ dell'iterator corrisponde al numero di nodi."""
        it = iter(self.skill_wheel)
        self.assertEqual(len(it), 3)

    def test_ITR_19_iterator_to_list(self):
        """ITR_19 — to_list() converte l'iterator in lista di SkillNode."""
        it = iter(self.skill_wheel)
        lst = it.to_list()
        self.assertIsInstance(lst, list)
        self.assertEqual(len(lst), 3)
        self.assertTrue(all(isinstance(n, SkillNode) for n in lst))


if __name__ == "__main__":
    unittest.main()