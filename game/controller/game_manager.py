"""
game_manager.py — GameManager singleton e SaveManager.

Il ``GameManager`` è il singleton centrale del gioco: tiene lo stato globale
(personaggi, posizioni, fazioni, flag di trama, etica, log), registra i sistemi
(ISystem) e orchestra la transizione tra le screen.

Il ``SaveManager`` gestisce la serializzazione dello stato su file JSON
(3 slot di salvataggio) e il ripristino dallo stato salvato.
"""

from __future__ import annotations
from game.audio.audio_manager import AudioManager

import sys
import os
import json
from datetime import datetime
from game.events.event_bus import EventBus
from game.paths import asset, asset_path
from game.events.event_types import EventType

from game.model.character_builder import CharacterDirector, RivetBuilder, EchoBuilder
from game.model.enemy import EnemyFactory
from game.model.faction_factory import FactionAssembler
from game.model.faction_system import ReputationSystem, FactionID
from game.model.item import Item, ItemType, Inventory
from game.model.item_registry import register_default_items
from game.model.weapon_system import WeaponRegistry

from game.systems.battle_system import BattleSystem
from game.systems.crafting_system import CraftingSystem
from game.systems.hacking_system import HackingSystem
from game.systems.hud_system import HUDSystem
from game.systems.loot_system import LootSystem
from game.systems.movement_system import MovementSystem, KeyBinding
from game.systems.party_system import PartySystem
from game.systems.quest_system import QuestSystem, register_all_quests
from game.systems.save_ui import SaveMenuSystem
from game.systems.social_system import CoupleEthicsSystem, PreDialogueSystem
from game.systems.world_rules import WorldRulesSystem

from game.dialogue.dialogue import DialogueManager

from game.view.effects import EffectManager
from game.view.map_loader import TiledMap as JsonTiledMap
from game.view.renderer import make_Rivet_sprite, make_Echo_sprite

from game.world.world_data import W, H, FPS, GREEN, BG, NPCS

from game.controller.event_chain import build_event_chain

