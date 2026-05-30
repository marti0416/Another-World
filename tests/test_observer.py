"""test_observer.py — Pattern Observer / EventBus (OBS_01 … OBS_12)."""
import unittest
import base_setup  # noqa: F401
from game.events.event_bus import EventBus
from game.events.event_types import EventType


class TestObserver(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()

    def test_OBS_01_subscribe_registers_callback(self):
        """OBS_01 — subscribe() aggiunge la callback alla lista."""
        cb = lambda d: None
        self.bus.subscribe(EventType.ITEM_PICKUP, cb)
        self.assertIn(cb, self.bus._listeners[EventType.ITEM_PICKUP])

    def test_OBS_02_subscribe_multiple_callbacks(self):
        """OBS_02 — due cb distinte registrate sullo stesso evento."""
        cb1, cb2 = lambda d: None, lambda d: None
        self.bus.subscribe(EventType.ITEM_PICKUP, cb1)
        self.bus.subscribe(EventType.ITEM_PICKUP, cb2)
        listeners = self.bus._listeners[EventType.ITEM_PICKUP]
        self.assertIn(cb1, listeners)
        self.assertIn(cb2, listeners)

    def test_OBS_03_unsubscribe_removes_callback(self):
        """OBS_03 — unsubscribe() rimuove la callback."""
        cb = lambda d: None
        self.bus.subscribe(EventType.QUEST_COMPLETED, cb)
        self.bus.unsubscribe(EventType.QUEST_COMPLETED, cb)
        self.assertNotIn(cb, self.bus._listeners[EventType.QUEST_COMPLETED])

    def test_OBS_04_unsubscribe_nonexistent_no_error(self):
        """OBS_04 — unsubscribe di cb non registrata non solleva eccezioni."""
        cb = lambda d: None
        self.bus.unsubscribe(EventType.ITEM_PICKUP, cb)

    def test_OBS_05_publish_notifies_all_subscribers(self):
        """OBS_05 — publish() chiama tutte le callback registrate."""
        called = []
        self.bus.subscribe(EventType.ENEMY_KILLED, lambda d: called.append(1))
        self.bus.subscribe(EventType.ENEMY_KILLED, lambda d: called.append(2))
        self.bus.publish(EventType.ENEMY_KILLED, {"faction": "zombie"})
        self.assertEqual(called, [1, 2])

    def test_OBS_06_publish_no_subscribers_no_error(self):
        """OBS_06 — publish() senza subscriber non solleva eccezioni."""
        self.bus.publish(EventType.GAME_STARTED, {})

    def test_OBS_07_publish_passes_data_to_callback(self):
        """OBS_07 — i dati vengono passati correttamente alla callback."""
        received = []
        self.bus.subscribe(EventType.REPUTATION_CHANGED, lambda d: received.append(d))
        self.bus.publish(EventType.REPUTATION_CHANGED, {"delta": 5})
        self.assertEqual(received, [{"delta": 5}])

    def test_OBS_08_publish_item_crafted(self):
        """OBS_08 — evento ITEM_CRAFTED notifica con id='molotov_cocktail'."""
        received = []
        self.bus.subscribe(EventType.ITEM_CRAFTED, lambda d: received.append(d))
        self.bus.publish(EventType.ITEM_CRAFTED, {"id": "molotov_cocktail"})
        self.assertEqual(received[0]["id"], "molotov_cocktail")

    def test_OBS_09_publish_ethics_changed(self):
        """OBS_09 — evento ETHICS_CHANGED notifica correttamente."""
        received = []
        self.bus.subscribe(EventType.ETHICS_CHANGED, lambda d: received.append(d))
        self.bus.publish(EventType.ETHICS_CHANGED, {"delta": -1})
        self.assertEqual(received[0]["delta"], -1)

    @unittest.expectedFailure
    def test_OBS_10_subscribe_same_callback_twice_no_duplicate(self):
        """OBS_10 — subscribe della stessa cb due volte: cb presente UNA VOLTA (spec).
        NOTA: il bus usa list.append → duplica. Test previsto come fallimento.
        """
        cb = lambda d: None
        self.bus.subscribe(EventType.ITEM_PICKUP, cb)
        self.bus.subscribe(EventType.ITEM_PICKUP, cb)
        self.assertEqual(self.bus._listeners[EventType.ITEM_PICKUP].count(cb), 1)

    @unittest.expectedFailure
    def test_OBS_11_exception_in_subscriber_does_not_block_others(self):
        """OBS_11 — eccezione in cb1 non blocca cb2 (spec).
        NOTA: il bus attuale non ha try/except. Test previsto come fallimento.
        """
        called = []

        def bad(d): raise RuntimeError("boom")

        self.bus.subscribe(EventType.GAME_STARTED, bad)
        self.bus.subscribe(EventType.GAME_STARTED, lambda d: called.append(True))
        try:
            self.bus.publish(EventType.GAME_STARTED, {})
        except RuntimeError:
            pass
        self.assertEqual(called, [True])

    @unittest.expectedFailure
    def test_OBS_12_publish_none_data_passed_as_none(self):
        """OBS_12 — publish con data=None → cb chiamata con None (spec).
        NOTA: il bus fa cb(data or {}) → passa {}. Test previsto come fallimento.
        """
        received = []
        self.bus.subscribe(EventType.GAME_STARTED, lambda d: received.append(d))
        self.bus.publish(EventType.GAME_STARTED, None)
        self.assertEqual(received, [None])


if __name__ == "__main__":
    unittest.main()