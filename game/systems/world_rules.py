"""
world_rules.py — Regole di mondo: clamp coordinate, aggro, pattuglie, rianimazione.

Struttura
---------
- ``MapBounds``        : clamp delle coordinate in tile della griglia.
- ``AggroTrigger``     : trigger di aggressione basato su raggio euclideo.
- ``PatrolZone``       : zona di pattuglia rettangolare per fazioni umane.
- ``WorldRulesSystem`` : ISystem che orchestra tutte le regole via EventBus.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.events.isystem import ISystem


# ---------------------------------------------------------------------------
# Clamp coordinate
# ---------------------------------------------------------------------------

class MapBounds:
    """Clamp delle coordinate dei giocatori entro i limiti della griglia.

    La mappa di esplorazione è 64×48 tile (colonne 0–63, righe 0–47).
    Usato dal ``GameManager`` dopo ogni aggiornamento di posizione.
    """

    COLS: int = 64
    ROWS: int = 48

    @classmethod
    def clamp(cls, col: int, row: int) -> tuple[int, int]:
        """Applica il clamp a una coordinata (col, row).

        Args:
            col: Colonna da clampare.
            row: Riga da clampare.

        Returns:
            Coppia ``(col, row)`` garantita entro ``[0, COLS-1] × [0, ROWS-1]``.
        """
        col = max(0, min(cls.COLS - 1, col))
        row = max(0, min(cls.ROWS - 1, row))
        return col, row

    @classmethod
    def clamp_vec2(cls, pos: tuple[int, int]) -> tuple[int, int]:
        """Overload per tuple (col, row).

        Args:
            pos: Coppia ``(col, row)`` da clampare.
        """
        return cls.clamp(pos[0], pos[1])

    @classmethod
    def is_in_bounds(cls, col: int, row: int) -> bool:
        """Verifica se una coordinata è entro i limiti della griglia.

        Returns:
            ``True`` se la coordinata è valida.
        """
        return 0 <= col < cls.COLS and 0 <= row < cls.ROWS


# ---------------------------------------------------------------------------
# Trigger aggro
# ---------------------------------------------------------------------------

@dataclass
class AggroTrigger:
    """Trigger di battaglia basato sulla distanza euclidea dal nemico.

    Sostituisce il vecchio sistema casuale (0.4% per tile) con una logica
    deterministica: l'aggressione scatta solo quando almeno un giocatore
    si trova entro ``aggro_radius`` tile dal nemico.

    Il raggio massimo è 1.5 tile per evitare aggro a distanza elevata.

    Attributes:
        enemy_type:   Tipo di nemico ("zombie", "human", "razziatori", ecc.).
        aggro_radius: Raggio di aggro in tile (clampato a max 1.5).
        position:     Posizione (col, row) del nemico sulla griglia.
        faction:      Fazione di appartenenza.
        is_active:    ``False`` dopo che il trigger è stato attivato (evita doppi incontri).
        DEFAULT_RADII: Raggi di default per tipo di nemico.
    """

    enemy_type:   str
    aggro_radius: float
    position:     tuple[int, int]
    faction:      str = "zombie"
    is_active:    bool = True
    wait_for_leave: bool = False  # True → non aggrare finché il player non esce dal range

    DEFAULT_RADII: dict = field(default_factory=lambda: {
        "zombie":    1.5,
        "hellhound": 1.5,
        "meat_giant":1.5,
        "razziatori":1.5,
        "erranti":   1.5,
        "sulfur":    1.5,
    })

    def __post_init__(self) -> None:
        """Applica il raggio di default e il clamp al massimo di 1.5 tile."""
        if self.aggro_radius <= 0:
            self.aggro_radius = self.DEFAULT_RADII.get(self.enemy_type, 1.5)
        else:
            self.aggro_radius = min(self.aggro_radius, 1.5)

    def check_aggro(self, player_pos: tuple[int, int],
                    player2_pos: tuple[int, int] | None = None) -> bool:
        """Verifica se almeno un giocatore è dentro il raggio di aggro.

        Args:
            player_pos:  Posizione del primo giocatore (col, row).
            player2_pos: Posizione del secondo giocatore (opzionale).

        Returns:
            ``True`` se l'aggressione scatta, ``False`` altrimenti o se non attivo.
        """
        if not self.is_active:
            return False

        def _dist(pos: tuple[int, int]) -> float:
            dx = pos[0] - self.position[0]
            dy = pos[1] - self.position[1]
            return math.sqrt(dx * dx + dy * dy)

        if _dist(player_pos) <= self.aggro_radius:
            return True
        if player2_pos is not None and _dist(player2_pos) <= self.aggro_radius:
            return True
        return False

    @classmethod
    def from_npc_data(cls, npc_data: dict) -> "AggroTrigger":
        """Factory che costruisce un ``AggroTrigger`` da un dizionario NPC.

        Args:
            npc_data: Dict NPC da ``world_data.NPCS``, con chiavi "faction",
                      "aggro_radius" (opzionale) e "pos".

        Returns:
            Nuovo ``AggroTrigger`` configurato.
        """
        etype = npc_data.get("faction", "zombie")
        return cls(
            enemy_type=etype,
            aggro_radius=npc_data.get("aggro_radius", 0),
            position=tuple(npc_data.get("pos", (0, 0))),
            faction=etype,
        )


# ---------------------------------------------------------------------------
# Zona di pattuglia
# ---------------------------------------------------------------------------

@dataclass
class PatrolZone:
    """Zona di pattuglia rettangolare per fazioni umane.

    Se il giocatore entra nell'area, si genera un incontro condizionato
    alla reputazione corrente verso la fazione di pattuglia.

    Attributes:
        faction:        Fazione che pattuglia la zona.
        top_left:       Angolo superiore-sinistro in tile (col, row).
        bottom_right:   Angolo inferiore-destro in tile (col, row).
        aggro_on_sight: Se ``True``, l'incontro è sempre ostile (es. Razziatori).
    """

    faction:        str
    top_left:       tuple[int, int]
    bottom_right:   tuple[int, int]
    aggro_on_sight: bool = False

    def contains(self, pos: tuple[int, int]) -> bool:
        """Verifica se una posizione è dentro la zona di pattuglia.

        Args:
            pos: Posizione (col, row) da verificare.

        Returns:
            ``True`` se la posizione è nell'area rettangolare della zona.
        """
        col, row = pos
        c0, r0 = self.top_left
        c1, r1 = self.bottom_right
        return c0 <= col <= c1 and r0 <= row <= r1

    def is_hostile_encounter(self, faction_rep: int) -> bool:
        """Decide se l'incontro con questa zona è ostile.

        I Razziatori (``aggro_on_sight = True``) sono sempre ostili.
        Le altre fazioni dipendono dalla reputazione (ostile se ≤ -10).

        Args:
            faction_rep: Reputazione corrente verso questa fazione.

        Returns:
            ``True`` se l'incontro deve essere ostile.
        """
        if self.aggro_on_sight:
            return True
        return faction_rep <= -10


# ---------------------------------------------------------------------------
# Sistema regole di mondo
# ---------------------------------------------------------------------------

class WorldRulesSystem(ISystem):
    """Orchestratore delle regole di mondo.

    Gestisce:
    - Clamp delle coordinate dei giocatori (``clamp_player_pos``).
    - Trigger di aggro per ogni NPC registrato (``_on_player_moved``).
    - Zone di pattuglia per fazioni umane (``_on_player_moved``).
    - Danno continuo in zona Chemical Leak (``_on_chemical_tick``).
    - Rianimazione casuale dei cadaveri zombie (``_on_enemy_killed``).

    Attributes:
        CHEMICAL_DPS: Danno per frame in zona chimica senza protezione.
    """

    CHEMICAL_DPS: int = 3

    def __init__(self) -> None:
        self._bus:             EventBus | None        = None
        self._aggro_triggers:  list[AggroTrigger]     = []
        self._patrol_zones:    list[PatrolZone]       = []
        self._corpse_map:      dict                   = {}
        self._p1_pos: tuple[int, int] | None = None
        self._p2_pos: tuple[int, int] | None = None

    def initialize(self, bus: EventBus) -> None:
        """Iscrive i callback agli eventi rilevanti.

        Args:
            bus: L'istanza condivisa dell'``EventBus``.
        """
        self._bus = bus
        bus.subscribe(EventType.PLAYER_MOVED,         self._on_player_moved)
        bus.subscribe(EventType.ENEMY_KILLED,         self._on_enemy_killed)
        bus.subscribe(EventType.CHEMICAL_DAMAGE_TICK, self._on_chemical_tick)

    def cleanup(self) -> None:
        """Rimuove le iscrizioni dall'``EventBus``."""
        if self._bus:
            self._bus.unsubscribe(EventType.PLAYER_MOVED,         self._on_player_moved)
            self._bus.unsubscribe(EventType.ENEMY_KILLED,         self._on_enemy_killed)
            self._bus.unsubscribe(EventType.CHEMICAL_DAMAGE_TICK, self._on_chemical_tick)

    def register_aggro(self, trigger: AggroTrigger) -> None:
        """Registra un trigger di aggro nel sistema.

        Args:
            trigger: Il trigger da registrare.
        """
        self._aggro_triggers.append(trigger)

    def register_patrol(self, zone: PatrolZone) -> None:
        """Registra una zona di pattuglia nel sistema.

        Args:
            zone: La zona di pattuglia da registrare.
        """
        self._patrol_zones.append(zone)

    def build_aggro_from_npc_list(self, npcs: list[dict]) -> None:
        """Costruisce ``AggroTrigger`` per ogni NPC della lista.

        Esclude automaticamente gli NPC già sconfitti (presenti in
        ``GameManager.defeated_npcs``).

        Args:
            npcs: Lista di dizionari NPC (da ``world_data.NPCS``).
        """
        try:
            from game.controller.game_manager import GameManager
            gs = GameManager.get_instance()
            defeated  = gs.defeated_npcs
            fled_keys = gs.fled_npcs
        except Exception:
            defeated  = set()
            fled_keys = set()

        for npc in npcs:
            npc_key = (npc.get("name", ""), tuple(npc.get("_local_pos") or npc.get("pos", ())))
            if npc_key in defeated:
                continue
            trigger = AggroTrigger.from_npc_data(npc)
            # Dopo un caricamento, i NPC da cui si è fuggiti non devono aggrarare
            # immediatamente: attendono che il player si allontani prima.
            if npc_key in fled_keys:
                trigger.wait_for_leave = True
            self.register_aggro(trigger)

    @staticmethod
    def clamp_player_pos(col: int, row: int) -> tuple[int, int]:
        """Applica il clamp a una posizione giocatore (wrapper di ``MapBounds.clamp``).

        Esempio di uso in ``main.py``::

            p1_col, p1_row = WorldRulesSystem.clamp_player_pos(p1_col, p1_row)

        Args:
            col: Colonna da clampare.
            row: Riga da clampare.

        Returns:
            Coppia ``(col, row)`` garantita entro i limiti della mappa.
        """
        return MapBounds.clamp(col, row)

    def _on_player_moved(self, data: dict) -> None:
        """Controlla aggro e zone di pattuglia ad ogni movimento del giocatore.

        Traccia le posizioni di entrambi i giocatori. L'aggro viene controllato
        per ogni trigger attivo; la zona di pattuglia viene valutata rispetto
        alla reputazione corrente.

        Data keys:
            position (tuple): (col, row) del giocatore che si è mosso.
            player_id (str):  "p1"/"Rivet" o "p2"/"Echo".
            reps (dict):      Reputazioni correnti per fazione.
        """
        pos = data.get("position")
        if not pos:
            return

        player_pos = (pos[0], pos[1])
        player_id  = data.get("player_id", "p1")
        reps       = data.get("reps", {})

        # Aggiorna la posizione del giocatore che si è mosso
        if player_id in ("p1", "Rivet"):
            self._p1_pos = player_pos
        else:
            self._p2_pos = player_pos

        # Controlla tutti i trigger di aggro attivi
        other_pos = self._p2_pos if player_id in ("p1", "Rivet") else self._p1_pos
        for trigger in self._aggro_triggers:
            # Se il trigger attende che il player esca dal range (post-fuga),
            # riattivalo solo una volta che entrambi i giocatori sono fuori portata.
            if getattr(trigger, "wait_for_leave", False):
                in_range = trigger.check_aggro(player_pos, other_pos)
                if not in_range:
                    trigger.wait_for_leave = False  # ora può aggrare normalmente
                continue  # non aggrare ancora in ogni caso
            if trigger.check_aggro(player_pos, other_pos):
                trigger.is_active = False
                if self._bus:
                    self._bus.publish(EventType.START_ENCOUNTER, {
                        "trigger_pos": trigger.position,
                        "faction":     trigger.faction,
                        "enemy_type":  trigger.enemy_type,
                    })

        # Controlla le zone di pattuglia
        for zone in self._patrol_zones:
            if zone.contains(player_pos):
                rep = reps.get(zone.faction, 0)
                if zone.is_hostile_encounter(rep):
                    if self._bus:
                        self._bus.publish(EventType.START_ENCOUNTER, {
                            "zone":    zone.faction,
                            "hostile": True,
                        })

    def _on_enemy_killed(self, data: dict) -> None:
        """Registra la morte di un nemico e gestisce la probabilità di rianimazione.

        I nemici zombie non uccisi con headshot hanno il 30% di probabilità
        di rianmarsi parzialmente (30% degli HP massimi).

        Data keys:
            enemy (Enemy):    Il nemico sconfitto.
            headshot (bool):  Se è stato un colpo alla testa.
            faction (str):    Fazione del nemico.
        """
        import random
        enemy    = data.get("enemy")
        headshot = data.get("headshot", False)
        faction  = data.get("faction", "")

        if faction == "zombie" and not headshot and enemy is not None:
            if random.random() < 0.30:
                if self._bus:
                    self._bus.publish(EventType.ENEMY_REANIMATED, {
                        "enemy":      enemy,
                        "hp_restore": int(getattr(
                            getattr(enemy, "stats", None), "max_hp", 40
                        ) * 0.30),
                    })

    def _on_chemical_tick(self, data: dict) -> None:
        """Applica danno continuo ai giocatori in zona Chemical Leak.

        Se il giocatore non ha protezione adeguata, pubblica ``PLAYER_DAMAGED``
        per tutti i bersagli.

        Data keys:
            protected (bool): Se il giocatore ha protezione chimica.
            dps (int):        Danno per tick (default: ``CHEMICAL_DPS``).
        """
        protected = data.get("protected", False)
        dps       = data.get("dps", self.CHEMICAL_DPS)

        if not protected and self._bus:
            self._bus.publish(EventType.PLAYER_DAMAGED, {
                "amount": dps,
                "source": "chemical_leak",
                "target": "all",
            })
