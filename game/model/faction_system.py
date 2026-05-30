"""
faction_system.py — Sistema di reputazione e gestione delle fazioni.

Struttura
---------
- ``FactionID``        : enum delle fazioni del gioco.
- ``Faction``          : dataclass con reputazione corrente e flag di ostilità.
- ``FactionCreator``   : Creator astratto GoF (Factory Method).
- ``*Creator``         : ConcreteCreator per ogni fazione.
- ``FactionFactory``   : Facade di retrocompatibilità.
- ``ReputationSystem`` : ISystem che reagisce agli eventi e aggiorna le fazioni.
- ``SpawnManager``     : tabella di probabilità di spawn per bioma.

Pattern utilizzati
------------------
- **Factory Method GoF** — ogni ``FactionCreator`` crea una specifica ``Faction``.
- **Observer GoF**        — ``ReputationSystem`` si iscrive all'``EventBus``.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.events.isystem import ISystem


# ---------------------------------------------------------------------------
# Enum fazioni
# ---------------------------------------------------------------------------

class FactionID(Enum):
    """Identificatori univoci delle fazioni del gioco.

    Usati come chiavi nel dizionario interno di ``ReputationSystem``
    e come valori nei payload degli eventi.
    """
    SOLIDALI   = "solidali"
    ERRANTI    = "erranti"
    DANNATI    = "dannati"
    RAZZIATORI = "razziatori"
    ZOMBIE     = "zombie"


# ---------------------------------------------------------------------------
# Prodotto — Faction
# ---------------------------------------------------------------------------

@dataclass
class Faction:
    """Rappresenta una fazione del gioco con reputazione e stato di ostilità.

    La ``current_reputation`` viene inizializzata da ``base_reputation`` in
    ``__post_init__`` e modificata durante il gioco tramite ``modify_reputation()``.
    Il range è clampato tra -50 e +50.

    Attributes:
        faction_id:             Identificatore univoco (``FactionID``).
        name:                   Nome visualizzato nell'interfaccia.
        base_reputation:        Reputazione iniziale (default 0).
        alignment:              Allineamento narrativo ("friendly", "neutral", "hostile").
        is_permanently_hostile: Se ``True``, la fazione è sempre ostile indipendentemente
                                dalla reputazione.
        ui_marker_color:        Colore RGB del marker sulla mappa (default bianco).
        trade_in_safe_zone:     Se ``True``, il commercio è disponibile solo in zona sicura.
        current_reputation:     Reputazione attuale (inizializzata da ``base_reputation``).
    """
    faction_id:       FactionID
    name:             str
    base_reputation:  int   = 0
    alignment:        str   = "neutral"
    is_permanently_hostile: bool = False

    ui_marker_color:  tuple = field(default_factory=lambda: (255, 255, 255))
    trade_in_safe_zone: bool = False

    # Inizializzato in __post_init__, non passato al costruttore
    current_reputation: int = field(init=False)

    def __post_init__(self) -> None:
        """Inizializza ``current_reputation`` dal valore base."""
        self.current_reputation = self.base_reputation

    def is_hostile(self, threshold: int = -10) -> bool:
        """Verifica se la fazione è ostile verso i giocatori.

        Una fazione è ostile se è permanentemente tale, oppure se la reputazione
        corrente è pari o inferiore alla soglia (default -10).

        Args:
            threshold: Soglia di reputazione sotto la quale la fazione diventa ostile.

        Returns:
            ``True`` se ostile, ``False`` altrimenti.
        """
        return self.is_permanently_hostile or self.current_reputation <= threshold

    def modify_reputation(self, delta: int) -> None:
        """Modifica la reputazione, clampandola tra -50 e +50.

        Args:
            delta: Variazione da applicare (positiva = miglioramento, negativa = peggioramento).
        """
        self.current_reputation = max(-50, min(50, self.current_reputation + delta))

    def make_permanently_hostile(self) -> None:
        """Rende la fazione permanentemente ostile, ignorando la reputazione futura."""
        self.is_permanently_hostile = True

    def __repr__(self) -> str:
        return (f"Faction({self.name}, rep={self.current_reputation}, "
                f"hostile={self.is_hostile()})")


# ---------------------------------------------------------------------------
# Creator astratto — Factory Method GoF
# ---------------------------------------------------------------------------

class FactionCreator(ABC):
    """Creator astratto GoF (Factory Method) per la creazione delle Faction.

    Ogni sottoclasse concreta sovrascrive ``create_faction()`` per istanziare
    la specifica ``Faction`` con i parametri corretti.
    """

    @abstractmethod
    def create_faction(self) -> Faction:
        """Factory Method: istanzia e restituisce la Faction concreta."""
        ...

    def build(self) -> Faction:
        """Operazione pubblica: chiama il factory method e restituisce la Faction."""
        return self.create_faction()


# ---------------------------------------------------------------------------
# ConcreteCreator — uno per ogni fazione
# ---------------------------------------------------------------------------

class SolidaliCreator(FactionCreator):
    """Creator per i Solidali (fazione alleata, commercio in zona sicura)."""

    def create_faction(self) -> Faction:
        return Faction(
            faction_id=FactionID.SOLIDALI,
            name="Solidali",
            base_reputation=20,
            alignment="friendly",
            ui_marker_color=(57, 255, 20),  # Verde brillante
            trade_in_safe_zone=True,
        )


class ErrantiCreator(FactionCreator):
    """Creator per gli Erranti (fazione neutrale con sostanze chimiche)."""

    def create_faction(self) -> Faction:
        return Faction(
            faction_id=FactionID.ERRANTI,
            name="Erranti",
            base_reputation=0,
            alignment="neutral",
            ui_marker_color=(0, 120, 255),  # Blu
        )


class DannatiCreator(FactionCreator):
    """Creator per i Dannati (fazione ostile con armi da fuoco)."""

    def create_faction(self) -> Faction:
        return Faction(
            faction_id=FactionID.DANNATI,
            name="Dannati",
            base_reputation=-15,
            alignment="hostile",
        )


class RazziatoriCreator(FactionCreator):
    """Creator per i Razziatori (fazione molto ostile con armi da taglio)."""

    def create_faction(self) -> Faction:
        return Faction(
            faction_id=FactionID.RAZZIATORI,
            name="Razziatori",
            base_reputation=-30,
            alignment="hostile",
        )


class ZombieCreator(FactionCreator):
    """Creator per gli Zombie (fazione sempre ostile, reputazione irrecuperabile)."""

    def create_faction(self) -> Faction:
        f = Faction(
            faction_id=FactionID.ZOMBIE,
            name="Zombie",
            base_reputation=-100,
            alignment="hostile",
        )
        f.make_permanently_hostile()
        return f


# ---------------------------------------------------------------------------
# Facade di retrocompatibilità
# ---------------------------------------------------------------------------

class FactionFactory:
    """Facade di retrocompatibilità — API pubblica invariata.

    Delega internamente ai ConcreteCreator GoF; tutto il codice esistente
    che chiama ``FactionFactory.create_*()`` continua a funzionare senza modifiche.
    """

    @staticmethod
    def create_solidali() -> Faction:
        """Crea la fazione Solidali con reputazione iniziale +20."""
        return SolidaliCreator().build()

    @staticmethod
    def create_erranti() -> Faction:
        """Crea la fazione Erranti con reputazione iniziale 0."""
        return ErrantiCreator().build()

    @staticmethod
    def create_dannati() -> Faction:
        """Crea la fazione Dannati con reputazione iniziale -15."""
        return DannatiCreator().build()

    @staticmethod
    def create_razziatori() -> Faction:
        """Crea la fazione Razziatori con reputazione iniziale -30."""
        return RazziatoriCreator().build()

    @staticmethod
    def create_zombie() -> Faction:
        """Crea la fazione Zombie, permanentemente ostile."""
        return ZombieCreator().build()


# ---------------------------------------------------------------------------
# Sistema reputazione — Observer GoF
# ---------------------------------------------------------------------------

class ReputationSystem(ISystem):
    """Sistema che gestisce la reputazione del giocatore verso le fazioni.

    Si iscrive agli ``EventType`` rilevanti sull'``EventBus`` e aggiorna le
    ``Faction`` di conseguenza. È un ``ISystem``: il ``GameManager`` chiama
    ``initialize()`` all'avvio e ``cleanup()`` prima di cambiare scena.

    Costanti di classe
    ------------------
    - ``REP_SAVE_FROM_INFECTED``   : bonus reputazione per aver salvato NPC dagli infetti.
    - ``REP_KILL_ACTIVE_ZOMBIE``   : bonus reputazione per aver ucciso uno zombie attivo.
    - ``REP_TRADE_WITH_Echo``      : moltiplicatore sconto commercio per Echo (15% di sconto).
    - ``ETHICS_FRIENDLY_FIRE_THRESHOLD``: soglia oltre la quale il fuoco amico impatta l'etica.
    """

    REP_SAVE_FROM_INFECTED: int   = +15
    REP_KILL_ACTIVE_ZOMBIE: int   = +5
    REP_TRADE_WITH_Echo:     float = 0.85   # Echo paga l'85% del prezzo base
    ETHICS_FRIENDLY_FIRE_THRESHOLD: int = 15

    def __init__(self) -> None:
        self._factions: dict[FactionID, Faction] = {}
        self._bus: EventBus | None = None
        self._in_safe_zone: bool = False

    def initialize(self, bus: EventBus) -> None:
        """Crea le fazioni e iscrive i callback agli eventi rilevanti.

        Args:
            bus: L'istanza condivisa dell'``EventBus`` del gioco.
        """
        self._bus = bus
        self._factions = {
            FactionID.SOLIDALI:   FactionFactory.create_solidali(),
            FactionID.ERRANTI:    FactionFactory.create_erranti(),
            FactionID.DANNATI:    FactionFactory.create_dannati(),
            FactionID.RAZZIATORI: FactionFactory.create_razziatori(),
            FactionID.ZOMBIE:     FactionFactory.create_zombie(),
        }
        bus.subscribe(EventType.ENEMY_KILLED,       self._on_enemy_killed)
        bus.subscribe(EventType.NPC_SAVED,          self._on_npc_saved)
        bus.subscribe(EventType.NPC_DAMAGED,        self._on_npc_damaged)
        bus.subscribe(EventType.ZONE_ENTERED,       self._on_zone_entered)
        bus.subscribe(EventType.DEVASTATING_WEAPON, self._on_devastating_weapon)

    def cleanup(self) -> None:
        """Rimuove tutte le iscrizioni dall'EventBus."""
        if self._bus:
            self._bus.unsubscribe(EventType.ENEMY_KILLED,       self._on_enemy_killed)
            self._bus.unsubscribe(EventType.NPC_SAVED,          self._on_npc_saved)
            self._bus.unsubscribe(EventType.NPC_DAMAGED,        self._on_npc_damaged)
            self._bus.unsubscribe(EventType.ZONE_ENTERED,       self._on_zone_entered)
            self._bus.unsubscribe(EventType.DEVASTATING_WEAPON, self._on_devastating_weapon)

    # --- Handler degli eventi ---

    def _on_enemy_killed(self, data: dict) -> None:
        """Aumenta la reputazione solo uccidendo zombie che stavano attaccando attivamente.

        Data keys:
            faction (str): fazione del nemico ucciso.
            was_attacking_actively (bool): se stava attaccando al momento della morte.
        """
        faction_id      = data.get("faction", "")
        was_attacking   = data.get("was_attacking_actively", False)

        if faction_id == FactionID.ZOMBIE.value and was_attacking:
            for fid in (FactionID.SOLIDALI, FactionID.ERRANTI):
                self._factions[fid].modify_reputation(self.REP_KILL_ACTIVE_ZOMBIE)

    def _on_npc_saved(self, data: dict) -> None:
        """Migliora la reputazione con la fazione dell'NPC salvato dagli infetti.

        Data keys:
            faction (str): fazione dell'NPC salvato.
        """
        faction_id_str = data.get("faction", "")
        try:
            fid = FactionID(faction_id_str)
        except ValueError:
            return
        faction = self._factions.get(fid)
        if faction and not faction.is_hostile():
            faction.modify_reputation(self.REP_SAVE_FROM_INFECTED)

    def _on_npc_damaged(self, data: dict) -> None:
        """Rende gli Erranti permanentemente ostili se un loro membro viene ferito.

        Data keys:
            faction (str): fazione dell'NPC danneggiato.
        """
        faction_id_str = data.get("faction", "")
        if faction_id_str == FactionID.ERRANTI.value:
            self._factions[FactionID.ERRANTI].make_permanently_hostile()

    def _on_zone_entered(self, data: dict) -> None:
        """Gestisce gli effetti ambientali al cambio di zona.

        Zona "chemical_leak": pubblica un tick di danno chimico se il giocatore
        non ha protezione adeguata.
        Zona "city_forest": pubblica un evento di priorità spawn verso nemici umani.

        Data keys:
            zone_type (str): tipo di zona ("chemical_leak", "city_forest", "safe_zone", ecc.).
            has_protection (bool): se il giocatore ha protezione chimica.
        """
        zone_type = data.get("zone_type", "")
        self._in_safe_zone = (zone_type == "safe_zone")

        if zone_type == "chemical_leak":
            if self._bus:
                self._bus.publish(EventType.CHEMICAL_DAMAGE_TICK, {
                    "dps": 3,
                    "protected": data.get("has_protection", False),
                })
        elif zone_type == "city_forest":
            if self._bus:
                self._bus.publish(EventType.SPAWN_PRIORITY, {
                    "prefer_human": True,
                    "zone": "city_forest",
                })

    def _on_devastating_weapon(self, data: dict) -> None:
        """Applica penalità di reputazione e penalità etica per l'uso di armi devastanti.

        Riduce la reputazione con Solidali ed Erranti e pubblica un evento
        ``ETHICS_CHANGED`` per aggiornare l'etica di coppia.

        Data keys:
            reputation_penalty (int): penalità di reputazione (default -20).
            ethics_delta (int):       variazione dell'etica di coppia (default -3).
        """
        rep_penalty  = data.get("reputation_penalty", -20)
        ethics_delta = data.get("ethics_delta", -3)

        for fid in (FactionID.SOLIDALI, FactionID.ERRANTI):
            self._factions[fid].modify_reputation(rep_penalty)

        if self._bus:
            self._bus.publish(EventType.ETHICS_CHANGED, {"delta": ethics_delta})

    # --- API pubblica ---

    def get_faction(self, fid: FactionID) -> Faction | None:
        """Restituisce la ``Faction`` con l'id specificato, o ``None`` se non esiste.

        Args:
            fid: Identificatore della fazione.
        """
        return self._factions.get(fid)

    def is_trade_available(self, fid: FactionID) -> bool:
        """Verifica se il commercio con la fazione è disponibile nella situazione attuale.

        I Solidali commerciano solo in zona sicura; le altre fazioni commerciano
        se non sono ostili.

        Args:
            fid: Identificatore della fazione.

        Returns:
            ``True`` se il commercio è disponibile, ``False`` altrimenti.
        """
        faction = self._factions.get(fid)
        if faction is None:
            return False
        if fid == FactionID.SOLIDALI:
            return self._in_safe_zone and faction.trade_in_safe_zone
        return not faction.is_hostile()

    def apply_Echo_trade_discount(self, base_price: int) -> int:
        """Calcola il prezzo scontato per Echo quando commercia con i Solidali.

        Echo ottiene tariffe di cambio migliori (85% del prezzo base).

        Args:
            base_price: Prezzo base dell'oggetto in crediti.

        Returns:
            Prezzo scontato (minimo 1 credito).
        """
        return max(1, int(base_price * self.REP_TRADE_WITH_Echo))

    def handle_dannati_interaction(self, ethics_delta: int) -> None:
        """Gestisce l'impatto etico di un'interazione con i Dannati.

        Le interazioni con i Dannati impattano solo l'Etica di Coppia,
        non la reputazione con le altre fazioni.

        Args:
            ethics_delta: Variazione dell'etica di coppia (negativa = peggioramento).
        """
        if self._bus:
            self._bus.publish(EventType.ETHICS_CHANGED, {"delta": ethics_delta})

    def handle_farm_decision(self, choice: str) -> None:
        """Gestisce la scelta del destino della Fattoria dopo l'infestazione.

        Ogni scelta produce effetti diversi su reputazione e etica di coppia.

        Args:
            choice: Decisione presa ("liberate", "claim" o "abandon").
        """
        rep_effects = {
            "liberate": {FactionID.SOLIDALI: +10, FactionID.ERRANTI: +5},
            "claim":    {FactionID.RAZZIATORI: +5},
            "abandon":  {},
        }
        ethics_effects = {"liberate": +2, "claim": -1, "abandon": 0}

        for fid, delta in rep_effects.get(choice, {}).items():
            if fid in self._factions:
                self._factions[fid].modify_reputation(delta)

        ethics = ethics_effects.get(choice, 0)
        if ethics != 0 and self._bus:
            self._bus.publish(EventType.ETHICS_CHANGED, {"delta": ethics})

    def handle_coup_de_grace(self, target_faction: str) -> None:
        """Gestisce l'impatto etico del Colpo di Grazia su un Dannato.

        Produce una piccola penalità etica, senza impattare le reputazioni
        con le altre fazioni.

        Args:
            target_faction: Fazione del nemico su cui è stato eseguito il colpo di grazia.
        """
        if target_faction == FactionID.DANNATI.value:
            self.handle_dannati_interaction(ethics_delta=-1)


