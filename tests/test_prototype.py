"""test_prototype.py — Pattern Prototype: Item + Inventory (PRO_01 … PRO_12)."""
import unittest
import base_setup  # noqa: F401
from game.model.item import Item, Inventory, ItemType


class TestPrototype(unittest.TestCase):

    def setUp(self):
        self.simple_item = Item(item_id="medikit", name="Medikit",
                                item_type=ItemType.CONSUMABLE, quantity=3)
        self.empty_inventory = Inventory(max_weight=0)
        self.bounded_inventory = Inventory(max_weight=5)

    def test_PRO_01_clone_is_independent_copy(self):
        """PRO_01 — clone() produce una copia indipendente."""
        clone = self.simple_item.clone()
        self.assertIsNot(clone, self.simple_item)
        self.assertEqual(clone.item_id, self.simple_item.item_id)
        self.assertEqual(clone.name, self.simple_item.name)

    def test_PRO_02_clone_modification_doesnt_affect_original(self):
        """PRO_02 — modificare il clone non altera l'originale."""
        clone = self.simple_item.clone()
        clone.quantity = 99
        self.assertEqual(self.simple_item.quantity, 3)

    def test_PRO_03_clone_copies_item_type(self):
        """PRO_03 — item_type viene copiato correttamente."""
        item = Item("rifle", "Fucile", ItemType.WEAPON, quantity=1)
        clone = item.clone()
        self.assertEqual(clone.item_type, ItemType.WEAPON)

    def test_PRO_04_inventory_add_item(self):
        """PRO_04 — add_item() aggiunge l'oggetto e lo rende accessibile."""
        self.empty_inventory.add_item(self.simple_item)
        self.assertIsNotNone(self.empty_inventory.get_item("medikit"))

    def test_PRO_05_inventory_get_item_returns_correct(self):
        """PRO_05 — get_item() restituisce l'Item corretto."""
        self.empty_inventory.add_item(self.simple_item)
        result = self.empty_inventory.get_item("medikit")
        self.assertEqual(result.name, "Medikit")

    def test_PRO_06_inventory_remove_item_reduces_quantity(self):
        """PRO_06 — remove_item() riduce la quantità correttamente."""
        self.empty_inventory.add_item(self.simple_item)
        result = self.empty_inventory.remove_item("medikit", 2)
        self.assertTrue(result)
        self.assertEqual(self.empty_inventory.get_item("medikit").quantity, 1)

    def test_PRO_07_inventory_remove_item_insufficient_quantity(self):
        """PRO_07 — quantità insufficiente restituisce False."""
        item = Item("med", "Med", ItemType.CONSUMABLE, quantity=1)
        self.empty_inventory.add_item(item)
        self.assertFalse(self.empty_inventory.remove_item("med", 5))

    def test_PRO_08_inventory_can_add_within_limit(self):
        """PRO_08 — can_add() True se sotto il limite di peso."""
        self.assertTrue(self.bounded_inventory.can_add(1))

    def test_PRO_09_inventory_get_by_type(self):
        """PRO_09 — get_by_type() filtra per ItemType."""
        self.empty_inventory.add_item(Item("w1", "Pistola", ItemType.WEAPON))
        self.empty_inventory.add_item(Item("c1", "Kit",     ItemType.CONSUMABLE))
        weapons = self.empty_inventory.get_by_type(ItemType.WEAPON)
        self.assertEqual(len(weapons), 1)
        self.assertEqual(weapons[0].item_id, "w1")

    def test_PRO_10_inventory_to_dict(self):
        """PRO_10 — to_dict() serializza correttamente."""
        self.empty_inventory.add_item(self.simple_item)
        d = self.empty_inventory.to_dict()
        self.assertIn("items", d)
        self.assertTrue(any(i["item_id"] == "medikit" for i in d["items"]))

    def test_PRO_11_inventory_all_items(self):
        """PRO_11 — all_items() restituisce tutti gli item presenti."""
        self.empty_inventory.add_item(Item("x", "X", ItemType.MATERIAL))
        self.empty_inventory.add_item(Item("y", "Y", ItemType.KEY_ITEM))
        self.assertEqual(len(self.empty_inventory.all_items()), 2)

    def test_PRO_12_inventory_add_stacks_same_item(self):
        """PRO_12 — aggiungere lo stesso item_id incrementa quantity invece di duplicare."""
        item1 = Item("bolt", "Bullone", ItemType.MATERIAL, quantity=2)
        item2 = Item("bolt", "Bullone", ItemType.MATERIAL, quantity=3)
        self.empty_inventory.add_item(item1)
        self.empty_inventory.add_item(item2)
        self.assertEqual(self.empty_inventory.get_item("bolt").quantity, 5)


if __name__ == "__main__":
    unittest.main()