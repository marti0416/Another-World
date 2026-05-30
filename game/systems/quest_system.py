"""
quest_system.py — Sistema di quest con trigger, obiettivi e handler (Observer GoF).

Struttura
---------
- Enum: ``QuestStatus``, ``QuestTriggerType``, ``ObjectiveType``.
- ``QuestTrigger``  : condizione che attiva una quest (INACTIVE → AVAILABLE).
- ``Objective``     : obiettivo singolo con avanzamento numerico e Prototype GoF.
- ``Quest``         : quest completa con trigger, obiettivi, ricompense e stato.
- Handler Observer  : un ConcreteObserver per ogni tipo di evento rilevante
                      (ZoneEntered, EnemyKilled, NpcSaved, RepChanged, ecc.).
- ``QuestSystem``   : ISystem che orchestra trigger, avanzamento e completamento.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.model.item import ICloneable
from game.events.isystem import ISystem



class QuestStatus(Enum):
    """Enum degli stati possibili di una quest."""
    INACTIVE   = "inactive"
    AVAILABLE  = "available"
    ACTIVE     = "active"
    COMPLETED  = "completed"
    FAILED     = "failed"


class QuestTriggerType(Enum):
    """Enum dei tipi di condizione che attivano una quest."""
    ZONE_ENTER      = auto()
    FLAG_SET        = auto()
    ENEMY_KILLED    = auto()
    NPC_SAVED       = auto()
    REP_THRESHOLD   = auto()
    MANUAL          = auto()
    ITEM_IN_INV     = auto()

class ObjectiveType(Enum):
    """Enum dei tipi di obiettivo di una quest."""
    REACH_ZONE      = auto()
    KILL_ENEMIES    = auto()
    COLLECT_ITEM    = auto()
    DELIVER_ITEM    = auto()
    ACTIVATE_FLAG   = auto()
    SURVIVE_BATTLE  = auto()
    TALK_TO_NPC     = auto()
    SAVE_NPC        = auto()
    CRAFT_ITEM      = auto()



@dataclass
class QuestTrigger:
    """Condizione che fa passare la quest da INACTIVE ad AVAILABLE."""
    trigger_type: QuestTriggerType
    zone_id:      str | None = None
    flag_key:     str | None = None
    enemy_type:   str | None = None
    npc_name:     str | None = None
    faction_id:   str | None = None
    rep_threshold: int = 0
    item_id:      str | None = None

@dataclass
class Objective(ICloneable):
    """
    Singolo obiettivo di una quest.
    progress e required definiscono l'avanzamento numerico.
    completed viene impostato a True quando progress >= required.
    """
    obj_id:       str
    description:  str
    obj_type:     ObjectiveType
    required:     int  = 1
    progress:     int  = 0
    completed:    bool = False
    zone_id:      str | None = None
    enemy_type:   str | None = None
    item_id:      str | None = None
    npc_name:     str | None = None
    flag_key:     str | None = None
    hidden:       bool = False

    def advance(self, amount: int = 1) -> bool:
        """Incrementa il progresso. Restituisce True se l'obiettivo è appena completato."""
        if self.completed:
            return False
        self.progress = min(self.required, self.progress + amount)
        if self.progress >= self.required:
            self.completed = True
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "obj_id": self.obj_id,
            "progress": self.progress,
            "completed": self.completed,
        }

    def restore_from_dict(self, d: dict) -> None:
        self.progress  = d.get("progress", 0)
        self.completed = d.get("completed", False)

    def clone(self) -> "Objective":
        """Prototype: copia profonda — preserva lo stato di avanzamento indipendente."""
        return copy.deepcopy(self)



@dataclass
class QuestDef(ICloneable):
    """
    Definizione statica di una quest. Registrata una sola volta a startup.
    Non viene mai modificata durante la partita.
    """
    quest_id:        str
    title:           str
    description:     str
    trigger:         QuestTrigger
    objectives:      list[Objective]
    rewards:         dict = field(default_factory=dict)
    fail_conditions: list[str] = field(default_factory=list)
    prerequisites:   list[str] = field(default_factory=list)
    auto_accept:     bool = False
    completion_flag: str | None = None

    def clone(self) -> "QuestDef":
        """Prototype: copia profonda — la lista objectives deve essere indipendente."""
        return copy.deepcopy(self)



class QuestState:
    """
    Stato in-partita di una singola quest.
    Viene creato dal QuestSystem quando la quest diventa AVAILABLE.
    """

    def __init__(self, quest_def: QuestDef) -> None:
        self._def    = quest_def
        self.status  = QuestStatus.INACTIVE
        self.objectives: list[Objective] = [obj.clone() for obj in quest_def.objectives]

    @property
    def quest_id(self) -> str:
        return self._def.quest_id

    @property
    def title(self) -> str:
        return self._def.title

    @property
    def all_objectives_done(self) -> bool:
        return all(o.completed for o in self.objectives)

    def get_objective(self, obj_id: str) -> Objective | None:
        return next((o for o in self.objectives if o.obj_id == obj_id), None)


    def to_dict(self) -> dict:
        return {
            "quest_id":   self.quest_id,
            "status":     self.status.value,
            "objectives": [o.to_dict() for o in self.objectives],
        }

    def restore_from_dict(self, d: dict) -> None:
        status_str = d.get("status", "inactive")
        try:
            self.status = QuestStatus(status_str)
        except ValueError:
            self.status = QuestStatus.INACTIVE
        obj_data = {o["obj_id"]: o for o in d.get("objectives", [])}
        for obj in self.objectives:
            if obj.obj_id in obj_data:
                obj.restore_from_dict(obj_data[obj.obj_id])



from abc import ABC, abstractmethod as _abstractmethod


