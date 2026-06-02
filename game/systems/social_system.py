"""
social_system.py — Sistema di etica di coppia e pre-dialogo sociale.

Struttura
---------
- ``CoupleEthicsSystem``  : ISystem che gestisce il punteggio di etica (-10/+10).
- ``PreDialogueStance``   : enum degli atteggiamenti disponibili prima di un dialogo.
- ``PreDialogueSystem``   : ISystem che fornisce le opzioni pre-dialogo in base al personaggio.

Il modulo ri-esporta anche le classi di dialogo principali per comodità degli
import nei sistemi client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.events.isystem import ISystem


# ---------------------------------------------------------------------------
# Sistema etica di coppia
# ---------------------------------------------------------------------------

class CoupleEthicsSystem(ISystem):
    """Sistema che gestisce il punteggio di Etica di Coppia.

    Il valore è compreso tra -10 (in crisi) e +10 (uniti).
    Si sottoscrive agli eventi ``ETHICS_CHANGED`` e ``FRIENDLY_FIRE``
    tramite ``EventBus`` (pattern Observer).

    Regole di aggiornamento:
    - ``ETHICS_CHANGED``: applica un delta diretto all'etica.
    - ``FRIENDLY_FIRE``: se il danno supera la soglia, penalizza di -2.
    - Ogni 5 punti di etica guadagnati, entrambi i personaggi ricevono XP bonus.
    - L'uso di armi devastanti produce un delta negativo
      (gestito da ``ReputationSystem`` che pubblica ``ETHICS_CHANGED``).
    - Le interazioni con i Dannati impattano solo l'etica, non le fazioni.

    Attributes:
        FRIENDLY_FIRE_THRESHOLD: Soglia di danno da fuoco amico che penalizza l'etica.
    """

    FRIENDLY_FIRE_THRESHOLD: int = 15

    def __init__(self) -> None:
        self._ethics: int = 0
        self._bus: EventBus | None = None

    def initialize(self, bus: EventBus) -> None:
        """Iscrive i callback agli eventi rilevanti.

        Args:
            bus: L'istanza condivisa dell'``EventBus``.
        """
        self._bus = bus
        bus.subscribe(EventType.ETHICS_CHANGED, self._on_ethics_changed)
        bus.subscribe(EventType.FRIENDLY_FIRE,  self._on_friendly_fire)

    def cleanup(self) -> None:
        """Rimuove le iscrizioni dall'``EventBus``."""
        if self._bus:
            self._bus.unsubscribe(EventType.ETHICS_CHANGED, self._on_ethics_changed)
            self._bus.unsubscribe(EventType.FRIENDLY_FIRE,  self._on_friendly_fire)

    def _on_ethics_changed(self, data: dict) -> None:
        """Applica un delta all'etica e aggiorna il ``GameManager`` se disponibile.

        Ogni 5 punti di etica guadagnati (soglia positiva), assegna 15 XP
        a entrambi i personaggi.

        Data keys:
            delta (int): variazione da applicare.
        """
        delta = data.get("delta", 0)
        self.update_ethics(delta)
        try:
            from game.controller.game_manager import GameManager
            gs = GameManager.get_instance()
            if gs is not None and not getattr(gs, "_updating_ethics", False):
                old      = gs.ethics
                gs.ethics = max(-10, min(10, gs.ethics + delta))
                # Bonus XP ogni 5 punti di etica guadagnati
                if delta > 0 and gs.Rivet and gs.Echo:
                    crossed = (gs.ethics // 5) - (old // 5)
                    if crossed > 0:
                        xp_award = crossed * 15
                        gs.Rivet.stats.gain_xp(xp_award)
                        gs.Echo.stats.gain_xp(xp_award)
                        gs.log(gs.wlog, f"Etica +{xp_award} XP a entrambi (ogni 5 punti)")
        except Exception:
            pass

    def _on_friendly_fire(self, data: dict) -> None:
        """Penalizza l'etica di -2 se il danno da fuoco amico supera la soglia.

        Data keys:
            damage (int): danno inflitto al partner.
        """
        damage = data.get("damage", 0)
        if damage >= self.FRIENDLY_FIRE_THRESHOLD:
            self.update_ethics(-2)
            try:
                from game.controller.game_manager import GameManager
                gs = GameManager.get_instance()
                if gs is not None:
                    gs.ethics = max(-10, min(10, gs.ethics - 2))
            except Exception:
                pass

    @property
    def ethics(self) -> int:
        """Valore corrente dell'etica di coppia (-10 a +10)."""
        return self._ethics

    def update_ethics(self, delta: int) -> None:
        """Aggiorna l'etica e pubblica ``ETHICS_UPDATED`` per aggiornare l'UI.

        Args:
            delta: Variazione da applicare (clampata a [-10, +10]).
        """
        self._ethics = max(-10, min(10, self._ethics + delta))
        if self._bus:
            self._bus.publish(EventType.ETHICS_UPDATED, {"value": self._ethics})

    def get_ethics_label(self) -> str:
        """Restituisce una label testuale per il valore corrente di etica.

        Returns:
            Una delle label: "Uniti", "Affiatati", "Neutrali", "Tesi", "In Crisi".
        """
        if self._ethics >= 7:  return "Uniti"
        if self._ethics >= 3:  return "Affiatati"
        if self._ethics >= 0:  return "Neutrali"
        if self._ethics >= -4: return "Tesi"
        return "In Crisi"


# ---------------------------------------------------------------------------
# Pre-dialogo
# ---------------------------------------------------------------------------

class PreDialogueStance(Enum):
    """Atteggiamenti sociali disponibili prima di avviare un albero di dialogo.

    Ogni stance è associata a un personaggio specifico (Echo o Rivet),
    tranne ``ATTACCA`` e ``IGNORA`` che sono universali.
    """
    EMPATICO    = "Approccio Empatico (Lei)"
    DIPLOMATICO = "Approccio Diplomatico (Lei)"
    MINACCIOSO  = "Approccio Minaccioso (Lui)"
    PRAGMATICO  = "Approccio Diretto/Affari (Lui)"
    ATTACCA     = "Attacca di sorpresa"
    IGNORA      = "Allontanati"


class PreDialogueSystem(ISystem):
    """Sistema che gestisce le opzioni iniziali prima di un albero di dialogo.

    Determina quali atteggiamenti sono disponibili in base al personaggio
    più vicino all'NPC e al tipo di NPC. Sostituisce il vecchio
    ``PreCombatSystem``.
    """

    def __init__(self) -> None:
        self._bus = None

    def initialize(self, bus: EventBus) -> None:
        """Registra il bus; questo sistema non si iscrive ad eventi.

        Args:
            bus: L'istanza condivisa dell'``EventBus``.
        """
        self._bus = bus

    def cleanup(self) -> None:
        """No-op: nessuna iscrizione da rimuovere."""
        pass

    def get_available_options(self, character_role: str,
                              npc_type: str) -> list[PreDialogueStance]:
        """Restituisce le stance disponibili in base al personaggio e al tipo di NPC.

        Per NPC umani, le stance specifiche del personaggio (Echo o Rivet)
        vengono inserite in testa alla lista. ``IGNORA`` e ``ATTACCA``
        sono sempre presenti come ultima risorsa.

        Args:
            character_role: "Echo" o "Rivet" — il personaggio che interagisce.
            npc_type:       "human" o "zombie".

        Returns:
            Lista di ``PreDialogueStance`` disponibili, in ordine di priorità.
        """
        options: list[PreDialogueStance] = [
            PreDialogueStance.IGNORA,
            PreDialogueStance.ATTACCA,
        ]

        if npc_type == "human":
            if character_role == "Echo":
                options.insert(0, PreDialogueStance.DIPLOMATICO)
                options.insert(1, PreDialogueStance.EMPATICO)
            elif character_role == "Rivet":
                options.insert(0, PreDialogueStance.PRAGMATICO)
                options.insert(1, PreDialogueStance.MINACCIOSO)

        return options


# ---------------------------------------------------------------------------
# Re-export classi dialogo
# ---------------------------------------------------------------------------

from game.dialogue.dialogue import (
    DialogueNode,
    DialogueTree,
    SolidaliDialogues,
    DialogueManager,
)

__all__ = [
    "CoupleEthicsSystem",
    "PreDialogueStance",
    "PreDialogueSystem",
    "DialogueNode",
    "DialogueTree",
    "SolidaliDialogues",
    "DialogueManager",
]