class GameMemento:
    """Snapshot immutabile dell'intero stato di partita."""

    def __init__(self, state_snapshot: dict, location: str = "") -> None:
        self._state_snapshot = state_snapshot
        self._timestamp      = datetime.now()
        self._location       = location
        self._sound_played = False

    def get_state_snapshot(self) -> dict:
        return dict(self._state_snapshot)

    def get_timestamp(self) -> datetime:
        return self._timestamp

    def get_location(self) -> str:
        return self._location

    def to_dict(self) -> dict:
        """Serializza il memento in un dizionario JSON-friendly."""
        return {
            "snapshot": self._state_snapshot,
            "timestamp": self._timestamp.isoformat(),
            "location": self._location
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameMemento":
        """Ricrea un memento partendo da un dizionario JSON."""
        snap = data.get("snapshot", {})
        loc = data.get("location", "")
        ts_str = data.get("timestamp")

        m = cls(snap, loc)
        if ts_str:
            try:
                m._timestamp = datetime.fromisoformat(ts_str)
            except ValueError:
                m._timestamp = datetime.now()
        return m


class SaveManager:
    SAVE_FILE = "savegame.json"

    def __init__(self) -> None:
        self._slots: dict[int, GameMemento] = {}
        self._load_from_disk()

    def _save_to_disk(self) -> None:
        """Salva fisicamente il dizionario _slots sul file JSON."""
        data = {}
        for slot_id, memento in self._slots.items():
            data[str(slot_id)] = memento.to_dict()

        try:
            with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Errore durante la scrittura del salvataggio: {e}")

    def _load_from_disk(self) -> None:
        """Legge il file JSON (se esiste) e popola il dizionario _slots."""
        if not os.path.exists(self.SAVE_FILE):
            return

        try:
            with open(self.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            for slot_str, memento_data in data.items():
                slot_id = int(slot_str)
                self._slots[slot_id] = GameMemento.from_dict(memento_data)
        except Exception as e:
            print(f"Errore durante la lettura del salvataggio: {e}")

    def save_game(self, originator: "GameManager", slot_id: int) -> GameMemento:
        m = originator.create_memento()
        self._slots[slot_id] = m
        self._save_to_disk()
        return m

    def load_game(self, originator: "GameManager", slot_id: int) -> bool:
        if slot_id not in self._slots:
            return False
        originator.restore_from_memento(self._slots[slot_id])
        return True

    def has_slot(self, slot_id: int) -> bool:
        return slot_id in self._slots

    def delete_save(self, slot_id: int) -> bool:
        if slot_id in self._slots:
            del self._slots[slot_id]
            self._save_to_disk()
            return True
        return False

    def get_slot_metadata(self, slot_id: int) -> dict:
        if slot_id in self._slots:
            m = self._slots[slot_id]
            return {
                "is_empty": False,
                "timestamp": m.get_timestamp(),
                "location": m.get_location()
            }
        return {
            "is_empty": True,
            "timestamp": None,
            "location": ""
        }

    def get_first_empty_slot(self, max_slots: int = 3) -> int:
        for i in range(1, max_slots + 1):
            if i not in self._slots:
                return i
        return 1

    def has_any_saves(self) -> bool:
        return len(self._slots) > 0



class GameSystemBuilder:
    """Builder fluente per la lista di ISystem del GameManager.

    Uso tipico:
        systems, refs = (GameSystemBuilder(bus)
            .add(PartySystem(),    ref="party_sys")
            .add(CraftingSystem(), ref="craft_sys")
            .add(BattleSystem(),   ref="battle_sys")
            .build())
        self._systems   = systems
        self.craft_sys  = refs["craft_sys"]

    Ogni sistema viene inizializzato con il bus immediatamente in .add(),
    garantendo che le sottoscrizioni avvengano nell'ordine dichiarato.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus:     EventBus               = bus
        self._systems: list                   = []
        self._refs:    dict[str, object]      = {}

    def add(self, system, ref: str = "") -> "GameSystemBuilder":
        """Inizializza il sistema con il bus, lo accoda e salva la reference.

        Args:
            system: istanza ISystem da registrare
            ref:    nome opzionale per recuperare l'istanza dopo build()
                    (es. ref="craft_sys" → refs["craft_sys"] = system)

        Returns:
            self — per catena fluente
        """
        system.initialize(self._bus)
        self._systems.append(system)
        if ref:
            self._refs[ref] = system
        return self

    def build(self) -> tuple[list, dict[str, object]]:
        """Restituisce (lista_sistemi_ordinata, dict_reference).

        Da chiamare una sola volta al termine della catena .add().
        """
        return list(self._systems), dict(self._refs)


class GameManager:
    """
    Controller centrale Singleton.
    Gestisce lo stato globale di gioco (ex GS) e il loop pygame.
    """
    _instance: "GameManager | None" = None

    def __new__(cls) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameManager":
        if cls._instance is None:
            cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def initialize(self) -> None:
        if self._initialized:
            return
        self._event_bus    = EventBus()
        self._systems      = []
        self._save_manager = SaveManager()
        self.audio = AudioManager()

        self._current_screen: str = "menu"
        self.Rivet            = None
        self.Echo            = None
        self.player         = None
        self.p1             = [5, 7]
        self.p2             = [5, 7]
        self.enemies: list  = []
        self.blog: list[str] = []
        self.wlog: list[str] = []
        self.hlog: list[str] = []
        self.save: dict     = {}
        self.ethics: int    = 0
        self.xp: int        = 0
        self.combo_cooldown: int = 0
        self.reps           = {"razziatori": -40, "solidali": 15, "erranti": 0, "dannati": 0}
        self.looted: set    = set()
        self.defeated_npcs: set = set()
        self.fled_npcs: set = set()          # NPC da cui si è fuggiti (HP parziali)
        self.fled_npc_hp: dict = {}          # npc_key → lista hp dei nemici sopravvissuti
        self.current_battle_npc: dict | None = None
        self.turn: str      = "player"
        self.hack_sys       = None
        self.craft_sys      = None
        self.party_sys      = None
        self.battle_sys     = None
        self.bus            = None
        self.over_reason: str = ""
        self.puzzle_type: str = "slot"
        self.craft_msg: str = ""
        self.craft_ok: bool = True
        self.predialogue_npc: dict | None = None
        self.predialogue_options: list = []
        self.bat_cursor: int = 0
        self.cft_cursor: int = 0
        self.cft_target: str = "Rivet"
        self.hack_input: str = ""
        self.Rivet_sprite     = None
        self.Echo_sprite     = None
        self.sb_map         = None
        self.bat_renderer   = None
        self.flash_msg: str  = ""
        self.flash_timer: int = 0
        self.quest_sys = None
        self.flags: dict = {}

        self.running: bool  = False
        self.state: str     = "Default"
        self._initialized   = True
        self._audio_refresh: bool = False

    @property
    def screen(self) -> str:
        return self._current_screen

    @screen.setter
    def screen(self, value: str) -> None:
        self._current_screen = value

    def change_screen(self, name: str) -> None:
        """Cambia la scEchomata attiva in modo esplicito."""
        self._current_screen = name

    @property
    def reputation_sys(self):
        """Restituisce il ReputationSystem tramite get_system()."""
        return self.get_system(ReputationSystem)

    def modify_rep(self, faction_id: str, delta: int) -> None:
        """Aggiorna sia gs.reps (retrocompatibilità) che ReputationSystem.

        Le Screen devono chiamare questo metodo al posto di modificare
        gs.reps direttamente. Il metodo aggiorna il dict legacy (gs.reps)
        e propaga REPUTATION_CHANGED sull'EventBus così ReputationSystem
        (e tutti i sistemi iscritti) ricevono l'aggiornamento.
        """
        self._updating_rep = True
        try:
            if faction_id in self.reps:
                old_rep = self.reps[faction_id]
                self.reps[faction_id] = max(-50, min(50, old_rep + delta))
            else:
                old_rep = 0
            if self.bus:
                self.bus.publish(EventType.REPUTATION_CHANGED,
                                 {"faction": faction_id, "delta": delta})

            if delta > 0 and self.Rivet and self.Echo:
                new_rep = self.reps.get(faction_id, 0)
                crossed = (new_rep // 5) - (old_rep // 5)
                if crossed > 0:
                    xp_award = crossed * 15
                    r_msgs = self.Rivet.stats.gain_xp(xp_award)
                    e_msgs = self.Echo.stats.gain_xp(xp_award)
                    self.log(self.wlog,
                             f"Rep {faction_id} +{xp_award} XP a entrambi (ogni 5 punti)")
                    for m in r_msgs + e_msgs:
                        self.log(self.wlog, m)
        finally:
            self._updating_rep = False

    def modify_ethics(self, delta: int) -> None:
        """Aggiorna gs.ethics e notifica CoupleEthicsSystem via EventBus.

        Le Screen devono chiamare questo metodo al posto di modificare
        gs.ethics direttamente. Il metodo aggiorna il valore legacy (cache
        di lettura per le Screen) e propaga ETHICS_CHANGED sull'EventBus
        così CoupleEthicsSystem riceve tutti gli aggiornamenti.
        """
        self._updating_ethics = True
        try:
            old_ethics = self.ethics
            self.ethics = max(-10, min(10, self.ethics + delta))
            if self.bus:
                self.bus.publish(EventType.ETHICS_CHANGED, {"delta": delta})

            if delta > 0 and self.Rivet and self.Echo:
                crossed = (self.ethics // 5) - (old_ethics // 5)
                if crossed > 0:
                    xp_award = crossed * 15
                    r_msgs = self.Rivet.stats.gain_xp(xp_award)
                    e_msgs = self.Echo.stats.gain_xp(xp_award)
                    self.log(self.wlog, f"Etica +{xp_award} XP a entrambi (ogni 5 punti)")
                    for m in r_msgs:
                        self.log(self.wlog, f"[Rivet] {m}")
                    for m in e_msgs:
                        self.log(self.wlog, f"[Echo] {m}")
        finally:
            self._updating_ethics = False

    def start_new_game(self) -> None:
        """Resetta lo stato per una nuova partita."""
        self.p1          = [5, 7]
        self.p2          = [5, 7]
        self.enemies     = []
        self.blog        = []
        self.wlog        = []
        self.hlog        = []
        self.save        = {}
        self.ethics      = 0
        self.xp          = 0
        self.reps        = {"razziatori": -40, "solidali": 15, "erranti": 0, "dannati": 0}
        self.looted      = set()
        self.dropped_spots: list = []
        self.partial_loot: dict  = {}
        self.defeated_npcs = set()
        self.fled_npcs: set = set()
        self.fled_npc_hp: dict = {}
        self.current_battle_npc = None
        self.turn        = "player"
        self.over_reason = ""
        self.bat_cursor  = 0
        self.cft_cursor  = 0
        self.cft_target  = "Rivet"
        self.hack_input  = ""
        self.craft_msg   = ""
        self.craft_ok    = True
        self.predialogue_npc     = None
        self.predialogue_options = []
        self.flash_msg   = ""
        self.flash_timer = 0
        self.flags = {}

    def start_debug_battle(self) -> None:
        """Avvia una battaglia di debug contro il Gigante di Carne.

        Personaggi costruiti ex-novo con:
          - HP ridotti a 29 per testare scenari critici
          - tech_points massimi (tutte le skill sbloccate)
          - Inventari pieni di offensivi x2 e curativi x3
          - Tutte le armi con 5 munizioni
          - Tutti i crafting avanzati sbloccati
        Appartiene al Controller: costruisce lo stato di partita completo
        e imposta la schermata battaglia senza coinvolgere la View.
        """

        self.start_new_game()
        self.Rivet = CharacterDirector(RivetBuilder()).construct()
        self.Echo  = CharacterDirector(EchoBuilder()).construct()
        self._setup_systems()

        _MAX_TECH = 999
        self.Rivet.stats.tech_points = _MAX_TECH
        self.Echo.stats.tech_points  = _MAX_TECH
        self.Rivet.stats.hp = 29
        self.Echo.stats.hp  = 29

        self.modify_ethics(10)

        hv_node = self.Echo.skill_wheel.get_skill("Hacking Veloce")
        if hv_node:
            hv_node.unlock_tech = 0

        for node in self.Rivet.skill_wheel:
            node.current_cooldown = 0
        for node in self.Echo.skill_wheel:
            node.current_cooldown = 0

        craft = self.get_system(CraftingSystem)
        if craft:
            craft.unlock_advanced_chemistry("Rivet")
            craft.unlock_advanced_chemistry("Echo")
            craft.unlock_weapon_tech("Rivet")
            craft.unlock_weapon_tech("Echo")
            craft.unlock_high_explosives("Rivet")
            craft.unlock_high_explosives("Echo")
            craft.unlock_unstable_synthesis("Rivet")
            craft.unlock_unstable_synthesis("Echo")

        self.Rivet.inventory.max_weight = 9999
        self.Echo.inventory.max_weight  = 9999

        for char in (self.Rivet, self.Echo):
            for item in list(char.inventory._items.values()):
                char.inventory.remove_item(item.item_id, item.quantity)

        OFFENSIVI = [
            ("molotov_cocktail", "Cocktail Molotov",   ItemType.CONSUMABLE, 40,  35),
            ("thermite_01",      "Termite",             ItemType.CONSUMABLE, 15,  60),
            ("c4_01",            "Carica C4",           ItemType.CONSUMABLE, 50, 120),
            ("piranha_solution", "Piranha Solution",    ItemType.CONSUMABLE, 10,  40),
            ("battle_explosive", "Esplosivo Combatt.",  ItemType.CONSUMABLE, 25,  50),
            ("grenade_01",       "Granata Flash",       ItemType.CONSUMABLE,  0,  90),
            ("landmine_01",      "Mina Militare",       ItemType.CONSUMABLE, 80, 150),
        ]
        for item_id, name, itype, dmg, val in OFFENSIVI:
            self.Rivet.inventory.add_item(Item(item_id, name, itype, quantity=2, damage=dmg, value=val))
            if item_id in ("molotov_cocktail", "grenade_01"):
                self.Echo.inventory.add_item(Item(item_id, name, itype, quantity=2, damage=dmg, value=val))

        for char in (self.Rivet, self.Echo):
            char.inventory.add_item(Item("medkit_01", "Kit medico", ItemType.CONSUMABLE,
                                         quantity=3, hp_restore=30, value=40))
            char.inventory.add_item(Item("medkit_advanced", "Kit med. avanzato", ItemType.CONSUMABLE,
                                         quantity=2, hp_restore=60, value=80))

        rivet_weapons = [
            WeaponRegistry.heavy_rifle(ammo=5),
            WeaponRegistry.rail_gun(ammo=5),
            WeaponRegistry.acid_gun(ammo=5),
            WeaponRegistry.incendiary_missile(ammo=5),
            WeaponRegistry.artillery(charges=5),
            WeaponRegistry.antimatter_grenade(qty=5),
            WeaponRegistry.light_pistol(ammo=5),
            WeaponRegistry.improvised_club(ammo=5),
            WeaponRegistry.improvised_knife(ammo=5),
        ]
        self.Rivet.weapons = rivet_weapons
        self.Rivet.equip_weapon(rivet_weapons[0])

        echo_weapons = [
            WeaponRegistry.light_pistol(ammo=5),
            WeaponRegistry.rusty_pistol(ammo=5),
            WeaponRegistry.improvised_club(ammo=5),
            WeaponRegistry.improvised_knife(ammo=5),
        ]
        self.Echo.weapons = echo_weapons
        self.Echo.equip_weapon(echo_weapons[0])

        self.enemies = [EnemyFactory.create_meat_giant()]

        self._piranha_used_this_battle  = False
        self._rivet_healed_in_battle    = False
        self._echo_healed_in_battle     = False
        self._rattoppo_used_this_battle = False
        self._fusione_used_this_battle  = False
        self._miraggio_used_this_battle = False

        self.screen = "battle"

    def start_battle(self, npc: dict) -> None:
        """Avvia la battaglia con l'NPC indicato.

        Costruisce i nemici tramite le factory appropriate, imposta lo stato
        di battaglia (enemies, turn, bat_cursor, pending_faction_loot_strategy)
        e transisce alla schermata battle.
        Appartiene al Controller: nessuna View deve manipolare direttamente
        questi attributi di stato.

        Args:
            npc: dizionario NPC con almeno le chiavi 'name', 'faction',
                 opzionalmente 'sprite' e '_local_pos'.
        """

        f          = npc["faction"]
        npc_name   = npc["name"]
        npc_sprite = npc.get("sprite", "")

        if f == "zombie":
            assembly = FactionAssembler.build_zombie_group(npc_name)
            enemies  = assembly.enemies
        elif f in ("razziatori", "dannati", "solidali", "erranti"):
            assembly     = FactionAssembler.build(f.capitalize(), npc_name)
            e            = assembly.enemy
            e.sprite_key = npc_name
            enemies      = [e]
            self.pending_faction_loot_strategy = assembly.loot_strategy
        else:
            e            = EnemyFactory.create_infetto()
            e.name       = npc_name
            e.sprite_key = npc_sprite
            enemies      = [e]

        self.enemies      = enemies
        self.blog         = [f"⚔  Scontro con {npc['name']}!"]
        local_pos         = npc.get("_local_pos") or npc.get("pos")
        self.current_battle_npc = {**npc, "_local_pos": local_pos}

        if f in self.reps and self.reps[f] > 0:
            value = -10 if self.reps[f] > 0 else -5
            self.modify_rep(f, value)
            self.flash(f"Reputazione {f.capitalize()} {value}", 80)

        self.turn       = "player"
        self.bat_cursor = 0
        self.get_system(BattleSystem)
        self.screen = "battle"

    def apply_dialogue_effects(self, effects: dict) -> dict:
        """Applica la parte di stato degli effetti di un nodo di dialogo.

        Appartiene al Controller: modifica flags, inventari, quest.
        NON emette feedback visivi (flash, bark) — quelli restano nella View.

        Returns:
            dict con chiavi opzionali per guidare il feedback visivo:
              - "map_unlocked"   : bool
              - "item_cost_ok"   : {item_id: qty_consegnata}
              - "item_cost_fail" : {item_id: qty_mancante}
              - "combat_trigger" : bool  (combat_risk scattato)
              - "flee_success"   : bool | None  (None = nessun flee_attempt)
        """

        feedback: dict = {}
        if not effects:
            return feedback

        if "set_flag" in effects:
            for key, value in effects["set_flag"].items():
                self.flags[key] = value
                if self.quest_sys:
                    self.quest_sys.notify_flag_set(key, value)
                if key == "rael_paid" and value:
                    feedback["map_unlocked"] = True

        if "cost" in effects:
            cost_ok   = {}
            cost_fail = {}
            for item_id, qty in effects["cost"].items():
                remaining = qty
                for char in (self.Rivet, self.Echo):
                    if remaining <= 0:
                        break
                    for item in char.inventory.all_items():
                        if remaining <= 0:
                            break
                        name_match = getattr(item, "name",    "").lower() == item_id.lower()
                        id_match   = getattr(item, "item_id", "").lower() == item_id.lower()
                        if name_match or id_match:
                            char.inventory.remove_item(
                                getattr(item, "item_id", item.name))
                            remaining -= 1
                if remaining <= 0:
                    cost_ok[item_id]   = qty
                else:
                    cost_fail[item_id] = remaining
            if cost_ok:
                feedback["item_cost_ok"]   = cost_ok
            if cost_fail:
                feedback["item_cost_fail"] = cost_fail

        if "combat_risk" in effects:
            import random
            risk = effects["combat_risk"]
            feedback["combat_trigger"] = random.random() < risk

        if "flee_attempt" in effects:
            import random
            success_rate = effects.get("flee_success_rate", 0.5)
            feedback["flee_success"] = random.random() < success_rate

        return feedback

    def end_battle(self, victory: bool = True, fled: bool = False) -> None:
        """Chiude la battaglia e transisce alla schermata corretta.

        In caso di vittoria vera (victory=True, fled=False):
          - Segna l'NPC corrente come sconfitto nel mondo di gioco.
          - Pubblica BATTLE_ENDED con result="victory".
          - Torna a "explore".
        In caso di fuga riuscita (victory=True, fled=True):
          - NON segna l'NPC come sconfitto.
          - Salva la chiave NPC in fled_npcs per bloccare il re-trigger immediato.
          - Pubblica BATTLE_ENDED con result="fled" (senza generare loot).
          - Torna a "explore".
        In caso di sconfitta:
          - Pubblica BATTLE_ENDED con result="defeat".
          - Transisce a "gameover".

        Args:
            victory: True = vittoria o fuga, False = sconfitti.
            fled:    True = la battaglia è terminata per fuga (non vittoria).
        """
        if victory:
            npc = getattr(self, "current_battle_npc", None)
            if fled:
                # Fuga: non aggiungere a defeated_npcs, ma registra in fled_npcs
                if npc and "pos" in npc:
                    npc_key = (npc.get("name", ""),
                               tuple(npc.get("_local_pos") or npc["pos"]))
                    self.fled_npcs.add(npc_key)
                    # Salva gli HP correnti dei nemici sopravvissuti
                    surviving = npc.get("saved_enemies", self.enemies)
                    self.fled_npc_hp[npc_key] = [
                        e.stats.hp for e in surviving if hasattr(e, "stats")
                    ]
                self.current_battle_npc = None
                if self.bus:
                    self.bus.publish(EventType.BATTLE_ENDED, {
                        "result":  "fled",
                        "enemies": [],
                    })
            else:
                if npc and "pos" in npc:
                    npc_key = (npc.get("name", ""),
                               tuple(npc.get("_local_pos") or npc["pos"]))
                    self.defeated_npcs.add(npc_key)
                    # Pulizia: se precedentemente fuggiti, rimuovi dai fled
                    self.fled_npcs.discard(npc_key)
                    self.fled_npc_hp.pop(npc_key, None)
                self.current_battle_npc = None
                if self.bus:
                    self.bus.publish(EventType.BATTLE_ENDED, {
                        "result":  "victory",
                        "enemies": self.enemies,
                    })
            self.screen = "explore"
        else:
            if self.bus:
                self.bus.publish(EventType.BATTLE_ENDED,
                                 {"result": "defeat", "enemies": []})
            self.screen = "gameover"

    def set_gameover(self, reason: str) -> None:
        """Imposta il motivo di game-over e transisce alla schermata gameover.

        Unico punto di scrittura su over_reason: garantisce che il messaggio
        e la transizione avvengano sempre insieme.

        Args:
            reason: stringa mostrata nella schermata game-over.
        """
        self.over_reason = reason
        self.screen = "gameover"

    _TERMINAL_PUZZLE: dict = {
        (162, 31): "radar",
        (61,  56): "pipe",
        (171, 103): "node",
    }

    def activate_terminal(self, terminal_pos: tuple) -> bool:
        """Attiva un terminale di hacking e transisce alla schermata hack.

        Imposta active_terminal, puzzle_type, hlog e avvia hack_sys.
        La View non deve più conoscere né le coordinate né il tipo di puzzle.

        Args:
            terminal_pos: coordinata (x, y) del terminale.

        Returns:
            True se il terminale è stato attivato, False se sconosciuto
            o se hack_sys ha rifiutato (can_hack).
        """
        puzzle_type = self._TERMINAL_PUZZLE.get(terminal_pos)
        if puzzle_type is None:
            return False

        if not self.hack_sys:
            return False

        ok, reason = self.hack_sys.can_hack(terminal_pos)
        if not ok:
            return False

        self.active_terminal = terminal_pos
        self.puzzle_type     = puzzle_type
        self.hlog            = []
        self.hack_sys.start_hacking(puzzle_type, "Echo")
        self.screen = "hack"
        return True

    def complete_hacking(self) -> dict:
        """Applica gli effetti di stato di un hacking riuscito.

        Appartiene al Controller: gestisce flags, quest, collision removal
        e transizione di schermata. La View (hack_screen) delega qui dopo
        aver rilevato p.is_solved(), e usa il dict restituito solo per il
        feedback visivo (flash, bark).

        Returns:
            dict con chiavi opzionali per guidare il feedback visivo:
              - "bark_key"       : str  — chiave bark da emettere
              - "flash_msg"      : str  — messaggio flash aggiuntivo
              - "flash_duration" : int  — durata del flash aggiuntivo
        """
        from game.world.city_engine import MAP_TILE_PX

        feedback: dict = {}
        active_term = getattr(self, "active_terminal", None)
        if active_term is None:
            return feedback

        if self.hack_sys:
            self.hack_sys.mark_hacked(active_term)

        self.modify_ethics(+1)
        self.Echo.stats.gain_tech_points(10)

        _SKYSCRAPER_TERM = (61,  56)
        _RADAR_TOWER     = (162, 31)
        _CENTRAL_TERM    = (171, 103)

        if active_term == _SKYSCRAPER_TERM:
            if not self.flags.get("skyscraper_terminal_hacked", False):
                self.flags["skyscraper_terminal_hacked"] = True
                if self.quest_sys:
                    self.quest_sys.notify_flag_set(
                        "skyscraper_terminal_hacked", True)
                explore_scr = getattr(self, "_explore_screen", None)
                if explore_scr and hasattr(explore_scr, "maps"):
                    _BLOCK_GLOBAL = (62, 52)
                    for m in explore_scr.maps:
                        off_tx = round(m.offset_x / MAP_TILE_PX)
                        off_ty = round(m.offset_y / MAP_TILE_PX)
                        local_cell = (
                            _BLOCK_GLOBAL[0] - off_tx,
                            _BLOCK_GLOBAL[1] - off_ty,
                        )
                        if local_cell in m.collision_cells:
                            m.collision_cells.discard(local_cell)
                            break
                feedback["bark_key"]       = "hack_story_safe"
                feedback["flash_msg"]      = "ACCESSO APERTO — Raggiungi la cassaforte!"
                feedback["flash_duration"] = 150

        elif active_term == _RADAR_TOWER:
            if not self.flags.get("radar_tower_hacked", False):
                self.flags["radar_tower_hacked"]    = True
                self.flags["radar_station_active"]  = True
                self.flags["giants_visible_on_map"] = True
                if self.quest_sys:
                    self.quest_sys.notify_flag_set("radar_tower_hacked", True)
                feedback["bark_key"]       = "hack_story_radar"
                feedback["flash_msg"]      = "RADAR ATTIVO — I GIGANTI SONO SULLA MAPPA!"
                feedback["flash_duration"] = 200

        elif active_term == _CENTRAL_TERM:
            if not self.flags.get("factory_terminal_hacked", False):
                self.flags["factory_terminal_hacked"] = True
                if self.quest_sys:
                    self.quest_sys.notify_flag_set(
                        "factory_terminal_hacked", True)
                self.active_terminal = None
                self.screen = "factory_finale"
                return feedback

        self.active_terminal = None
        self.screen = "explore"
        return feedback

    def select_player(self, choice_idx: int) -> None:
        """Imposta il giocatore principale e prepara lo stato iniziale di partita.

        Appartiene al Controller: scrive su gs.player, gs.blog, gs.wlog
        e attiva la prima quest. La View (select_screen) deve solo comunicare
        la scelta dell'utente (0 = Rivet, 1 = Echo) senza toccare lo stato.

        Args:
            choice_idx: 0 per Rivet, qualsiasi altro valore per Echo.
        """
        self.build_party()
        self.player = self.Rivet if choice_idx == 0 else self.Echo
        self.blog   = []
        self.wlog   = []
        if self.quest_sys:
            self.quest_sys.activate_quest("Q01_grattacielo")
        self.screen = "explore"

    def breach_door(self, door: dict, district_code: str = "") -> None:
        """Registra lo sfondamento di una porta e notifica le quest.

        Appartiene al Controller: scrive i flag su self.flags e notifica
        quest_sys. La View (explore_screen) gestisce solo la parte fisica
        (rimozione collision_cells, bark, flash) e delega qui la parte di stato.

        Args:
            door:          dizionario porta con almeno la chiave 'pos': (x, y).
            district_code: codice del distretto corrente (es. "F" per Fabbrica).
                           Usato per rilevare automaticamente factory_inner_door_breached.
        """
        if not hasattr(self, "flags"):
            self.flags = {}

        dx, dy    = door["pos"]
        flag_key  = f"door_breached_{dx}_{dy}"

        self.flags[flag_key] = True
        if self.quest_sys:
            self.quest_sys.notify_flag_set(flag_key, True)

        if district_code == "F" and not self.flags.get(
                "factory_inner_door_breached", False):
            self.flags["factory_inner_door_breached"] = True
            if self.quest_sys:
                self.quest_sys.notify_flag_set(
                    "factory_inner_door_breached", True)

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def save_manager(self) -> SaveManager:
        return self._save_manager

    def register_system(self, system) -> None:
        """Deprecato — usare GameSystemBuilder in _setup_systems().

        Mantenuto per retrocompatibilità con eventuale codice esterno.
        Emette DeprecationWarning a runtime per segnalare l'uso scorretto.
        """
        import warnings
        warnings.warn(
            "register_system() è deprecato. "
            "Usare GameSystemBuilder.add() in _setup_systems().",
            DeprecationWarning,
            stacklevel=2,
        )
        system.initialize(self._event_bus)
        self._systems.append(system)

    def get_system(self, system_type):
        """Restituisce il primo sistema registrato del tipo richiesto, o None."""
        for s in self._systems:
            if isinstance(s, system_type):
                return s
        return None

    def create_memento(self) -> GameMemento:
        """Crea un Memento con l'intero stato di partita.

        Serializza TUTTO: stats complete dei personaggi (level, atk, max_hp,
        effects, inventario, armi), terminali hackerati, NPC sconfitti,
        dialoghi visti (via flags), reputazioni, quest, posizioni, etica.
        """
        Rivet_stats = self.Rivet.stats.to_dict() if self.Rivet else {}
        Echo_stats  = self.Echo.stats.to_dict()  if self.Echo  else {}

        Rivet_inv = self.Rivet.inventory.to_dict() if self.Rivet else []
        Echo_inv  = self.Echo.inventory.to_dict()  if self.Echo  else []

        def _serialize_weapons(char):
            if char is None:
                return []
            result = []
            for w in getattr(char, "weapons", []):
                result.append({"item_id": w.item_id, "ammo": w.ammo})
            return result

        def _equipped_id(char):
            if char is None:
                return None
            w = getattr(char, "equipped_weapon", None)
            return w.item_id if w else None

        def _serialize_skills(char):
            if char is None:
                return []
            wheel = getattr(char, "skills", None)
            if wheel is None:
                return []
            return wheel.to_dict()

        hack_sys = self.hack_sys
        hacked_terminals = hack_sys.to_dict() if hack_sys else {"hacked_terminals": []}

        defeated_npcs_list = []
        for entry in getattr(self, "defeated_npcs", set()):
            if isinstance(entry, tuple):
                defeated_npcs_list.append(list(entry))
            else:
                defeated_npcs_list.append(entry)

        # Serializza fled_npcs come lista di [nome, [x, y]]
        fled_npcs_list = []
        for entry in getattr(self, "fled_npcs", set()):
            if isinstance(entry, tuple):
                fled_npcs_list.append(list(entry))
            else:
                fled_npcs_list.append(entry)

        # Serializza fled_npc_hp come lista di {key: [nome,[x,y]], hp: [...]}
        fled_npc_hp_list = []
        for key, hp_list in getattr(self, "fled_npc_hp", {}).items():
            fled_npc_hp_list.append({
                "key": list(key) if isinstance(key, tuple) else key,
                "hp":  list(hp_list),
            })

        snapshot = {
            "state":         self.state,
            "running":       self.running,
            "ethics":        self.ethics,
            "xp":            self.xp,
            "combo_cooldown":self.combo_cooldown,

            "p1": list(self.p1),
            "p2": list(self.p2),

            "Rivet_stats": Rivet_stats,
            "Echo_stats":  Echo_stats,

            "Rivet_inventory":  Rivet_inv,
            "Echo_inventory":   Echo_inv,

            "Rivet_weapons":         _serialize_weapons(self.Rivet),
            "Rivet_equipped_weapon": _equipped_id(self.Rivet),
            "Echo_weapons":          _serialize_weapons(self.Echo),
            "Echo_equipped_weapon":  _equipped_id(self.Echo),

            "Rivet_skills": _serialize_skills(self.Rivet),
            "Echo_skills":  _serialize_skills(self.Echo),

            "reps":   dict(self.reps),
            "looted": [list(x) for x in self.looted],
            "flags":  dict(getattr(self, "flags", {})),

            "quests": self.quest_sys.to_dict() if self.quest_sys else {},

            "defeated_npcs": defeated_npcs_list,
            "fled_npcs":     fled_npcs_list,
            "fled_npc_hp":   fled_npc_hp_list,

            "hacking": hacked_terminals,

            "dropped_spots": self._serialize_dropped_spots(),

            "partial_loot": self._serialize_partial_loot(),

            "mines_gone":  [list(pos) for pos in getattr(
                                getattr(self, "_explore_screen", None), "_mines_gone", set())],
            "mine_placed": getattr(getattr(self, "_explore_screen", None), "_mine_placed", False),
            "mine_timer":  getattr(getattr(self, "_explore_screen", None), "_mine_timer",  0.0),

            "puzzle_type": self.puzzle_type,
        }
        return GameMemento(snapshot, location=self.state)

    def restore_from_memento(self, m: GameMemento | None) -> None:
        """Ripristina l'intero stato di partita da un Memento."""
        if m is None:
            return
        snap = m.get_state_snapshot()

        self.state          = snap.get("state",          "Default")
        self.running        = snap.get("running",        False)
        self.ethics         = snap.get("ethics",         0)
        self.xp             = snap.get("xp",             0)
        self.combo_cooldown = snap.get("combo_cooldown", 0)

        self.p1 = list(snap.get("p1", [18, 20]))
        self.p2 = list(snap.get("p2", [19, 20]))

        if self.party_sys:
            if hasattr(self.party_sys, "members"):
                self.party_sys.members.clear()
            elif hasattr(self.party_sys, "_members"):
                self.party_sys._members.clear()
        self.build_party()

        if self.Rivet:
            rivet_stats = snap.get("Rivet_stats", {})
            if rivet_stats:
                self.Rivet.stats.restore_from_dict(rivet_stats)
            else:
                self.Rivet.stats.hp = snap.get("Rivet_hp", self.Rivet.stats.max_hp)
                self.Rivet.stats.xp = snap.get("Rivet_xp", 0)

        if self.Echo:
            echo_stats = snap.get("Echo_stats", {})
            if echo_stats:
                self.Echo.stats.restore_from_dict(echo_stats)
            else:
                self.Echo.stats.hp = snap.get("Echo_hp", self.Echo.stats.max_hp)
                self.Echo.stats.xp = snap.get("Echo_xp", 0)

        if self.Rivet:
            rivet_inv_data = snap.get("Rivet_inventory", [])
            if rivet_inv_data:
                self.Rivet.inventory = Inventory.from_dict(rivet_inv_data)
        if self.Echo:
            echo_inv_data = snap.get("Echo_inventory", [])
            if echo_inv_data:
                self.Echo.inventory = Inventory.from_dict(echo_inv_data)

        self._audio_refresh = True

        def _restore_weapons(char, weapons_data, equipped_id):
            if char is None or not weapons_data:
                return
            char.weapons.clear()
            char.equipped_weapon = None
            factory = {
                "rail_gun":           WeaponRegistry.rail_gun,
                "acid_gun":           WeaponRegistry.acid_gun,
                "antimatter_grenade": WeaponRegistry.antimatter_grenade,
                "incendiary_missile": WeaponRegistry.incendiary_missile,
                "artillery":          WeaponRegistry.artillery,
                "thermobaric_rocket": WeaponRegistry.thermobaric_rocket,
                "assault_rifle":      WeaponRegistry.heavy_rifle,
                "recovered_weapon":   WeaponRegistry.recovered_weapon,
                "light_pistol":       WeaponRegistry.light_pistol,
                "pistol_01":          WeaponRegistry.light_pistol,
                "heavy_rifle_01":     WeaponRegistry.heavy_rifle,
                "improvised_club":    WeaponRegistry.improvised_club,
                "improvised_knife":   WeaponRegistry.improvised_knife,
            }
            for wd in weapons_data:
                wid   = wd.get("item_id", "")
                ammo  = wd.get("ammo", -1)
                fn    = factory.get(wid)
                if fn:
                    w = fn(ammo) if ammo != -1 else fn()
                    w.item_id = wid
                    char.weapons.append(w)
                    if wid == equipped_id:
                        char.equipped_weapon = w
                else:
                    print(f"[SAVE] Attenzione: arma '{wid}' non trovata nella factory — ignorata.")

        _restore_weapons(
            self.Rivet,
            snap.get("Rivet_weapons", []),
            snap.get("Rivet_equipped_weapon"),
        )
        _restore_weapons(
            self.Echo,
            snap.get("Echo_weapons", []),
            snap.get("Echo_equipped_weapon"),
        )

        def _restore_skills(char, skills_data):
            if char is None or not skills_data:
                return
            wheel = getattr(char, "skills", None)
            if wheel is not None:
                wheel.restore_from_dict(skills_data)

        _restore_skills(self.Rivet, snap.get("Rivet_skills", []))
        _restore_skills(self.Echo,  snap.get("Echo_skills",  []))

        self.reps   = dict(snap.get("reps",   self.reps))
        self.looted = set(tuple(x) for x in snap.get("looted", []))
        self.flags  = snap.get("flags", {})

        if self.quest_sys:
            self.quest_sys.restore_from_dict(snap.get("quests", {}))

        def _to_npc_key(entry):
            """Converte [nome, [x, y]] → (nome, (x, y)) ricorsivamente."""
            if isinstance(entry, (list, tuple)):
                return tuple(_to_npc_key(e) for e in entry)
            return entry

        self.defeated_npcs = set(
            _to_npc_key(x) for x in snap.get("defeated_npcs", [])
        )

        # Ripristina fled_npcs e fled_npc_hp
        self.fled_npcs = set(
            _to_npc_key(x) for x in snap.get("fled_npcs", [])
        )
        self.fled_npc_hp = {}
        for entry in snap.get("fled_npc_hp", []):
            key = _to_npc_key(entry["key"])
            self.fled_npc_hp[key] = list(entry.get("hp", []))

        if self.hack_sys:
            self.hack_sys.restore_from_dict(snap.get("hacking", {}))

        self.dropped_spots = self._deserialize_dropped_spots(
            snap.get("dropped_spots", [])
        )

        if getattr(self, '_explore_screen', None) is not None:
            self._explore_screen._mines_gone = set(
                tuple(pos) for pos in snap.get("mines_gone", [])
            )
            mine_placed = snap.get("mine_placed", False)
            mine_timer  = float(snap.get("mine_timer", 0.0))

            if mine_placed and not self.flags.get("power_plant_door_blown", False):
                mine_placed = False
                mine_timer  = 0.0

            self._explore_screen._mine_placed = mine_placed
            self._explore_screen._mine_timer  = mine_timer

        self.partial_loot = self._deserialize_partial_loot(
            snap.get("partial_loot", [])
        )

        self.puzzle_type = snap.get("puzzle_type", "slot")

    def _serialize_partial_loot(self) -> list:
        """Serializza le casse parzialmente saccheggiate in formato JSON-friendly.

        Struttura output: lista di {pos, items} dove items ha gli stessi campi
        usati da _serialize_dropped_spots.
        """
        result = []
        for pos, items in getattr(self, "partial_loot", {}).items():
            if not items:
                continue
            items_data = []
            for it in items:
                items_data.append({
                    "item_id":   it.item_id,
                    "name":      it.name,
                    "item_type": it.item_type.name,
                    "quantity":  it.quantity,
                    "value":     it.value,
                    "hp_restore":it.hp_restore,
                    "damage":    it.damage,
                    "defense":   it.defense,
                })
            result.append({
                "pos":   list(pos),
                "items": items_data,
            })
        return result

    def _deserialize_partial_loot(self, data: list) -> dict:
        """Ricrea il dict partial_loot da dati serializzati.

        Restituisce {tuple(pos): [Item, ...]} pronto per essere assegnato
        a gs.partial_loot in modo che _collect_loot lo trovi subito.
        """
        result = {}
        for entry in data:
            pos = tuple(entry["pos"])
            items = []
            for d in entry.get("items", []):
                try:
                    itype = ItemType[d.get("item_type", "CONSUMABLE")]
                except KeyError:
                    itype = ItemType.CONSUMABLE
                items.append(Item(
                    item_id    = d["item_id"],
                    name       = d.get("name", d["item_id"]),
                    item_type  = itype,
                    quantity   = d.get("quantity", 1),
                    value      = d.get("value", 0),
                    hp_restore = d.get("hp_restore", 0),
                    damage     = d.get("damage", 0),
                    defense    = d.get("defense", 0),
                ))
            if items:
                result[pos] = items
        return result

    def _serialize_dropped_spots(self) -> list:
        """Serializza i dropped spots (zaini lasciati a terra) in formato JSON-friendly."""
        result = []
        for spot in getattr(self, "dropped_spots", []):
            items_data = []
            for it in spot.get("items", []):
                items_data.append({
                    "item_id":   it.item_id,
                    "name":      it.name,
                    "item_type": it.item_type.name,
                    "quantity":  it.quantity,
                    "value":     it.value,
                    "hp_restore":it.hp_restore,
                    "damage":    it.damage,
                    "defense":   it.defense,
                })
            result.append({
                "pos":   list(spot["pos"]),
                "label": spot.get("label", "Zaino a terra"),
                "items": items_data,
            })
        return result

    def _deserialize_dropped_spots(self, data: list) -> list:
        """Ricrea i dropped spots da dati serializzati."""
        spots = []
        for entry in data:
            items = []
            for d in entry.get("items", []):
                try:
                    itype = ItemType[d.get("item_type", "CONSUMABLE")]
                except KeyError:
                    itype = ItemType.CONSUMABLE
                items.append(Item(
                    item_id    = d["item_id"],
                    name       = d.get("name", d["item_id"]),
                    item_type  = itype,
                    quantity   = d.get("quantity", 1),
                    value      = d.get("value", 0),
                    hp_restore = d.get("hp_restore", 0),
                    damage     = d.get("damage", 0),
                    defense    = d.get("defense", 0),
                ))
            if items:
                spots.append({
                    "pos":       tuple(entry["pos"]),
                    "zone_type": "dropped",
                    "label":     entry.get("label", "Zaino a terra"),
                    "looted":    False,
                    "items":     items,
                })
        return spots

    def run(self, surface) -> None:
        """Loop principale pygame.
        Gestisce scaling dinamico della finestra, eventi, rendering e audio.
        """
        import pygame
        from pathlib import Path
        from game.screens import (
            Screen, MenuScreen, SelectScreen, ExploreScreen,
            BattleScreen, CraftScreen, HackScreen, PauseScreen,
            GameOverScreen, WorldMapScreen, SkillWheelScreen, QuestScreen, VictoryScreen
        )
        from game.screens.factory_finale_screen import FactoryFinaleScreen

        register_default_items()
        self._setup_systems()

        self.audio.initialize()
        self.audio.load_sound(
            "menu_zombie",
            asset("audio/menu_mixed.wav"),
        )

        self.audio.load_music(
            "explore",
            asset("audio/explore_theme.wav"),
            volume=0.6
        )
        self.audio.load_music(
            "combat",
            asset("audio/combat_theme.wav"),
            volume=0.3
        )
        self.audio.load_music(
            "gameover",
            asset("audio/game_over_evil.wav")
        )

        self.audio.load_music(
             "victory",
            asset("audio/victory_theme.wav"),
            volume=0.6
        )

        self.audio.load_sound(
            "explosion",
            asset("audio/explosion_theme.wav"),
            volume=0.9
        )

        self.audio._build_audio_map()

        self.Rivet_sprite = make_Rivet_sprite()
        self.Echo_sprite = make_Echo_sprite()
        _sb_path = str(
            asset_path("Map/mappa_sb.json")
        )
        try:
            self.sb_map = JsonTiledMap(_sb_path)
        except Exception as e:
            print(f"[sb_map] {e}")

        PIXEL_FONT_PATH = asset("fonts/PressStart2P-Regular.ttf")

        def _load_font(size, bold=False):
            try:
                return pygame.font.Font(PIXEL_FONT_PATH, size)
            except Exception:
                print(f"[WARN] Font pixel non trovato, uso fallback")
                for name in ("Courier New", "DejaVu Sans Mono", "monospace"):
                    try:
                        return pygame.font.SysFont(name, size, bold=bold)
                    except Exception:
                        pass
                return pygame.font.Font(None, size)

        def _load_consolas(size, bold=False):
            try:
                path = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
                return pygame.font.Font(path, size)
            except Exception:
                try:
                    return pygame.font.SysFont("Consolas", size, bold=bold)
                except Exception:
                    return pygame.font.Font(None, size)

        fonts = {
            "sm":   _load_consolas(13),
            "md":   _load_consolas(16),
            "lg":   _load_consolas(20),
            "xl":   _load_consolas(26, bold=True),
            "bold": _load_consolas(16, bold=True),
        }

        from game.screens.help_screen import HelpScreen
        from game.screens.intro_screen import IntroScreen

        screens: dict[str, Screen] = {
            "menu":     MenuScreen(fonts),
            "select":   SelectScreen(fonts),
            "explore":  ExploreScreen(fonts),
            "battle":   BattleScreen(fonts),
            "craft":    CraftScreen(fonts),
            "hack":     HackScreen(fonts),
            "pause":    PauseScreen(fonts),
            "gameover": GameOverScreen(fonts),
            "victory":  VictoryScreen(fonts),
            "factory_finale": FactoryFinaleScreen(fonts),
            "worldmap": WorldMapScreen(fonts),
            "skill_wheel": SkillWheelScreen(fonts),
            "quest_log": QuestScreen(fonts),
            "help":     HelpScreen(fonts),
            "intro":    IntroScreen(fonts)
        }
        self._explore_screen = screens["explore"]

        effects = EffectManager()
        self._clock = pygame.time.Clock()
        clock = self._clock
        prev_screen = None

        surf = surface

        internal_surf = pygame.Surface((W, H))

        win_w, win_h = surf.get_size()
        state_ref: dict = {
            "surf":    surf,
            "scale_x": W / win_w,
            "scale_y": H / win_h,
            "W":       W,
            "H":       H,
        }
        event_chain = build_event_chain(self, state_ref, screens)

        while True:
            clock.tick(FPS)

            screen_changed = self.screen != prev_screen

            if screen_changed or self._audio_refresh:
                if screen_changed and prev_screen and prev_screen in screens:
                    prev_obj = screens[prev_screen]
                    if hasattr(prev_obj, "on_exit"):
                        prev_obj.on_exit()

                self.audio.apply_for_screen(self.screen)

                if screen_changed:
                    current_screen_obj = screens.get(self.screen)
                    if current_screen_obj and hasattr(current_screen_obj, "on_enter"):
                        current_screen_obj.on_enter()

                prev_screen = self.screen
                self._audio_refresh = False

            current = screens[self.screen]

            events = pygame.event.get()

            surf = state_ref["surf"]

            save_menu_sys = self.get_system(SaveMenuSystem)
            is_save_menu_open = save_menu_sys and save_menu_sys.is_open

            for event in events:
                event_chain.handle(event)

            surf = state_ref["surf"]

            if not is_save_menu_open:
                current.update()

            ox, oy = effects.camera.offset

            if ox != 0 or oy != 0:
                shifted = pygame.Surface((W, H))
                shifted.fill(BG)
                current.draw(shifted)
                internal_surf.blit(shifted, (ox, oy))
            else:
                current.draw(internal_surf)

            effects.update()
            effects.draw(internal_surf)

            if is_save_menu_open:
                save_menu_sys.render(
                    internal_surf, W, H,
                    fonts["xl"], fonts["bold"], fonts["sm"], fonts["sm"],
                    save_menu_sys.mode
                )
                save_menu_sys.handle_input(events)

            if self.flash_timer > 0:
                alpha = min(220, self.flash_timer * 6)
                font = fonts["bold"]

                if self.screen == "explore" and "explore" in screens:
                    map_w = getattr(screens["explore"], "MAP_VIEW_W", 860)
                    cx = 8 + (map_w // 2)
                    max_box_w = map_w - 60
                else:
                    cx = W // 2
                    max_box_w = W - 100

                words = self.flash_msg.split()
                lines = []
                current_line = ""
                for word in words:
                    test_line = current_line + word + " "
                    if font.size(test_line)[0] > max_box_w and current_line:
                        lines.append(current_line.rstrip())
                        current_line = word + " "
                    else:
                        current_line = test_line
                if current_line:
                    lines.append(current_line.rstrip())

                line_height = font.get_height()
                total_height = len(lines) * (line_height + 4)

                base_y = H - 100

                for i, line in enumerate(lines):
                    fs = font.render(line, True, GREEN)
                    fs.set_alpha(alpha)

                    row_y = base_y - (len(lines) - 1 - i) * (line_height + 4)
                    fr = fs.get_rect(center=(cx, row_y))

                    bg_rect = fr.inflate(24, 12)
                    bg_surf = pygame.Surface((bg_rect.w, bg_rect.h), pygame.SRCALPHA)
                    bg_surf.fill((10, 15, 20, min(190, alpha)))
                    internal_surf.blit(bg_surf, bg_rect.topleft)

                    internal_surf.blit(fs, fr)

                self.flash_timer -= 1

            win_w, win_h = surf.get_size()
            scaled_surf = pygame.transform.scale(internal_surf, (win_w, win_h))

            surf.blit(scaled_surf, (0, 0))
            pygame.display.flip()

    def _setup_systems(self) -> None:
        """Inizializza e registra tutti i sistemi ISystem nell'ordine corretto
        di dipendenza, + sottoscrizione GAME_OVER.

        PATTERN: Builder (GoF — Creazionale)
          GameSystemBuilder costruisce la lista sistemi con API fluente.
          L'ordine di dipendenza è dichiarativo e visibile in un unico posto.
          Aggiungere un sistema = 1 riga .add(...).
          Le reference (craft_sys, battle_sys, ecc.) sono dichiarate esplicitamente
          invece di essere sparse in blocchi separati.

        Ordine di registrazione (le dipendenze prima dei consumatori):
          1. PartySystem          — gestione party, base per ComboCommand
          2. ReputationSystem     — fazioni; richiesto da PreDialogueSystem/WorldRules
          3. CoupleEthicsSystem   — etica di coppia via ETHICS_CHANGED
          4. CraftingSystem       — crafting e azioni speciali
          5. HackingSystem        — puzzle hacking
          6. LootSystem           — generazione loot post-battaglia
          7. BattleSystem         — ciclo battaglia con TurnManager
          8. PreDialogueSystem    — opzioni pre-combattimento
          9. WorldRulesSystem     — aggressione NPC, rianimazione, danni chimici
         10. MovementSystem       — movimento avanzato con keybinding
         11. DialogueManager      — dialoghi strutturati (Solidali + Razziatori)
         12. HUDSystem            — HUD inventario e interazione co-op
         13. SaveMenuSystem       — UI salvataggio a 3 slot
         14. QuestSystem          — missioni e obiettivi
        """

        self._event_bus = EventBus()
        self._systems.clear()

        if hasattr(self, '_clock') and self._clock:
            self._clock.tick()

        self._systems, refs = (
            GameSystemBuilder(self._event_bus)
            .add(PartySystem(),                           ref="party_sys")
            .add(ReputationSystem())
            .add(CoupleEthicsSystem())
            .add(CraftingSystem(),                        ref="craft_sys")
            .add(HackingSystem(),                         ref="hack_sys")
            .add(LootSystem())
            .add(BattleSystem(),                          ref="battle_sys")
            .add(PreDialogueSystem())
            .add(WorldRulesSystem())
            .add(MovementSystem())
            .add(DialogueManager())
            .add(HUDSystem())
            .add(SaveMenuSystem(self._save_manager, self))
            .add(QuestSystem(),                           ref="quest_sys")
            .build()
        )

        self.party_sys  = refs["party_sys"]
        self.craft_sys  = refs["craft_sys"]
        self.hack_sys   = refs["hack_sys"]
        self.battle_sys = refs["battle_sys"]
        self.quest_sys  = refs["quest_sys"]
        self.bus        = self._event_bus

        register_all_quests(self.quest_sys)

        def _on_game_over(data):
            self.over_reason = data.get("reason", "sconosciuto")
            self.audio.stop_music()
            self.screen = "gameover"

        self._event_bus.subscribe(EventType.GAME_OVER, _on_game_over)

        def _on_game_won(data):
            self.win_reason = data.get("reason", "Hai completato il gioco!")
            self.screen = "victory"

        self._event_bus.subscribe(EventType.GAME_WON, _on_game_won)

        def _on_rep_changed_gs(data):
            if getattr(self, "_updating_rep", False):
                return
            faction = data.get("faction")
            delta   = data.get("delta", 0)
            if faction and faction in self.reps:
                self.reps[faction] = max(-100, min(100, self.reps[faction] + delta))

        self._event_bus.subscribe(EventType.REPUTATION_CHANGED, _on_rep_changed_gs)

    def build_party(self) -> None:
        """Crea i personaggi tramite CharacterDirector e li aggiunge al party.

        Nota: sprite, tilemap e sb_map vengono caricati una volta sola in run()
        prima che questa funzione venga chiamata. build_party() si occupa
        esclusivamente della costruzione dei personaggi e del party.
        """

        Rivet = CharacterDirector(RivetBuilder()).construct()
        Echo = CharacterDirector(EchoBuilder()).construct()
        if self.party_sys is not None:
            self.party_sys.add_member(Rivet)
            self.party_sys.add_member(Echo)
        self.Rivet = Rivet
        self.Echo = Echo

        rep_sys = self.reputation_sys
        if rep_sys:
            for fid in FactionID:
                f = rep_sys.get_faction(fid)
                if f:
                    self.reps[fid.value] = f.current_reputation

        movement = self.get_system(MovementSystem)
        if movement:
            movement.register_player("p1", Rivet, KeyBinding.default_p1(),
                                     start_col=self.p1[0], start_row=self.p1[1])
            movement.register_player("p2", Echo, KeyBinding.default_p2(),
                                     start_col=self.p2[0], start_row=self.p2[1])

        world_rules = self.get_system(WorldRulesSystem)
        if world_rules:
            world_rules.build_aggro_from_npc_list(NPCS)

    def apply_save(self, slot_id: int = 0) -> bool:
        if self._save_manager.has_slot(slot_id):
            self._save_manager.load_game(self, slot_id)
            self._log(self.wlog, f"Partita caricata (slot {slot_id}).")
            self._audio_refresh = True
            return True

        s = self.save
        if not s:
            return False

        self.p1     = list(s.get("p1", [18, 20]))
        self.p2     = list(s.get("p2", [19, 20]))
        self.ethics = s.get("ethics", 0)

        if self.party_sys:
            if hasattr(self.party_sys, "members"): self.party_sys.members.clear()
            elif hasattr(self.party_sys, "_members"): self.party_sys._members.clear()
        self.build_party()

        if self.Rivet:
            self.Rivet.stats.hp = s.get("Rivet_hp", self.Rivet.stats.max_hp)
            self.Rivet.stats.xp = s.get("him_xp", 0)
        if self.Echo:
            self.Echo.stats.hp = s.get("Echo_hp", self.Echo.stats.max_hp)
            self.Echo.stats.xp = s.get("Echo_xp", 0)

        self.reps   = dict(s.get("reps",   self.reps))
        self.looted = set(tuple(x) for x in s.get("looted", []))
        self.flags  = s.get("flags", {})

        def _to_npc_key(entry):
            if isinstance(entry, (list, tuple)):
                return tuple(_to_npc_key(e) for e in entry)
            return entry

        self.defeated_npcs = set(
            _to_npc_key(x) for x in s.get("defeated_npcs", [])
        )
        self.fled_npcs = set(
            _to_npc_key(x) for x in s.get("fled_npcs", [])
        )
        self.fled_npc_hp = {}
        for entry in s.get("fled_npc_hp", []):
            key = _to_npc_key(entry["key"])
            self.fled_npc_hp[key] = list(entry.get("hp", []))
        if self.hack_sys:
            self.hack_sys.restore_from_dict(s.get("hacking", {}))
        if self.quest_sys:
            self.quest_sys.restore_from_dict(s.get("quests", {}))

        self._log(self.wlog, "Partita caricata (legacy).")
        self._audio_refresh = True
        return True

    def do_save(self, slot_id: int = 0) -> None:
        """Salva lo stato corrente nello slot indicato tramite SaveManager + Memento.

        Sostituisce il vecchio meccanismo basato su gs.save (dict parallelo):
        ora tutto passa per create_memento() → SaveManager.save_game().
        Il dict gs.save viene aggiornato per retrocompatibilità con il codice
        che ancora lo legge (es. il check `if gs.save` in MenuScreen).
        """
        self._save_manager.save_game(self, slot_id)

        self.save = self._save_manager._slots[slot_id].get_state_snapshot()

        self._log(self.wlog, f"Partita salvata (slot {slot_id}).")
        self.flash_msg   = "SALVATA"
        self.flash_timer = 60

    def log(self, lst: list, msg: str, n: int = 14) -> None:
        """Aggiunge msg a lst mantenendo al massimo n voci (API pubblica)."""
        lst.append(msg)
        if len(lst) > n:
            lst.pop(0)

    def flash(self, msg: str, duration: int = 90) -> None:
        """Mostra un messaggio flash sovrapposto allo scEchomo."""
        self.flash_msg   = msg
        self.flash_timer = duration

    @staticmethod
    def _log(lst: list, msg: str, n: int = 14) -> None:
        """Alias statico per retrocompatibilità con main.log()."""
        lst.append(msg)
        if len(lst) > n:
            lst.pop(0)

    def check_skill_unlocks(self) -> None:
        """Controlla se i tech points attuali sbloccano nuove abilità per i personaggi."""
        if self.Rivet and hasattr(self.Rivet, 'skill_wheel') and self.craft_sys:
            tech = self.Rivet.stats.tech_points

            chimica_node = self.Rivet.skill_wheel.get_skill("Sintesi Tossicologica")
            if chimica_node and chimica_node.is_unlocked(tech):
                self.craft_sys.unlock_advanced_chemistry("Rivet")

            bellica_node = self.Rivet.skill_wheel.get_skill("Ingegneria Bellica")
            if bellica_node and bellica_node.is_unlocked(tech):
                self.craft_sys.unlock_weapon_tech("Rivet")

            esplosivi_node = self.Rivet.skill_wheel.get_skill("Esperto di Esplosivi")
            if esplosivi_node and esplosivi_node.is_unlocked(tech):
                self.craft_sys.unlock_high_explosives("Rivet")
                if not self.flags.get("rivet_esperto_esplosivi_unlocked", False):
                    self.flags["rivet_esperto_esplosivi_unlocked"] = True
                    if hasattr(self, "quest_sys") and self.quest_sys:
                        self.quest_sys.notify_flag_set("rivet_esperto_esplosivi_unlocked", True)

            instabile_node = self.Rivet.skill_wheel.get_skill("Sintesi Instabile")
            if instabile_node and instabile_node.is_unlocked(tech):
                self.craft_sys.unlock_unstable_synthesis("Rivet")