class QuestEventHandler(ABC):
    """Template Method: handle() = _check_triggers() + _check_objectives()."""

    def handle(self, system: "QuestSystem", data: dict) -> None:
        self._check_triggers(system, data)
        self._check_objectives(system, data)

    @_abstractmethod
    def _check_triggers(self, system: "QuestSystem", data: dict) -> None:
        """Valuta se una quest INACTIVE deve diventare AVAILABLE."""
        ...

    @_abstractmethod
    def _check_objectives(self, system: "QuestSystem", data: dict) -> None:
        """Avanza gli obiettivi delle quest ACTIVE."""
        ...


    def _iter_inactive(self, system: "QuestSystem"):
        """Itera (quest_id, quest_def, state) per le quest INACTIVE."""
        for quest_id, quest_def in system._defs.items():
            state = system._states[quest_id]
            if state.status == QuestStatus.INACTIVE:
                yield quest_id, quest_def, state

    def _make_available_if_prereqs(self, system: "QuestSystem",
                                   quest_def: "QuestDef",
                                   state: "QuestState") -> None:
        if system._prerequisites_met(quest_def):
            system._make_available(state)

    def _advance_obj(self, system: "QuestSystem",
                     state: "QuestState", obj: "Objective") -> None:
        if obj.advance():
            system._notify_obj_completed(state, obj)
            system._check_completion(state)



class ZoneEnteredHandler(QuestEventHandler):
    """Handler Observer per l'evento ``ZONE_ENTERED``.

        Avanza gli obiettivi di tipo ``REACH_ZONE`` che corrispondono alla zona corrente.
    """
    def _check_triggers(self, system, data):
        zone_id = data.get("zone_id", "")
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.ZONE_ENTER
                    and quest_def.trigger.zone_id == zone_id):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        zone_id = data.get("zone_id", "")
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.REACH_ZONE
                        and obj.zone_id == zone_id):
                    self._advance_obj(system, state, obj)



_SKYSCRAPER_X0, _SKYSCRAPER_X1 = 53, 72
_SKYSCRAPER_Y0, _SKYSCRAPER_Y1 = 44, 69
_ZOMBIE_FAMILY = {"zombie", "infetto", "corazzato", "orda", "giant"}


def _resolve_current_zones(data: dict) -> set[str]:
    """Risolve le zone correnti dalla posizione del nemico/giocatori."""
    from game.controller.game_manager import GameManager
    gs = GameManager.get_instance()
    zones: set[str] = set()

    if "zone_id" in data:
        zones.add(data["zone_id"])

    target_pos = None
    if hasattr(gs, "current_battle_npc") and gs.current_battle_npc:
        target_pos = tuple(gs.current_battle_npc.get("pos", (0, 0)))

    positions = [target_pos] if target_pos else []
    if not target_pos:
        if hasattr(gs, "p1") and gs.p1: positions.append(tuple(gs.p1))
        if hasattr(gs, "p2") and gs.p2: positions.append(tuple(gs.p2))

    for pos in positions:
        px, py = pos[0], pos[1]
        if _SKYSCRAPER_X0 <= px <= _SKYSCRAPER_X1 and _SKYSCRAPER_Y0 <= py <= _SKYSCRAPER_Y1:
            zones.add("Grattacielo")
        try:
            from game.view.draw_utils import cur_district
            _, (_, dcode, _) = cur_district(pos)
            if dcode:
                zones.add(dcode)
        except Exception:
            pass

    try:
        if gs.flags.get("factory_inner_door_breached", False) and "F" in zones:
            zones.add("factory_building")
    except Exception:
        pass

    return zones


def _enemy_matches_objective(obj_enemy_type: str | None, killed_type: str) -> bool:
    if obj_enemy_type is None:
        return True
    if obj_enemy_type == killed_type:
        return True
    if obj_enemy_type == "zombie" and killed_type in _ZOMBIE_FAMILY:
        return True
    return False


class EnemyKilledHandler(QuestEventHandler):
    """Handler Observer per l'evento ``ENEMY_KILLED``.

        Avanza gli obiettivi di tipo ``KILL_ENEMIES`` che corrispondono al tipo di nemico.
    """
    def _check_triggers(self, system, data):
        enemy_type = data.get("enemy_type", "")
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.ENEMY_KILLED
                    and quest_def.trigger.enemy_type == enemy_type):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        enemy_type    = data.get("enemy_type", "")
        current_zones = _resolve_current_zones(data)
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.KILL_ENEMIES
                        and _enemy_matches_objective(obj.enemy_type, enemy_type)):
                    if obj.zone_id is not None and obj.zone_id not in current_zones:
                        continue
                    self._advance_obj(system, state, obj)



class NpcSavedHandler(QuestEventHandler):
    """Handler Observer per l'evento ``NPC_SAVED``.

        Avanza gli obiettivi di tipo ``SAVE_NPC`` che corrispondono all'NPC salvato.
    """
    def _check_triggers(self, system, data):
        npc_name = data.get("npc_name", "")
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.NPC_SAVED
                    and (quest_def.trigger.npc_name is None
                         or quest_def.trigger.npc_name == npc_name)):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        npc_name = data.get("npc_name", "")
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.SAVE_NPC
                        and (obj.npc_name is None or obj.npc_name == npc_name)):
                    self._advance_obj(system, state, obj)



class RepChangedHandler(QuestEventHandler):
    """Handler Observer per l'evento ``REPUTATION_CHANGED``.

        Verifica se la nuova reputazione soddisfa un trigger di tipo ``REP_THRESHOLD``.
    """
    def _check_triggers(self, system, data):
        faction_id = data.get("faction", "")
        from game.controller.game_manager import GameManager
        current_rep = GameManager.get_instance().reps.get(faction_id, 0)
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.REP_THRESHOLD
                    and quest_def.trigger.faction_id == faction_id
                    and current_rep >= quest_def.trigger.rep_threshold):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        pass



class ItemPickupHandler(QuestEventHandler):
    """Handler Observer per l'evento ``ITEM_PICKUP``.

        Avanza obiettivi ``COLLECT_ITEM`` e verifica trigger ``ITEM_IN_INV``.
    """
    def _check_triggers(self, system, data):
        item_id = data.get("item_id", "")
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.ITEM_IN_INV
                    and quest_def.trigger.item_id == item_id):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        item_id = data.get("item_id", "")
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.COLLECT_ITEM
                        and obj.item_id == item_id):
                    self._advance_obj(system, state, obj)



