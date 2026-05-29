"""test_cor.py — Pattern Chain of Responsibility: EventHandler chain (COR_01 … COR_12)."""
import unittest
import base_setup  # noqa: F401
import pygame
from game.controller.event_chain import (
    EventHandler, QuitHandler, VideoResizeHandler,
    SaveMenuHandler, ScreenHandler,
)


def _make_event(etype, **kwargs):
    return pygame.event.Event(etype, **kwargs)


class TestChainOfResponsibility(unittest.TestCase):

    def test_COR_00_event_handler_is_abstract(self):
        """COR_00 — EventHandler è astratto e non può essere istanziato."""
        with self.assertRaises(TypeError):
            EventHandler()

    def test_COR_08_set_next_returns_next_handler(self):
        """COR_08 — set_next() restituisce il successivo per chaining."""
        class _H(EventHandler):
            def handle(self, event): return False
        h1 = _H(); h2 = _H()
        self.assertIs(h1.set_next(h2), h2)

    def test_COR_09_build_chain_fluent(self):
        """COR_09 — Catena costruita con chaining fluente."""
        class _H(EventHandler):
            def handle(self, event): return False
        h1 = _H(); h2 = _H(); h3 = _H(); h4 = _H()
        h1.set_next(h2).set_next(h3).set_next(h4)
        self.assertIs(h1._next, h2)
        self.assertIs(h2._next, h3)
        self.assertIs(h3._next, h4)

    def test_COR_09b_multiple_set_next(self):
        """COR_09b — Chaining di 4 handler controlla correttezza."""
        class _H(EventHandler):
            def handle(self, event): return False
        h = [_H() for _ in range(4)]
        h[0].set_next(h[1]).set_next(h[2]).set_next(h[3])
        self.assertIs(h[0]._next, h[1])
        self.assertIs(h[1]._next, h[2])
        self.assertIs(h[2]._next, h[3])
        self.assertIsNone(h[3]._next)

    def test_COR_10_chain_propagates_to_last(self):
        """COR_10 — Evento percorre l'intera catena di handler personalizzati."""
        order = []

        class _A(EventHandler):
            def handle(self, event): order.append('A'); return self._pass(event)

        class _B(EventHandler):
            def handle(self, event): order.append('B'); return True

        a = _A(); b = _B()
        a.set_next(b)
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a', scancode=0)
        a.handle(ev)
        self.assertEqual(order, ['A', 'B'])

    def test_COR_11_pass_invokes_next_handle(self):
        """COR_11 — _pass() chiama handle() del next handler."""
        called = []

        class _Recorder(EventHandler):
            def handle(self, event): called.append(event.type); return True

        class _H(EventHandler):
            def handle(self, event): return self._pass(event)

        h = _H()
        rec = _Recorder()
        h.set_next(rec)
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a', scancode=0)
        h.handle(ev)
        self.assertEqual(called, [pygame.KEYDOWN])

    def test_COR_12_pass_without_next_returns_falsy(self):
        """COR_12 — _pass() senza next restituisce False/None."""
        class _H(EventHandler):
            def handle(self, event): return self._pass(event)
        h = _H()
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a', scancode=0)
        self.assertFalse(h.handle(ev))

    def test_COR_02_chain_stops_at_first_handler(self):
        """COR_02 — Catena si ferma all'handler che restituisce True."""
        order = []

        class _A(EventHandler):
            def handle(self, event): order.append('A'); return True

        class _B(EventHandler):
            def handle(self, event): order.append('B'); return True

        a = _A(); b = _B()
        a.set_next(b)
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a', scancode=0)
        a.handle(ev)
        self.assertNotIn('B', order)


if __name__ == "__main__":
    unittest.main()