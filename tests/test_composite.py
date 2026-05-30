"""test_composite.py — Pattern Composite: UIComponent / WidgetGroup (CMP_01...15)."""
import unittest
import base_setup  # noqa: F401
import pygame
from game.view.ui_widgets import UIComponent, Button, HealthBar, Panel, WidgetGroup


class TestComposite(unittest.TestCase):

    def setUp(self):
        pygame.font.init()
        self.surf = pygame.display.get_surface()
        self.font = pygame.font.Font(None, 24)
        self.btn = Button((0, 0, 80, 30), "OK", (0, 200, 0), self.font)
        self.wg = WidgetGroup()

    def test_CMP_01_add_button(self):
        """CMP_01 — wg.add(button) → button in children()."""
        self.wg.add(self.btn)
        self.assertIn(self.btn, self.wg.children())

    def test_CMP_02_remove_button(self):
        """CMP_02 — wg.remove(button) → button non in children()."""
        self.wg.add(self.btn)
        self.wg.remove(self.btn)
        self.assertNotIn(self.btn, self.wg.children())

    def test_CMP_03_children_three(self):
        """CMP_03 — 3 widget aggiunti → wg.children() ha 3 elementi."""
        wg = WidgetGroup()
        for _ in range(3):
            wg.add(Button((0, 0, 50, 20), "X", (255, 0, 0), self.font))
        self.assertEqual(len(wg.children()), 3)

    def test_CMP_04_draw_delegates(self):
        """CMP_04 — wg.draw(surface) chiama draw() su tutti i figli."""
        drawn = []

        class _Leaf(UIComponent):
            def handle_event(self, e): return False
            def update(self): pass
            def draw(self, s): drawn.append(True)

        wg = WidgetGroup()
        wg.add(_Leaf())
        wg.add(_Leaf())
        wg.draw(self.surf)
        self.assertEqual(len(drawn), 2)

    def test_CMP_05_handle_event_stops_at_first_consumer(self):
        """CMP_05 — handle_event si ferma al primo widget che gestisce l'evento."""
        order = []

        class _Consumer(UIComponent):
            def handle_event(self, e): order.append("C"); return True
            def update(self): pass
            def draw(self, s): pass

        class _Recorder(UIComponent):
            def handle_event(self, e): order.append("R"); return False
            def update(self): pass
            def draw(self, s): pass

        wg = WidgetGroup()
        wg.add(_Consumer())
        wg.add(_Recorder())
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE,
                                mod=0, unicode=" ", scancode=0)
        wg.handle_event(ev)
        self.assertNotIn("R", order)

    def test_CMP_06_update_all_children(self):
        """CMP_06 — wg.update() chiama update() su tutti i figli."""
        updated = []

        class _Leaf(UIComponent):
            def handle_event(self, e): return False
            def update(self): updated.append(True)
            def draw(self, s): pass

        wg = WidgetGroup()
        for _ in range(3):
            wg.add(_Leaf())
        wg.update()
        self.assertEqual(len(updated), 3)

    def test_CMP_07_button_draw(self):
        """CMP_07 — btn.draw(surface) non solleva eccezioni."""
        self.btn.draw(self.surf)

    def test_CMP_08_button_on_click_via_events(self):
        """CMP_08 — MOUSEBUTTONDOWN+UP su area btn → on_click invocato."""
        clicked = []
        btn = Button((0, 0, 200, 200), "Go", (0, 255, 0), self.font,
                     on_click=lambda: clicked.append(True))
        ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(1, 1), button=1)
        btn.handle_event(ev_down)
        ev_up = pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(1, 1), button=1)
        btn.handle_event(ev_up)
        self.assertEqual(clicked, [True])

    def test_CMP_09_button_on_click_callback(self):
        """CMP_09 — btn.on_click callback chiamata direttamente."""
        called = []
        btn = Button((0, 0, 80, 30), "X", (0, 0, 255), self.font,
                     on_click=lambda: called.append(True))
        btn.on_click()
        self.assertEqual(called, [True])

    def test_CMP_10_panel_draw(self):
        """CMP_10 — Panel.draw(surface) non solleva eccezioni."""
        p = Panel((0, 0, 200, 100))
        p.draw(self.surf)

    def test_CMP_11_healthbar_set_values(self):
        """CMP_11 — hb.set_values(50, 100) aggiorna i valori."""
        hb = HealthBar((0, 0, 100, 20), self.font)
        hb.set_values(50, 100)
        self.assertEqual(hb._val, 50)
        self.assertEqual(hb._mx, 100)

    def test_CMP_12_healthbar_draw(self):
        """CMP_12 — hb.draw(surface) non solleva eccezioni."""
        hb = HealthBar((0, 0, 100, 20), self.font)
        hb.set_values(50, 100)
        hb.draw(self.surf)

    def test_CMP_13_healthbar_update(self):
        """CMP_13 — hb.update() non solleva eccezioni."""
        hb = HealthBar((0, 0, 100, 20), self.font)
        hb.update()

    def test_CMP_14_nested_widget_groups(self):
        """CMP_14 — parent.add(child_group) composizione annidata."""
        parent = WidgetGroup()
        child_group = WidgetGroup()
        child_group.add(Button((0, 0, 50, 20), "X", (255, 0, 0), self.font))
        parent.add(child_group)
        self.assertIn(child_group, parent.children())

    def test_CMP_15_remove_from_empty_group_no_error(self):
        """CMP_15 — wg.remove(button) su gruppo vuoto non solleva eccezioni."""
        wg = WidgetGroup()
        wg.remove(self.btn)


if __name__ == "__main__":
    unittest.main()