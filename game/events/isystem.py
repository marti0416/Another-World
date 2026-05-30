"""
isystem.py — Interfaccia base per tutti i sistemi del gioco (pattern Observer GoF).

Ogni sistema che deve ricevere eventi dall'``EventBus`` implementa ``ISystem``:
- ``initialize()`` iscrive i callback sugli ``EventType`` rilevanti.
- ``cleanup()`` rimuove le iscrizioni per evitare memory leak e callback stale.

I sistemi concreti (``ReputationSystem``, ``WorldRules``, ecc.) ereditano
da questa interfaccia e vengono registrati dal ``GameManager`` all'avvio.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from game.events.event_bus import EventBus


class ISystem(ABC):
    """Interfaccia astratta per i sistemi del gioco.

    Un sistema è un componente autonomo che reagisce agli eventi pubblicati
    sull'``EventBus``. L'inizializzazione e la pulizia delle iscrizioni sono
    responsabilità del sistema stesso, non del bus.
    """

    @abstractmethod
    def initialize(self, bus: EventBus) -> None:
        """Iscrive i callback agli eventi rilevanti sull'EventBus.

        Viene chiamato dal ``GameManager`` durante l'avvio o il cambio di scena.

        Args:
            bus: L'istanza condivisa dell'``EventBus`` del gioco.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Rimuove tutti i callback dall'EventBus.

        Deve essere chiamato prima di distruggere il sistema o cambiare scena,
        per evitare memory leak e chiamate a oggetti già deallocati.
        """
        ...