class DialogueEndedHandler(QuestEventHandler):
    """Handler Observer per l'evento ``DIALOGUE_ENDED``.

        Avanza obiettivi di tipo ``TALK_TO_NPC`` che corrispondono all'NPC dialogato.
    """
    def _check_triggers(self, system, data):
        pass

    def _check_objectives(self, system, data):
        npc_name = data.get("npc_name", "")
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.TALK_TO_NPC
                        and obj.npc_name == npc_name):
                    self._advance_obj(system, state, obj)



class FlagSetEventHandler(QuestEventHandler):
    """Handler Observer per l'evento ``FLAG_SET_EVENT``.

        Avanza obiettivi ``ACTIVATE_FLAG`` e attiva quest con trigger ``FLAG_SET``.
    """
    def _check_triggers(self, system, data):
        flag_key = data.get("key", "")
        flag_val = data.get("value", True)
        try:
            from game.controller.game_manager import GameManager
            gs = GameManager.get_instance()
            if not hasattr(gs, "flags"):
                gs.flags = {}
            gs.flags[flag_key] = flag_val
        except Exception:
            pass
        if flag_val is not True:
            return
        for _, quest_def, state in self._iter_inactive(system):
            if (quest_def.trigger.trigger_type == QuestTriggerType.FLAG_SET
                    and quest_def.trigger.flag_key == flag_key):
                self._make_available_if_prereqs(system, quest_def, state)

    def _check_objectives(self, system, data):
        flag_key = data.get("key", "")
        flag_val = data.get("value", True)
        if flag_val is not True:
            return
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.ACTIVATE_FLAG
                        and obj.flag_key == flag_key):
                    self._advance_obj(system, state, obj)



class ItemCraftedHandler(QuestEventHandler):
    """Handler Observer per l'evento ``ITEM_CRAFTED``.

        Avanza obiettivi di tipo ``CRAFT_ITEM`` che corrispondono all'oggetto craftato.
    """
    def _check_triggers(self, system, data):
        pass

    def _check_objectives(self, system, data):
        item   = data.get("item")
        weapon = data.get("weapon")
        if item:
            crafted_id = getattr(item, "item_id", None)
        elif weapon:
            crafted_id = getattr(weapon, "weapon_id",
                                  getattr(weapon, "weapon_type", None))
        else:
            crafted_id = None
        for state in system.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.CRAFT_ITEM
                        and (obj.item_id is None or obj.item_id == crafted_id)):
                    self._advance_obj(system, state, obj)



_QUEST_HANDLERS: dict = {
    EventType.ZONE_ENTERED:       ZoneEnteredHandler(),
    EventType.ENEMY_KILLED:       EnemyKilledHandler(),
    EventType.NPC_SAVED:          NpcSavedHandler(),
    EventType.REPUTATION_CHANGED: RepChangedHandler(),
    EventType.ITEM_PICKUP:        ItemPickupHandler(),
    EventType.DIALOGUE_ENDED:     DialogueEndedHandler(),
    EventType.FLAG_SET_EVENT:     FlagSetEventHandler(),
    EventType.ITEM_CRAFTED:       ItemCraftedHandler(),
}



