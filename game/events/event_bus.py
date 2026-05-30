"""
event_bus.py — Bus degli eventi (pattern Observer / Event Bus).

``EventBus`` è il mediatore centrale: i sistemi si iscrivono agli eventi
che li interessano e pubblicano eventi quando accade qualcosa di rilevante.
Il disaccoppiamento totale tra publisher e subscriber permette di aggiungere
o rimuovere sistemi senza modificare il codice degli altri.

Flusso tipico
-------------
    bus = EventBus()
    bus.subscribe(EventType.ENEMY_KILLED, my_handler)
    bus.publish(EventType.ENEMY_KILLED, {"faction": "zombie"})
    bus.unsubscribe(EventType.ENEMY_KILLED, my_handler)
"""

from __future__ import annotations
from collections import defaultdict
from typing import Callable
from game.events.event_types import EventType


class EventBus:
    """Bus degli eventi che gestisce iscrizione, cancellazione e pubblicazione.

    Ogni ``EventType`` può avere più subscriber (listeners). La pubblicazione
    chiama tutti i listener registrati nell'ordine di iscrizione.
    La lista dei listener viene copiata prima dell'iterazione per evitare
    problemi se un callback modifica le iscrizioni durante la notifica.
    """

    def __init__(self) -> None:
        # defaultdict evita di controllare manualmente se la chiave esiste
        self._listeners: dict[EventType, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Iscrive un callback a un tipo di evento.

        Se il callback è già registrato per quel tipo, l'operazione è no-op
        (nessun duplicato viene aggiunto).

        Args:
            event_type: Il tipo di evento a cui iscriversi.
            callback:   Funzione chiamata con ``data: dict`` quando l'evento è pubblicato.
        """
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Cancella l'iscrizione di un callback a un tipo di evento.

        Se il callback non è registrato per quel tipo, l'operazione è no-op.

        Args:
            event_type: Il tipo di evento.
            callback:   Il callback da rimuovere.
        """
        try:
            self._listeners[event_type].remove(callback)
        except ValueError:
            pass

    def publish(self, event_type: EventType, data: dict = None) -> None:
        """Pubblica un evento, notificando tutti i subscriber iscritti.

        La lista dei listener viene copiata prima dell'iterazione per
        garantire stabilità anche se un callback modifica le iscrizioni.

        Args:
            event_type: Il tipo di evento da pubblicare.
            data:       Dizionario con i dati dell'evento (default: dict vuoto).
        """
        for cb in list(self._listeners[event_type]):
            try:
                cb(data)
            except Exception:
                pass
