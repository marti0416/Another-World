"""
party_system.py — Sistema di gestione del gruppo (party) e dell'etica di coppia.

``PartySystem`` tiene traccia dei personaggi attivi nel gruppo e del valore
di etica di coppia. È un ``ISystem`` minimo: non si iscrive ad eventi ma
espone metodi consultati dagli altri sistemi e dalle screen.
"""

from __future__ import annotations
from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType


class PartySystem(ISystem):
    """Sistema che gestisce i membri del gruppo e l'etica di coppia.

    L'etica di coppia è un valore da -10 a +10 che riflette le decisioni
    morali prese durante il gioco. Viene aggiornato da ``CoupleEthicsSystem``
    (``social_system.py``) tramite eventi ``ETHICS_CHANGED``.

    Attributes:
        couple_ethics: Valore corrente dell'etica di coppia (-10 a +10).
    """

    def __init__(self) -> None:
        self._members: list = []
        self._bus: EventBus | None = None
        self.couple_ethics: int = 0

    def initialize(self, bus: EventBus) -> None:
        """Registra il bus; questo sistema non si iscrive ad eventi.

        Args:
            bus: L'istanza condivisa dell'``EventBus``.
        """
        self._bus = bus

    def cleanup(self) -> None:
        """No-op: nessuna iscrizione da rimuovere."""
        pass

    def add_member(self, character) -> None:
        """Aggiunge un personaggio al gruppo.

        Args:
            character: Oggetto ``Character`` da aggiungere.
        """
        self._members.append(character)

    def all_alive(self) -> bool:
        """Restituisce ``True`` se tutti i membri del gruppo sono in vita."""
        return all(m.is_alive() for m in self._members)

    def any_alive(self) -> bool:
        """Restituisce ``True`` se almeno un membro del gruppo è in vita."""
        return any(m.is_alive() for m in self._members)

    def update_ethics(self, delta: int) -> None:
        """Aggiorna il valore dell'etica di coppia, clampato tra -10 e +10.

        Args:
            delta: Variazione da applicare (positivo = miglioramento morale).
        """
        self.couple_ethics = max(-10, min(10, self.couple_ethics + delta))