class QuestSystem(ISystem):
    """
    ISystem orchestratore. Gestisce il ciclo di vita di tutte le quest.

    PATTERN: Template Method + Strategy sugli handler EventBus.
      Ogni tipo di evento (ZONE_ENTERED, ENEMY_KILLED, ecc.) è gestito da
      un QuestEventHandler concreto che implementa due hook:
        _check_triggers()  — valuta se una quest INACTIVE diventa AVAILABLE
        _check_objectives() — avanza gli obiettivi delle quest ACTIVE
      QuestSystem.initialize() registra tutti gli handler via _HANDLERS map:
      aggiungere un nuovo tipo di evento = 1 classe + 1 voce nella mappa,
      senza toccare QuestSystem.

    Flusso:
      1. register_quest(def) → aggiunge la definizione al registro
      2. EventBus pubblica un evento (ZONE_ENTERED, ENEMY_KILLED, ecc.)
      3. _check_triggers() valuta se una quest INACTIVE diventa AVAILABLE
      4. Se auto_accept → status = ACTIVE automaticamente
      5. Altrimenti: pubblica QUEST_AVAILABLE → HUDSystem mostra notifica
      6. Il giocatore accetta → accept_quest(quest_id) → status = ACTIVE
      7. _check_objectives() aggiorna il progresso ad ogni evento rilevante
      8. Se all_objectives_done → _complete_quest() → pubblica QUEST_COMPLETED
      9. Se fail_condition → _fail_quest() → pubblica QUEST_FAILED
    """

    def __init__(self) -> None:
        self._bus:     EventBus | None = None
        self._defs:    dict[str, QuestDef]   = {}
        self._states:  dict[str, QuestState] = {}
        self._subscribed: list[tuple] = []


    def initialize(self, bus: EventBus) -> None:
        self._bus = bus
        for event_type, handler in _QUEST_HANDLERS.items():
            cb = (lambda d, h=handler: h.handle(self, d))
            bus.subscribe(event_type, cb)
            self._subscribed.append((event_type, cb))

    def cleanup(self) -> None:
        if not self._bus:
            return
        for event_type, cb in self._subscribed:
            self._bus.unsubscribe(event_type, cb)
        self._subscribed.clear()


    def register_quest(self, quest_def: QuestDef) -> None:
        """Registra la definizione di una quest. Chiamato a startup."""
        self._defs[quest_def.quest_id] = quest_def
        state = QuestState(quest_def)
        self._states[quest_def.quest_id] = state


    def activate_quest(self, quest_id: str) -> None:
        """Attivazione manuale (trigger MANUAL). Usato da dialoghi o cutscene."""
        state = self._states.get(quest_id)
        if state and state.status == QuestStatus.INACTIVE:
            self._make_available(state)

    def accept_quest(self, quest_id: str) -> bool:
        """Il giocatore accetta una quest AVAILABLE. Chiamato dall'HUD."""
        state = self._states.get(quest_id)
        if state and state.status == QuestStatus.AVAILABLE:
            state.status = QuestStatus.ACTIVE
            if self._bus:
                self._bus.publish(EventType.QUEST_ACCEPTED, {"quest_id": quest_id})
            return True
        return False

    def get_active_quests(self) -> list[QuestState]:
        return [s for s in self._states.values() if s.status == QuestStatus.ACTIVE]

    def get_available_quests(self) -> list[QuestState]:
        return [s for s in self._states.values() if s.status == QuestStatus.AVAILABLE]

    def is_completed(self, quest_id: str) -> bool:
        state = self._states.get(quest_id)
        return state is not None and state.status == QuestStatus.COMPLETED

    def advance_objective(self, quest_id: str, obj_id: str, amount: int = 1) -> None:
        """
        Avanza manualmente un obiettivo. Usato dall'explore_screen
        per l'effetto 'set_flag' dei dialoghi che implica un obiettivo quest.
        """
        state = self._states.get(quest_id)
        if not state or state.status != QuestStatus.ACTIVE:
            return
        obj = state.get_objective(obj_id)
        if obj and obj.advance(amount):
            self._check_completion(state)

    def notify_flag_set(self, flag_key: str, value: Any) -> None:
        """
        Chiamato da ExploreScreen._apply_dialogue_effects() ogni volta che
        un effetto 'set_flag' viene applicato. Controlla trigger e obiettivi.
        """
        if value is not True:
            return
        for quest_id, quest_def in self._defs.items():
            state = self._states[quest_id]
            if (state.status == QuestStatus.INACTIVE
                    and quest_def.trigger.trigger_type == QuestTriggerType.FLAG_SET
                    and quest_def.trigger.flag_key == flag_key
                    and self._prerequisites_met(quest_def)):
                self._make_available(state)
        for state in self.get_active_quests():
            for obj in state.objectives:
                if (not obj.completed
                        and obj.obj_type == ObjectiveType.ACTIVATE_FLAG
                        and obj.flag_key == flag_key):
                    if obj.advance():
                        self._notify_obj_completed(state, obj)
                        self._check_completion(state)

    def _notify_obj_completed(self, state: QuestState, obj: Objective):
        """Invia un evento quando un singolo obiettivo è terminato."""
        if self._bus:
            self._bus.publish(EventType.OBJECTIVE_COMPLETED, {
                "quest_id": state.quest_id,
                "obj_id": obj.obj_id,
                "description": obj.description
            })



    def _prerequisites_met(self, quest_def: QuestDef) -> bool:
        return all(self.is_completed(pid) for pid in quest_def.prerequisites)

    def _make_available(self, state: QuestState) -> None:
        state.status = QuestStatus.AVAILABLE
        if self._bus:
            self._bus.publish(EventType.QUEST_AVAILABLE, {
                "quest_id": state.quest_id,
                "title":    state.title,
            })
        quest_def = self._defs[state.quest_id]
        if quest_def.auto_accept:
            self.accept_quest(state.quest_id)

    def _check_completion(self, state: QuestState) -> None:
        if state.all_objectives_done:
            self._complete_quest(state)

    def _complete_quest(self, state: QuestState) -> None:
        state.status = QuestStatus.COMPLETED
        quest_def = self._defs[state.quest_id]
        self._grant_rewards(quest_def.rewards)

        if quest_def.completion_flag:
            from game.controller.game_manager import GameManager
            gs = GameManager.get_instance()
            if not hasattr(gs, "flags"):
                gs.flags = {}
            gs.flags[quest_def.completion_flag] = True

            self.notify_flag_set(quest_def.completion_flag, True)

        if self._bus:
            self._bus.publish(EventType.QUEST_COMPLETED, {
                "quest_id": state.quest_id,
                "title":    state.title,
                "rewards":  quest_def.rewards,
            })


    def _fail_quest(self, quest_id: str, reason: str = "") -> None:
        state = self._states.get(quest_id)
        if state and state.status == QuestStatus.ACTIVE:
            state.status = QuestStatus.FAILED
            if self._bus:
                self._bus.publish(EventType.QUEST_FAILED, {
                    "quest_id": quest_id,
                    "reason":   reason,
                })

    def _grant_rewards(self, rewards: dict) -> None:
        """Distribuisce le ricompense di una quest completata."""
        if not rewards:
            return
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()

        xp = rewards.get("xp", 0)
        if xp and gs.Rivet and gs.Echo:
            gs.Rivet.stats.gain_xp(xp)
            gs.Echo.stats.gain_xp(xp)
            gs.log(gs.wlog, f"Quest completata! +{xp} XP a entrambi")

        tech = rewards.get("tech_points", {})
        if isinstance(tech, int):
            tech = {"Rivet": tech, "Echo": tech}
        for char_name, pts in tech.items():
            char = gs.Rivet if char_name == "Rivet" else gs.Echo
            if char and pts:
                char.stats.gain_tech_points(pts)
                gs.log(gs.wlog, f"[{char_name}] +{pts} Tech Points")

        rep = rewards.get("reputation", {})
        for faction_id, delta in rep.items():
            gs.modify_rep(faction_id, delta)

        ethics_delta = rewards.get("ethics", 0)
        if ethics_delta:
            gs.modify_ethics(ethics_delta)

        items = rewards.get("items", {})
        for item_id, qty in items.items():
            if gs.Rivet:
                from game.model.item_registry import get_item_proto
                for _ in range(qty):
                    item_proto = get_item_proto(item_id)
                    if item_proto:
                        gs.Rivet.inventory.add_item(item_proto.clone())
                gs.log(gs.wlog, f"Ottenuto: {item_id} ×{qty}")

        unlock_flags = rewards.get("unlock_flags", [])
        if not hasattr(gs, "flags"):
            gs.flags = {}
        for flag_key in unlock_flags:
            gs.flags[flag_key] = True

            self.notify_flag_set(flag_key, True)


    def to_dict(self) -> dict:
        """Esporta lo stato corrente di tutte le quest per il Memento."""
        return {
            qid: state.to_dict()
            for qid, state in self._states.items()
        }

    def restore_from_dict(self, data: dict) -> None:
        """Ripristina lo stato delle quest da un Memento."""
        for quest_id, state_data in data.items():
            state = self._states.get(quest_id)
            if state:
                state.restore_from_dict(state_data)