# ---------------------------------------------------------------------------
# SpawnManager
# ---------------------------------------------------------------------------

class SpawnManager:
    """Gestore della probabilità di spawn per bioma.

    Determina se lo spawn di un'entità è di tipo umano o zombie in base
    al bioma corrente. Nel Bosco Cittadino, la priorità è invertita: 70%
    nemici umani vs 30% zombie.

    Invocato tipicamente da ``WorldRules`` (``world_rules.py``).
    """

    SPAWN_TABLE: dict[str, dict] = {
        "city_forest": {
            "human":  0.70,   # Bosco cittadino: priorità umana
            "zombie": 0.30,
        },
        "default": {
            "human":  0.20,   # Zone generiche: prevalenza zombie
            "zombie": 0.80,
        },
    }

    @classmethod
    def pick_spawn_type(cls, biome: str) -> str:
        """Seleziona il tipo di entità da spawnare in base al bioma.

        Usa una selezione casuale pesata con le probabilità della ``SPAWN_TABLE``.
        Se il bioma non è nella tabella, usa il profilo "default".

        Args:
            biome: Identificatore del bioma (es. "city_forest", "default").

        Returns:
            "human" o "zombie" in base al risultato della selezione.
        """
        table = cls.SPAWN_TABLE.get(biome, cls.SPAWN_TABLE["default"])
        roll  = random.random()
        cumulative = 0.0
        for spawn_type, prob in table.items():
            cumulative += prob
            if roll <= cumulative:
                return spawn_type
        return "zombie"