def _build_all_quests() -> list[QuestDef]:
    """Costruisce e restituisce tutte le QuestDef del gioco (Allineate ai Dialoghi)."""

    quests: list[QuestDef] = []


    quests.append(QuestDef(
        quest_id    = "Q01_grattacielo",
        title       = "Dentro il Grattacielo",
        description = (
            "Trovate Rael nei vicoli — conosce queste strade meglio di chiunque altro. "
            "Il Grattacielo in città nasconde una cassaforte al piano alto."
            "Dentro c'è un'arma pesante che potrebbe cambiare le sorti della vostra sopravvivenza. "
            "Eliminate gli infetti, hackerate il terminale con Echo e recuperate l'arma. "
            "Poi consegnatela a Rael: ha bisogno di voi quanto voi di lui."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.MANUAL),
        auto_accept = True,
        objectives  = [
            Objective("Q01_o0", "Parla con Rael nei vicoli", ObjectiveType.TALK_TO_NPC, npc_name="Rael"),
            Objective("Q01_o1", "Eliminare gli infetti nel Grattacielo", ObjectiveType.KILL_ENEMIES, required=2, enemy_type="zombie", zone_id="Grattacielo"),
            Objective("Q01_o2", "Echo hacera il terminale — la porta si apre", ObjectiveType.ACTIVATE_FLAG, flag_key="skyscraper_terminal_hacked"),
            Objective("Q01_o3", "Rivet sfonda la cassaforte", ObjectiveType.ACTIVATE_FLAG, flag_key="safe_breached"),
            Objective("Q01_o4", "Consegnare l'arma a Rael", ObjectiveType.ACTIVATE_FLAG, flag_key="rael_paid"),
        ],
        rewards = {"xp": 50, "reputation": {"erranti": 10}},
        completion_flag = "Q01_done",
    ))

    quests.append(QuestDef(
        quest_id    = "Q02_centrale",
        title       = "Riaccendere la Centrale e il Radar",
        description = (
            "Recuperate una mina all'Aeroporto Militare (attenzione alle esplosioni!). "
            "Rivet la userà per far saltare il portello blindato della Centrale Elettrica. "
            "Una volta dentro, Echo riattiverà i circuiti interagendo con il pannello principale. "
            "Infine, raggiungete la Torre Radar: Echo dovrà hackerarla per localizzare i Giganti di Carne."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="Q01_done"),
        prerequisites = ["Q01_grattacielo"],
        auto_accept = True,
        objectives  = [
            Objective("Q02_o1", "Recuperare la mina all'Aeroporto", ObjectiveType.COLLECT_ITEM, item_id="landmine_01", required=1),
            Objective("Q02_o2", "Rivet fa saltare il portello della Centrale", ObjectiveType.ACTIVATE_FLAG, flag_key="power_plant_door_blown"),
            Objective("Q02_o3", "Echo attiva il pannello di controllo", ObjectiveType.ACTIVATE_FLAG, flag_key="power_panel_activated"),
            Objective("Q02_o4", "Echo hackera la Torre Radar", ObjectiveType.ACTIVATE_FLAG, flag_key="radar_tower_hacked"),
        ],
        rewards = {"xp": 60, "reputation": {"dannati": -5}, "unlock_flags": ["radar_station_active", "giants_visible_on_map"]},
        completion_flag = "Q02_done",
    ))

    quests.append(QuestDef(
        quest_id    = "Q03_fabbrica",
        title       = "La Fabbrica Chimica",
        description = (
            "La corrente ripristinata ha riattivato i meccanismi della Fabbrica Chimica. "
            "Entrate, eliminate gli infetti. Rivet sfonda la porta blindata interna. "
            "Echo hacera il terminale di laboratorio e troverà la Piranha Solution. "
            "Poi dovrete scegliere: usarla per purificare il mondo, o fuggire."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="Q02_done"),
        prerequisites = ["Q02_centrale"],
        auto_accept = True,
        objectives  = [
            Objective("Q03_o1", "Rivet sfonda la porta interna della Fabbrica",       ObjectiveType.ACTIVATE_FLAG, flag_key="factory_inner_door_breached"),
            Objective("Q03_o2", "Eliminare gli infetti nell'edificio della Fabbrica",   ObjectiveType.KILL_ENEMIES,  required=5, enemy_type="zombie", zone_id="factory_building"),
            Objective("Q03_o3", "Echo hacera il terminale di laboratorio",              ObjectiveType.ACTIVATE_FLAG, flag_key="factory_terminal_hacked"),
            Objective("Q03_o4", "Prendere la decisione finale",                         ObjectiveType.ACTIVATE_FLAG, flag_key="finale_choice_made", hidden=True),
        ],
        rewards = {"xp": 70},
        completion_flag = "Q03_done",
    ))


    quests.append(QuestDef(
        quest_id      = "Q04_giant_hunt",
        title         = "Caccia al Gigante",
        description   = (
            "Il radar è operativo e ha localizzato un Gigante di Carne nelle vicinanze. "
            "Abbatterlo libera le risorse dell'area e impressiona i sopravvissuti."
        ),
        trigger       = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="Q02_done"),
        prerequisites = ["Q02_centrale"],
        auto_accept   = True,
        objectives    = [
            Objective("Q04_o1", "Eliminare il Gigante di Carne", ObjectiveType.KILL_ENEMIES, required=1, enemy_type="giant"),
            Objective("Q04_o2", "Ripulire la scorta zombie nell'area", ObjectiveType.KILL_ENEMIES, required=4, enemy_type="zombie"),
        ],
        rewards         = {"xp": 100},
        completion_flag = "Q04_done",
    ))


    quests.append(QuestDef(
        quest_id      = "Q05_craft_explosive",
        title         = "Armare la Resistenza",
        description   = (
            "Rivet ha appena padroneggiato l'arte degli esplosivi. "
            "È il momento giusto per mettere alla prova le sue nuove competenze: "
            "costruire un Cocktail Molotov con i materiali di recupero. "
            "Potrebbe salvarvi la vita."
        ),

        trigger       = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="rivet_esperto_esplosivi_unlocked"),
        auto_accept   = True,
        objectives    = [
            Objective(
                "Q05_CE_o1",
                "Craftare un Cocktail Molotov (Rivet)",
                ObjectiveType.CRAFT_ITEM,
                item_id = "molotov_cocktail",
            ),
        ],
        rewards         = {"xp": 50},
        completion_flag = "Q05_craft_explosive_done",
    ))



    quests.append(QuestDef(
        quest_id    = "Q_NPC_Scar_Prag",
        title       = "Il Pedaggio di Scar — Scambio Merci",
        description = "Avete stretto un patto commerciale con Scar. Portategli 20 Razioni e 10 Scatole di Cibo per onorare l'accordo.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="scar_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_scar", "Consegna 20 Razioni e 10 Scatole a Scar", ObjectiveType.ACTIVATE_FLAG, flag_key="scar_paid")],
        rewards     = {"xp": 25, "reputation": {"razziatori": +5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Scar_Diplo",
        title       = "Il Pedaggio di Scar — Via Diplomatica",
        description = "Siete riusciti a ragionare con Scar. Per mantenere la tregua, consegnate le 20 Razioni e 10 Scatole pattuite.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="scar_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_scar", "Rispetta l'accordo con Scar (20 Razioni, 10 Scatole)", ObjectiveType.ACTIVATE_FLAG, flag_key="scar_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"razziatori": +5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Scar_Aggro",
        title       = "Il Pedaggio di Scar — Pugno di Ferro",
        description = "Avete intimidito Scar, ma la tensione è alta. Pagate il tributo (20 Razioni e 10 Scatole) per evitare che i Razziatori vi diano la caccia.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="scar_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_scar", "Paga Scar per calmare le acque (20 Razioni, 10 Scatole)", ObjectiveType.ACTIVATE_FLAG, flag_key="scar_paid")],
        rewards     = {"xp": 25, "combat_risk_reduction": 0.10, "reputation": {"razziatori": +2}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Scar_Emp",
        title       = "Il Pedaggio di Scar — Un Gesto Umano",
        description = "Avete visto l'uomo dietro la maschera del Razziatore. Aiutate la sua gente portando loro 20 Razioni e 10 Scatole di Cibo.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="scar_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_scar", "Dona 20 Razioni e 10 Scatole a Scar", ObjectiveType.ACTIVATE_FLAG, flag_key="scar_paid")],
        rewards     = {"xp": 25, "ethics": 2, "reputation": {"razziatori": 5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vex_Prag",
        title       = "Il Mirino di Vex — Scambio",
        description = "Vex vi tiene sotto tiro, ma chiuderà un occhio in cambio di cure. Portategli 1 Kit Avanzato, 3 Bende e 5 Antibiotici.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vex_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vex", "Consegna Kit Avanzato, Bende e Antibiotici", ObjectiveType.ACTIVATE_FLAG, flag_key="vex_paid")],
        rewards     = {"xp": 25, "reputation": {"razziatori": +2}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vex_Diplo",
        title       = "Il Mirino di Vex — Negoziazione a distanza",
        description = "Avete convinto Vex a non sparare offrendogli assistenza. Consegnate 1 Kit Avanzato, 3 Bende e 5 Antibiotici per mantenere la tregua.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vex_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vex", "Consegna Kit Avanzato, Bende e Antibiotici", ObjectiveType.ACTIVATE_FLAG, flag_key="vex_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"razziatori": +5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vex_Aggro",
        title       = "Il Mirino di Vex — Stallo alla Messicana",
        description = "Avete minacciato Vex, ma lui ha ancora il dito sul grilletto. Portategli le cure (1 Kit Avanzato, 3 Bende e 5 Antibiotici) per evitare uno scontro a fuoco.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vex_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vex", "Consegna Kit Avanzato, Bende e Antibiotici", ObjectiveType.ACTIVATE_FLAG, flag_key="vex_paid")],
        rewards     = {"xp": 25, "reputation": {"razziatori": +2}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vex_Emp",
        title       = "Il Mirino di Vex — Compassione per un Cecchino",
        description = "Avete capito che Vex è solo spaventato. Aiutatelo portandogli 1 Kit Avanzato, 3 Bende e 5 Antibiotici per salvarsi.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vex_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vex", "Dona Kit Avanzato, Bende e Antibiotici", ObjectiveType.ACTIVATE_FLAG, flag_key="vex_paid")],
        rewards     = {"xp": 25, "ethics": 2, "reputation": {"razziatori": +5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Marco_Prag",
        title       = "Il Blocco di Marco — Libero Scambio",
        description = "Marco sorveglia l'avamposto dei Solidali. Consegnate 20 Alluminio, 15 Rottami e 10 Kevlar per ottenere il transito.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="marco_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_marco", "Consegna Alluminio, Rottami e Kevlar", ObjectiveType.ACTIVATE_FLAG, flag_key="marco_paid")],
        rewards     = {"xp": 25, "reputation": {"solidali": 10}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Marco_Diplo",
        title       = "Il Blocco di Marco — Fiducia Reciproca",
        description = "Vi siete presentati come alleati. Marco ha bisogno di 20 Alluminio, 15 Rottami e 10 Kevlar per le difese.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="marco_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_marco", "Porta Alluminio, Rottami e Kevlar", ObjectiveType.ACTIVATE_FLAG, flag_key="marco_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"solidali": 5}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Marco_Aggro",
        title       = "Il Blocco di Marco — Tensione all'Avamposto",
        description = "Siete passati con le minacce. Marco esige 20 Alluminio, 15 Rottami e 10 Kevlar per non allertare i cecchini.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="marco_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_marco", "Paga Marco con Alluminio, Rottami e Kevlar", ObjectiveType.ACTIVATE_FLAG, flag_key="marco_paid")],
        rewards     = {"xp": 25, "reputation": {"solidali": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Marco_Emp",
        title       = "Il Blocco di Marco — Solidarietà",
        description = "Avete compreso le difficoltà dei Solidali. Aiutate l'avamposto fornendo 20 Alluminio, 15 Rottami e 10 Kevlar.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="marco_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_marco", "Dona Alluminio, Rottami e Kevlar all'avamposto", ObjectiveType.ACTIVATE_FLAG, flag_key="marco_paid")],
        rewards     = {"xp": 25, "ethics": 2, "reputation": {"solidali": 5}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vera_Prag",
        title       = "La Richiesta di Vera — Baratto Medico",
        description = "Vera ha bisogno di materiali. Venderete 3 Bende e 2 Antibiotici al prezzo di mercato.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vera_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vera", "Consegna 3 Bende e 2 Antibiotici a Vera", ObjectiveType.ACTIVATE_FLAG, flag_key="vera_paid")],
        rewards     = {"xp": 25, "reputation": {"solidali": 5}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vera_Diplo",
        title       = "La Richiesta di Vera — Collaborazione Sanitaria",
        description = "Avete stretto un accordo formale per fornire a Vera 3 Bende e 2 Antibiotici necessari per la clinica.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vera_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vera", "Porta 3 Bende e 2 Antibiotici in infermeria", ObjectiveType.ACTIVATE_FLAG, flag_key="vera_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"solidali": 5}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vera_Aggro",
        title       = "La Richiesta di Vera — Estorsione Medica",
        description = "Avete intimidito Vera, ma dovrete comunque fornirle 3 Bende e 2 Antibiotici se volete le sue cure.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vera_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vera", "Consegna 3 Bende e 2 Antibiotici", ObjectiveType.ACTIVATE_FLAG, flag_key="vera_paid")],
        rewards     = {"xp": 25, "reputation": {"solidali": 1}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Vera_Emp",
        title       = "La Richiesta di Vera — Vite da Salvare",
        description = "Siete rimasti toccati dalla dedizione di Vera. Trovate 3 Bende e 2 Antibiotici per salvare i feriti.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="vera_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_vera", "Dona 3 Bende e 2 Antibiotici a Vera", ObjectiveType.ACTIVATE_FLAG, flag_key="vera_paid")],
        rewards     = {"xp": 25, "ethics": 3, "reputation": {"solidali": 10}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Griss_Prag",
        title       = "Il Territorio di Griss — Dazio",
        description = "Griss richiede 2 Cocktail Molotov e 1 Soluzione Piranha per lasciarvi vagare nel territorio dei Dannati.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="griss_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_griss", "Consegna 2 Molotov e 1 Piranha a Griss", ObjectiveType.ACTIVATE_FLAG, flag_key="griss_paid")],
        rewards     = {"xp": 25, "reputation": {"dannati": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Griss_Diplo",
        title       = "Il Territorio di Griss — Rispetto Formale",
        description = "Avete dimostrato che la diplomazia funziona. Portategli 2 Molotov e 1 Piranha per formalizzare l'accordo.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="griss_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_griss", "Rispetta l'accordo (2 Molotov, 1 Piranha)", ObjectiveType.ACTIVATE_FLAG, flag_key="griss_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"dannati": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Griss_Aggro",
        title       = "Il Territorio di Griss — Legge del Più Forte",
        description = "Vi lascerà in pace solo se pagherete un tributo di 2 Molotov e 1 Soluzione Piranha.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="griss_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_griss", "Consegna 2 Molotov e 1 Piranha a Griss", ObjectiveType.ACTIVATE_FLAG, flag_key="griss_paid")],
        rewards     = {"xp": 25, "reputation": {"dannati": 1}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Griss_Emp",
        title       = "Il Territorio di Griss — Pietà Nascosta",
        description = "Avete visto oltre la crudeltà dei Dannati. Consegnate 2 Molotov e 1 Soluzione Piranha come gesto di buona volontà.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="griss_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_griss", "Dona 2 Molotov e 1 Piranha a Griss", ObjectiveType.ACTIVATE_FLAG, flag_key="griss_paid")],
        rewards     = {"xp": 25, "ethics": 2, "reputation": {"dannati": 1}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Tomas_Prag",
        title       = "Il Rancore di Tomas — Scambio Freddo",
        description = "Tomas vi osserva con sospetto. Portategli 30 Munizioni e 1 Esplosivo da Combattimento per comprare il suo silenzio.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="tomas_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_tomas", "Consegna 30 Munizioni e 1 Esplosivo", ObjectiveType.ACTIVATE_FLAG, flag_key="tomas_paid")],
        rewards     = {"xp": 25, "reputation": {"dannati": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Tomas_Diplo",
        title       = "Il Rancore di Tomas — Tregua Armata",
        description = "Siete riusciti a mantenere i nervi saldi. Consegnate 30 Munizioni e 1 Esplosivo per siglare la tregua.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="tomas_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_tomas", "Rispetta la tregua (30 Munizioni, 1 Esplosivo)", ObjectiveType.ACTIVATE_FLAG, flag_key="tomas_paid")],
        rewards     = {"xp": 25, "ethics": 1, "reputation": {"dannati": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Tomas_Aggro",
        title       = "Il Rancore di Tomas — Aggressione Sventata",
        description = "Lo avete minacciato apertamente. Pagate 30 Munizioni e 1 Esplosivo per evitare ritorsioni.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="tomas_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_tomas", "Paga per evitare agguati (30 Munizioni, 1 Esplosivo)", ObjectiveType.ACTIVATE_FLAG, flag_key="tomas_paid")],
        rewards     = {"xp": 25, "reputation": {"dannati": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Tomas_Emp",
        title       = "Il Rancore di Tomas — Un'Anima Sepolta",
        description = "Avete toccato un tasto dolente. Dimostrategli che l'umanità esiste portandogli 30 Munizioni e 1 Esplosivo.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="tomas_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_tomas", "Dona 30 Munizioni e 1 Esplosivo a Tomas", ObjectiveType.ACTIVATE_FLAG, flag_key="tomas_paid")],
        rewards     = {"xp": 25, "ethics": 3, "reputation": {"dannati": 2}},
    ))


    quests.append(QuestDef(
        quest_id    = "Q_NPC_Sybil_Prag",
        title       = "I Segreti di Sybil — Dati per Dati",
        description = "Sybil vende informazioni preziose. Consegnate 3 Componenti, 1 Chip Dati e 1 Badge per accedere.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="sybil_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_sybil", "Consegna 3 Componenti, 1 Chip e 1 Badge", ObjectiveType.ACTIVATE_FLAG, flag_key="sybil_paid")],
        rewards     = {"xp": 25, "reputation": {"erranti": 5}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Sybil_Diplo",
        title       = "I Segreti di Sybil — Rete di Contatti",
        description = "Vi siete proposti come collaboratori. Fornite a Sybil 3 Componenti, 1 Chip e 1 Badge per stabilizzare la rete.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="sybil_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_sybil", "Collabora (3 Componenti, 1 Chip, 1 Badge)", ObjectiveType.ACTIVATE_FLAG, flag_key="sybil_paid")],
        rewards     = {"xp": 25, "reputation": {"erranti": 5}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Sybil_Aggro",
        title       = "I Segreti di Sybil — Estrazione Forzata",
        description = "Avete forzato la mano all'informatrice. Consegnatele 3 Componenti, 1 Chip e 1 Badge o bloccherà le comunicazioni.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="sybil_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_sybil", "Consegna Componenti, Chip e Badge", ObjectiveType.ACTIVATE_FLAG, flag_key="sybil_paid")],
        rewards     = {"xp": 25, "reputation": {"erranti": 2}},
    ))
    quests.append(QuestDef(
        quest_id    = "Q_NPC_Sybil_Emp",
        title       = "I Segreti di Sybil — Oltre lo Schermo",
        description = "Avete capito quanto sia isolata Sybil. Portatele 3 Componenti, 1 Chip e 1 Badge per alleviare il suo carico.",
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="sybil_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_sybil", "Aiuta Sybil (3 Componenti, 1 Chip, 1 Badge)", ObjectiveType.ACTIVATE_FLAG, flag_key="sybil_paid")],
        rewards     = {"xp": 25, "reputation": {"erranti": 8}},
    ))


    quests.append(QuestDef(
        quest_id    = "Q_NPC_Rael_Prag",
        title       = "Il Patto con Rael — Affare Freddo",
        description = (
            "Avete stretto un patto commerciale con Rael. Vi fornirà una rotta sicura "
            "attraverso il settore in cambio del fucile pesante. Onorate l'accordo."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="rael_prag_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_rael_prag", "Consegna il fucile pesante a Rael", ObjectiveType.ACTIVATE_FLAG, flag_key="rael_paid")],
        rewards     = {"xp": 30, "reputation": {"erranti": 8}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Rael_Diplo",
        title       = "Il Patto con Rael — Via Diplomatica",
        description = (
            "Vi siete presentati come alleati e Rael vi ha dato fiducia. "
            "Portateli il fucile pesante per sbloccare la rotta sicura promessa."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="rael_diplo_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_rael_diplo", "Porta il fucile pesante a Rael", ObjectiveType.ACTIVATE_FLAG, flag_key="rael_paid")],
        rewards     = {"xp": 30, "ethics": 1, "reputation": {"indipendenti": 3}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Rael_Aggro",
        title       = "Il Patto con Rael — Pugno di Ferro",
        description = (
            "Lo avete intimidito, ma Rael ha comunque bisogno del fucile pesante "
            "per fidarsi di voi. La tensione è alta: fate in fretta."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="rael_aggro_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_rael_aggro", "Consegna il fucile pesante a Rael", ObjectiveType.ACTIVATE_FLAG, flag_key="rael_paid")],
        rewards     = {"xp": 15, "reputation": {"erranti": 8}},
    ))

    quests.append(QuestDef(
        quest_id    = "Q_NPC_Rael_Emp",
        title       = "Il Patto con Rael — Un Gesto di Umanità",
        description = (
            "Avete visto la paura nell'anima di Rael. Gli avete promesso il fucile "
            "non solo come pagamento, ma come atto di protezione. "
            "Mantenetela, quella promessa."
        ),
        trigger     = QuestTrigger(trigger_type=QuestTriggerType.FLAG_SET, flag_key="rael_emp_quest_active"),
        auto_accept = True,
        objectives  = [Objective("obj_rael_emp", "Porta il fucile pesante a Rael", ObjectiveType.ACTIVATE_FLAG, flag_key="rael_paid")],
        rewards     = {"xp": 25, "ethics": 2, "reputation": {"erranti": 8}},
    ))

    return quests



def register_all_quests(quest_sys: QuestSystem) -> None:
    """
    Registra tutte le QuestDef nel QuestSystem.
    Chiamare dopo aver registrato il sistema:

        quest = QuestSystem()
        gm.register_system(quest)
        register_all_quests(quest)
    """
    for quest_def in _build_all_quests():
        quest_sys.register_quest(quest_def)