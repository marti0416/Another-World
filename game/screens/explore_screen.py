"""
explore_screen.py — Screen di esplorazione della città (State GoF).

Gestisce il movimento dei giocatori, le interazioni con NPC e loot spot,
i trigger di incontro, il dialogo, il salvataggio e il rendering della città.
È la screen principale del gioco e delega ai sistemi registrati nel GameManager.
"""

from __future__ import annotations
import os
import random
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.paths import asset
from game.world.world_data import (
    W, H, BG, BG2, BG3, CYAN, GREEN, RED, YELLOW, GREY, WHITE, DARKGREY, ORANGE, PANEL,
    NPCS, TERMINALS, LOOT_SPOTS, npc_is_hostile, FPS,
    MINE_SPOTS, MINE_PLACEMENT_SPOT
)
from game.world.encounters import ENCOUNTERS
import game.world.world_data as wd
from game.view.draw_utils import txt, hp_bar, panel, sep, near_obj, cur_district
from game.controller.game_manager import GameManager
from game.world.city_engine import load_map, compute_offsets, build_light_overlay, MAP_TILE_PX, MAP_CONFIGS
from game.events.event_types import EventType
from game.dialogue.dialogue_barks import get_bark, EXPLORE_BARKS
from game.view.speech_bubble import SpeechBubbleManager
from game.systems.quest_system import QuestStatus
from game.model.item import ItemType
from game.model.faction_factory import ZombieFactory
from game.model.item_registry import get_item_proto
from game.model.weapon_system import InventoryWeightManager, WeaponRegistry, WeaponCategory, Echo_ALLOWED_CATEGORIES
from game.systems.movement_system import MovementSystem
from game.systems.world_rules import WorldRulesSystem

_MS       = MovementSystem
_MSCam    = MovementSystem
_MSDbg    = MovementSystem
_MSBubble = MovementSystem
from game.systems.loot_system import LootSystem, LootContext
from game.dialogue.dialogue import DialogueManager
from game.view.renderer import load_lpc_frames
from game.world.world_data import MAGENTA, ORANGE

class _RainDrop:
    __slots__ = ("x", "y", "speed", "length", "alpha")

    def __init__(self):
        self._reset(spawn=True)

    def _reset(self, spawn: bool = False):
        self.x      = random.randint(0, W)
        self.y      = random.randint(0, H) if spawn else -10
        self.speed  = random.uniform(8, 18)
        self.length = random.randint(6, 12)
        self.alpha  = random.randint(60, 140)

    def update(self):
        self.y += self.speed
        self.x -= 1
        if self.y > H + 20:
            self._reset()

    def draw(self, surf: Surface):
        s = pygame.Surface((1, self.length), pygame.SRCALPHA)
        s.fill((180, 210, 255, self.alpha))
        surf.blit(s, (int(self.x), int(self.y)))

class ExploreScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)
        self.simboli_font_lg = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 24)
        self._anim = 0.0
        self._debug_collisions  = False
        self._debug_node_puzzle = False

        self._rain_drops  = [_RainDrop() for _ in range(300)]
        self._rain_active = True

        self._dialogue_node   = None
        self._dialogue_cursor = 0
        self._dialogue_npc    = ""

        self._in_predialogue      = False
        self._predialogue_npc     = None
        self._predialogue_options = []
        self._predialogue_cursor  = 0

        self._in_loot_menu = False
        self._current_loot_stash = []
        self._loot_cursor = 0
        self._current_loot_spot = None

        self._acid_timer_p1: float = 0.0
        self._acid_timer_p2: float = 0.0
        self.ACID_DMG_INTERVAL: float = 0.8
        self.ACID_DMG_AMOUNT:   int   = 1

        self._mine_placed:       bool  = False
        self._mine_timer:        float = 0.0
        self.MINE_FUSE_TIME:     float = 3.0
        self._mines_gone: set = set()

        self._log_box = None

        self._bubbles = SpeechBubbleManager()

        self._selected_slot = [0, 0]

        self._maps_loaded = False
        self.maps = []
        self.city_w = 0
        self.city_h = 0

        self.MAP_VIEW_W = 860
        self.MAP_VIEW_H = H - 16

        self._loot_offset = 0
        self._drop_offset = 0
        self._use_item_offset = 0
        self.MAX_VISIBLE_ITEMS = 8

    def _wbark(self, text: str):
        """
        Scorciatoia ibrida: logga nel wlog E mostra la speech bubble.
        Sostituisce self._wbark(...) per i barks dei personaggi.
        """
        gs = GameManager.get_instance()
        gs.log(gs.wlog, text)
        self._bubbles.add_from_bark(text)

    def _load_city_and_collisions(self):
        print("[ExploreScreen] Caricamento Grafica e Collisioni JSON...")
        gs = GameManager.get_instance()
        asset_dir = str(__import__("game.paths", fromlist=["ASSETS_ROOT"]).ASSETS_ROOT)
        offsets = compute_offsets()

        self.maps = []
        tutti_i_mob_reali = []
        self._dynamic_loot_spots = []

        for i, (ox, oy) in enumerate(offsets, start=1):
            m = load_map(i, ox, oy, asset_dir)
            self.maps.append(m)

            offset_tiles_x = round(m.offset_x / MAP_TILE_PX)
            offset_tiles_y = round(m.offset_y / MAP_TILE_PX)

            for spot in m.loot_spots:
                spot_global = spot.copy()
                spot_global["pos"] = (spot["pos"][0] + offset_tiles_x, spot["pos"][1] + offset_tiles_y)
                self._dynamic_loot_spots.append(spot_global)

            for npc in m.mobs:
                npc_global = npc.copy()
                npc_global["_local_pos"] = tuple(npc["pos"])
                npc_global["pos"] = (npc["pos"][0] + offset_tiles_x, npc["pos"][1] + offset_tiles_y)
                npc_global["_px"] = npc["pos"][0] * MAP_TILE_PX + m.offset_x
                npc_global["_py"] = npc["pos"][1] * MAP_TILE_PX + m.offset_y
                tutti_i_mob_reali.append(npc_global)

        self.city_w = self.maps[-1].offset_x + self.maps[-1].width_px
        self.city_h = self.maps[-1].offset_y + self.maps[-1].height_px

        movement = gs.get_system(MovementSystem)
        if movement:
            movement.set_maps(self.maps, self.city_w, self.city_h)

        world_rules = gs.get_system(WorldRulesSystem)
        if world_rules:
            world_rules._aggro_triggers = []
            world_rules.build_aggro_from_npc_list(tutti_i_mob_reali)

        self._tutti_i_mob_reali = tutti_i_mob_reali

        gs.enclosed_zones = {}
        import game.world.world_data as wd
        for m in self.maps:
            for zone_name, cells in m.enclosed_zones.items():
                if zone_name not in gs.enclosed_zones:
                    gs.enclosed_zones[zone_name] = set()
                gs.enclosed_zones[zone_name].update(cells)
            if m.power_house_pos is not None:
                print("power house")
                lx, ly = m.power_house_pos

                otx = round(m.offset_x / MAP_TILE_PX)
                oty = round(m.offset_y / MAP_TILE_PX)

                wd.POWER_PANEL_SPOT = (lx + otx, ly + oty+2)
        self._maps_loaded = True
        self._apply_breached_doors_from_flags()
        self._restore_dropped_spots_from_save()

    def on_enter(self):
        if not self._maps_loaded:
            self._load_city_and_collisions()
        else:
            gs = GameManager.get_instance()
            movement = gs.get_system(MovementSystem)
            if movement:
                movement.set_maps(self.maps, self.city_w, self.city_h)
            world_rules = gs.get_system(WorldRulesSystem)
            if world_rules and hasattr(self, '_tutti_i_mob_reali'):
                world_rules._aggro_triggers = []
                world_rules.build_aggro_from_npc_list(self._tutti_i_mob_reali)

        gs = GameManager.get_instance()

        if gs.bus and getattr(self, "_current_bus_id", None) != id(gs.bus):
            gs.bus.subscribe(EventType.START_ENCOUNTER, self._on_aggro_triggered)
            gs.bus.subscribe(EventType.OBJECTIVE_COMPLETED, self._on_objective_completed)
            self._current_bus_id = id(gs.bus)

    def _on_objective_completed(self, data: dict):
        """Mostra un flash con il prossimo obiettivo quando uno viene completato."""
        gs = GameManager.get_instance()
        quest_id = data.get("quest_id")

        state = gs.quest_sys._states.get(quest_id)
        if not state or state.status != QuestStatus.ACTIVE:
            return

        next_obj = next((o for o in state.objectives if not o.completed and not o.hidden), None)

        if next_obj:
            msg = f"OBIETTIVO COMPLETATO! Prossimo: {next_obj.description}"
            gs.flash(msg, 200)

    def _on_aggro_triggered(self, data: dict):
        """Callback chiamata quando WorldRulesSystem rileva che un nemico ci ha visti."""
        gs = GameManager.get_instance()

        if self._in_predialogue or self._dialogue_node is not None or gs.screen != "explore":
            return

        faction      = data.get("faction", "zombie")
        trigger_pos  = data.get("trigger_pos")

        real_npc = None
        if trigger_pos is not None:
            mob_list = getattr(self, "_tutti_i_mob_reali", [])
            for npc in mob_list:
                if tuple(npc.get("pos", ())) == tuple(trigger_pos):
                    npc_key = (npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"]))
                    if npc_key in gs.defeated_npcs:
                        return
                    real_npc = npc
                    break

        if real_npc is None:
            real_npc = {
                "name":    faction.capitalize(),
                "faction": faction,
                "sprite":  "Orda" if faction == "zombie" else faction.capitalize(),
            }

        if faction == "zombie":
            gs.flash(f"AGGUATO! {real_npc['name']} attacca!", 100)
        else:
            gs.flash(f"CONFRONTO! {real_npc['name']} vi sbarra la strada!", 120)

        self._fight_npc(real_npc)

    def handle_event(self, event):
        gs = GameManager.get_instance()
        self._last_input_time = pygame.time.get_ticks()
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if k == pygame.K_F5:
            self._mine_placed = True
            self._mine_timer = 0.0
            return

        if getattr(self, '_in_loot_menu', False):
            self._handle_loot_menu_input(event)
            return None

        if getattr(self, '_in_drop_menu', False):
            self._handle_drop_menu_input(event)
            return None

        if getattr(self, '_in_use_menu', False):
            self._handle_use_menu_input(event)
            return None

        if self._dialogue_node is not None:
            self._handle_dialogue_input(k)
            return

        if self._in_predialogue:
            self._handle_predialogue_input(k)
            return

        if k == pygame.K_e: self._interact()
        elif k == pygame.K_F1: self._debug_collisions = not self._debug_collisions
        elif k == pygame.K_F2: self._debug_node_puzzle = not self._debug_node_puzzle
        elif k == pygame.K_c:
            self._wbark(get_bark(EXPLORE_BARKS, "open_crafting"))
            gs.screen = "craft"
            gs.cft_cursor = 0

        elif k == pygame.K_m:
            rael_paid = gs.flags.get("rael_paid", False)
            if rael_paid:
                self._wbark(get_bark(EXPLORE_BARKS, "open_map"))
                gs.screen = "worldmap"
            else:
                rael_talked = (
                    gs.flags.get("rael_prag_quest_active", False) or
                    gs.flags.get("rael_diplo_quest_active", False) or
                    gs.flags.get("rael_aggro_quest_active", False) or
                    gs.flags.get("rael_emp_quest_active", False)
                )
                if rael_talked:
                    self._wbark(get_bark(EXPLORE_BARKS, "map_locked_rael"))
                else:
                    self._wbark(get_bark(EXPLORE_BARKS, "map_locked_no_rael"))
        elif k == pygame.K_q:
            self._wbark(get_bark(EXPLORE_BARKS, "open_quests"))
            gs.screen = "quest_log"
        elif k == pygame.K_h: self._hack()
        elif k == pygame.K_p or k == pygame.K_ESCAPE: gs.screen = "pause"
        elif k == pygame.K_r: gs.check_skill_unlocks(); gs.screen = "skill_wheel"

        elif pygame.K_1 <= k <= pygame.K_5:
            self._handle_inventory_slot(k - pygame.K_1, char_idx=0)
        elif pygame.K_6 <= k <= pygame.K_9:
            self._handle_inventory_slot(k - pygame.K_6, char_idx=1)
        elif k == pygame.K_0:
            self._handle_inventory_slot(4, char_idx=1)

        if not hasattr(self, '_inv_offset'): self._inv_offset = [0, 0]

        if k == pygame.K_z:
            self._inv_offset[0] = max(0, self._inv_offset[0] - 1)
        elif k == pygame.K_x:
            self._inv_offset[0] += 1
        elif k == pygame.K_o:
            self._inv_offset[1] = max(0, self._inv_offset[1] - 1)
        elif k == pygame.K_p:
            self._inv_offset[1] += 1

        elif k == pygame.K_g:
            self._open_drop_menu(0)
        elif k == pygame.K_j:
            self._open_drop_menu(1)
        elif k == pygame.K_u:
            self._open_use_menu()

    def _handle_loot_menu_input(self, event: pygame.event.Event) -> None:
        """Gestisce l'input quando la finestra del bottino è aperta."""
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_UP:
            self._loot_cursor = max(0, self._loot_cursor - 1)
            if self._loot_cursor < self._loot_offset:
                self._loot_offset = self._loot_cursor

        elif event.key == pygame.K_DOWN:
            self._loot_cursor = min(len(self._current_loot_stash) - 1, self._loot_cursor + 1)
            if self._loot_cursor >= self._loot_offset + self.MAX_VISIBLE_ITEMS:
                self._loot_offset = self._loot_cursor - self.MAX_VISIBLE_ITEMS + 1

        elif event.key == pygame.K_TAB:
            self._loot_target_idx = 1 - self._loot_target_idx

        elif event.key == pygame.K_RETURN or event.key == pygame.K_e:
            if self._current_loot_stash:
                self._loot_cursor = max(0, min(self._loot_cursor, len(self._current_loot_stash) - 1))
                item = self._current_loot_stash[self._loot_cursor]

                gs = GameManager.get_instance()
                target_char = gs.Rivet if getattr(self, '_loot_target_idx', 0) == 0 else gs.Echo


                if InventoryWeightManager.can_add(target_char.name, target_char.inventory, item.quantity, target_char.weapons):

                    if item.item_type == ItemType.WEAPON:

                        WEAPON_CATEGORY_MAP = {
                            "pistol_01":          WeaponCategory.LIGHT,
                            "light_pistol":       WeaponCategory.LIGHT,
                            "improvised_club":    WeaponCategory.MELEE,
                            "improvised_knife":   WeaponCategory.MELEE,
                            "heavy_rifle_01":     WeaponCategory.HEAVY,
                            "recovered_weapon":   WeaponCategory.HEAVY,
                            "assault_rifle":      WeaponCategory.HEAVY,
                            "antimatter_grenade": WeaponCategory.EXPLOSIVE,
                            "incendiary_missile": WeaponCategory.SPECIAL,
                            "artillery":          WeaponCategory.SPECIAL,
                            "thermobaric_rocket": WeaponCategory.SPECIAL,
                            "rail_gun":           WeaponCategory.HEAVY,
                            "acid_gun":           WeaponCategory.HEAVY,
                        }

                        weapon_cat = WEAPON_CATEGORY_MAP.get(item.item_id, WeaponCategory.HEAVY)
                        if target_char.name == "Echo" and weapon_cat not in Echo_ALLOWED_CATEGORIES:
                            gs.flash(
                                "Echo non può portare armi pesanti! Assegnala a Rivet.",
                                120
                            )
                            return

                        factory_map = {
                            "pistol_01": WeaponRegistry.light_pistol,
                            "heavy_rifle_01": getattr(WeaponRegistry, "heavy_rifle", None),
                            "improvised_club": WeaponRegistry.improvised_club,
                            "improvised_knife": WeaponRegistry.improvised_knife,
                            "antimatter_grenade": WeaponRegistry.antimatter_grenade,
                            "incendiary_missile": WeaponRegistry.incendiary_missile,
                            "artillery": WeaponRegistry.artillery,
                            "thermobaric_rocket": WeaponRegistry.thermobaric_rocket
                        }
                        factory = factory_map.get(item.item_id)
                        if factory:
                            for _ in range(item.quantity):
                                new_weapon = factory()
                                target_char.weapons.append(new_weapon)
                            bark_key = "loot_weapon_rivet" if target_char.name == "Rivet" else "loot_weapon_echo"
                            self._wbark(get_bark(EXPLORE_BARKS, bark_key))
                            gs.flash(f"RACCOLTO: {new_weapon.display_name}", 80)
                        else:
                            self._wbark(get_bark(EXPLORE_BARKS, "weapon_error"))
                    else:
                        target_char.inventory.add_item(item)
                        bark_key = "loot_generic_rivet" if target_char.name == "Rivet" else "loot_generic_echo"
                        self._wbark(get_bark(EXPLORE_BARKS, bark_key))
                        gs.flash(f"RACCOLTO: {item.name} x{item.quantity}", 80)

                    self._current_loot_stash.pop(self._loot_cursor)

                    if self._loot_cursor >= len(self._current_loot_stash):
                        self._loot_cursor = max(0, len(self._current_loot_stash) - 1)

                    if not self._current_loot_stash:
                        self._in_loot_menu = False

                        if getattr(self, '_current_loot_spot', None) is not None:
                            self._current_loot_spot["looted"] = True
                            gs.looted.add(tuple(self._current_loot_spot["pos"]))
                            gs.dropped_spots = [
                                s for s in self._dynamic_loot_spots
                                if s.get("zone_type") == "dropped" and not s.get("looted", False)
                            ]
                else:
                    bark_full = "inv_full_rivet" if target_char.name == "Rivet" else "inv_full_echo"
                    self._wbark(get_bark(EXPLORE_BARKS, bark_full))
                    gs.flash("PESO LIMITE SUPERATO", 30)

        elif event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
            self._in_loot_menu = False
            if not self._current_loot_stash:
                if self._current_loot_spot is not None:
                    self._current_loot_spot["looted"] = True
                    gs = GameManager.get_instance()
                    gs.looted.add(tuple(self._current_loot_spot["pos"]))

    def _handle_inventory_slot(self, slot_idx: int, char_idx: int = -1):
        """Seleziona lo slot dell'inventario tenendo conto dello scorrimento."""
        gs = GameManager.get_instance()
        if char_idx == -1:
            is_echo = gs.player is gs.Echo
            char_idx = 1 if is_echo else 0
        char = gs.Echo if char_idx == 1 else gs.Rivet
        if char is None:
            return

        if not hasattr(self, '_inv_offset'): self._inv_offset = [0, 0]
        self._selected_slot[char_idx] = self._inv_offset[char_idx] + slot_idx

    def _open_drop_menu(self, char_idx: int):
        """Apre il pannello per scegliere cosa buttare e in che quantità."""
        gs = GameManager.get_instance()
        char = gs.Rivet if char_idx == 0 else gs.Echo

        if not char.inventory.all_items():
            self._wbark(get_bark(EXPLORE_BARKS, "inv_empty", char=char.name))
            return

        self._in_drop_menu = True
        self._drop_char_idx = char_idx
        self._drop_cursor = 0

    def _open_use_menu(self):
        """Apre il pannello per usare un consumabile durante l'esplorazione."""
        gs = GameManager.get_instance()

        aggregated: dict = {}
        for char in [gs.Rivet, gs.Echo]:
            if char.is_alive():
                for it in char.inventory.get_by_type(ItemType.CONSUMABLE):
                    if it.item_id not in aggregated:
                        aggregated[it.item_id] = it.clone()
                    else:
                        aggregated[it.item_id].quantity += it.quantity

        if not aggregated:
            self._wbark(get_bark(EXPLORE_BARKS, "no_consumables"))
            return

        self._use_item_list = list(aggregated.values())
        self._use_item_cursor = 0
        self._use_item_offset = 0
        self._in_use_menu = True

    def _handle_use_menu_input(self, event):
        """Gestisce l'input dentro la finestra usa-oggetto."""
        if event.type != pygame.KEYDOWN:
            return
        gs = GameManager.get_instance()
        items = getattr(self, '_use_item_list', [])

        if not items:
            self._in_use_menu = False
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._use_item_cursor = max(0, self._use_item_cursor - 1)
            if self._use_item_cursor < self._use_item_offset:
                self._use_item_offset = self._use_item_cursor

        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._use_item_cursor = min(len(items) - 1, self._use_item_cursor + 1)
            if self._use_item_cursor >= self._use_item_offset + self.MAX_VISIBLE_ITEMS:
                self._use_item_offset = self._use_item_cursor - self.MAX_VISIBLE_ITEMS + 1

        elif event.key in (pygame.K_ESCAPE, pygame.K_u):
            self._in_use_menu = False

        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._use_item_cursor = min(self._use_item_cursor, len(items) - 1)
            item_info = items[self._use_item_cursor]
            self._execute_use_item(item_info)

    def _execute_use_item(self, item_info):
        """
        Esegue l'uso di un consumabile durante l'esplorazione.
        - Curativi: usati sul personaggio con meno HP (%).
        - Offensivi: messaggio per conservarli al combattimento.
        - Materiali: non applicabile (filtrati alla creazione della lista).
        """
        gs = GameManager.get_instance()

        if item_info.damage > 0 and item_info.hp_restore == 0:
            char_name = gs.Rivet.name if gs.Rivet.is_alive() else gs.Echo.name
            self._wbark(get_bark(EXPLORE_BARKS, "keep_for_combat", char=char_name))
            self._in_use_menu = False
            return

        if item_info.hp_restore > 0:
            chars_alive = [c for c in [gs.Rivet, gs.Echo] if c.is_alive()]
            if not chars_alive:
                self._in_use_menu = False
                return

            target = min(chars_alive,
                         key=lambda c: c.stats.hp / max(c.stats.max_hp, 1))

            item_owner = None
            for char in [gs.Rivet, gs.Echo]:
                if char.inventory.get_item(item_info.item_id):
                    item_owner = char
                    break

            if not item_owner:
                self._in_use_menu = False
                return

            all_full = all(c.stats.hp >= c.stats.max_hp for c in chars_alive)
            if all_full:
                self._wbark(get_bark(EXPLORE_BARKS, "heal_full", char=item_owner.name))
                return

            old_hp = target.stats.hp
            target.stats.hp = min(target.stats.hp + item_info.hp_restore,
                                  target.stats.max_hp)
            healed = target.stats.hp - old_hp
            item_owner.inventory.remove_item(item_info.item_id, 1)

            self._wbark(get_bark(EXPLORE_BARKS, "use_heal",
                         user=item_owner.name,
                         target=target.name,
                         healed=healed))
            gs.flash(f"+{healed} HP ({target.name})", 80)

            remaining = getattr(self, '_use_item_list', [])
            new_list = []
            for it in remaining:
                total_qty = sum(
                    c.inventory.get_item(it.item_id).quantity
                    for c in [gs.Rivet, gs.Echo]
                    if c.inventory.get_item(it.item_id)
                )
                if total_qty > 0:
                    it.quantity = total_qty
                    new_list.append(it)
            self._use_item_list = new_list

            if not self._use_item_list:
                self._in_use_menu = False
            else:
                self._use_item_cursor = min(
                    self._use_item_cursor, len(self._use_item_list) - 1)
            return

        self._wbark(get_bark(EXPLORE_BARKS, "use_material"))
        self._in_use_menu = False

    def _handle_drop_menu_input(self, event):
        """Gestisce l'input dentro la finestra di abbandono oggetti."""
        if event.type != pygame.KEYDOWN: return
        gs = GameManager.get_instance()
        char = gs.Rivet if self._drop_char_idx == 0 else gs.Echo
        items = char.inventory.all_items()

        if not items:
            self._in_drop_menu = False
            return

        if event.key == pygame.K_UP or event.key == pygame.K_w:
            self._drop_cursor = max(0, self._drop_cursor - 1)
            if self._drop_cursor < self._drop_offset:
                self._drop_offset = self._drop_cursor

        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self._drop_cursor = min(len(items) - 1, self._drop_cursor + 1)
            if self._drop_cursor >= self._drop_offset + self.MAX_VISIBLE_ITEMS:
                self._drop_offset = self._drop_cursor - self.MAX_VISIBLE_ITEMS + 1
        elif event.key == pygame.K_ESCAPE or event.key in (pygame.K_g, pygame.K_j):
            self._in_drop_menu = False
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._drop_cursor = min(self._drop_cursor, len(items) - 1)
            item = items[self._drop_cursor]

            qty_to_drop = 1 if event.key == pygame.K_RETURN else item.quantity
            self._execute_drop(char, item, qty_to_drop)

            if not char.inventory.all_items():
                self._in_drop_menu = False
            else:
                self._drop_cursor = min(self._drop_cursor, len(char.inventory.all_items()) - 1)

    def _execute_drop(self, char, item, qty):
        """Esegue fisicamente la creazione dello stash a terra."""
        gs = GameManager.get_instance()

        if item.item_type == ItemType.WEAPON:
            if getattr(char, "equipped_weapon", None) and char.equipped_weapon.item_id == item.item_id:
                char.unequip_weapon()
            weapon_to_remove = next((w for w in char.weapons if w.item_id == item.item_id), None)
            if weapon_to_remove:
                char.weapons.remove(weapon_to_remove)

        char.inventory.remove_item(item.item_id, qty)

        pos = tuple(gs.p1 if char.name == "Rivet" else gs.p2)
        if pos in gs.looted: gs.looted.remove(pos)

        dropped_item = item.clone()
        dropped_item.quantity = qty

        existing_stash = next((spot for spot in getattr(self, '_dynamic_loot_spots', [])
                               if spot.get("zone_type") == "dropped" and tuple(spot["pos"]) == pos), None)

        if existing_stash:
            if "items" not in existing_stash: existing_stash["items"] = []
            found = False
            for i in existing_stash["items"]:
                if i.item_id == dropped_item.item_id:
                    i.quantity += qty
                    found = True; break
            if not found: existing_stash["items"].append(dropped_item)
        else:
            new_spot = {
                "pos": pos,
                "zone_type": "dropped",
                "label": "Zaino a terra",
                "looted": False,
                "items": [dropped_item]
            }
            self._dynamic_loot_spots.append(new_spot)

        gs.dropped_spots = [
            s for s in self._dynamic_loot_spots
            if s.get("zone_type") == "dropped" and not s.get("looted", False)
        ]

        self._wbark(get_bark(EXPLORE_BARKS, "drop_item", char=char.name))
        gs.flash(f"LASCIATO: {dropped_item.name} x{qty}", 60)

    def _handle_dialogue_input(self, key):
        """Gestisce l'input mentre un dialogo strutturato è aperto."""
        node = self._dialogue_node
        n_choices = len(node.choices)

        if key in (pygame.K_UP, pygame.K_w):
            self._dialogue_cursor = (self._dialogue_cursor - 1) % max(n_choices, 1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._dialogue_cursor = (self._dialogue_cursor + 1) % max(n_choices, 1)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self._advance_dialogue()

    def _advance_dialogue(self):
        """Conferma la scelta corrente e avanza nell'albero."""
        gs = GameManager.get_instance()
        dm = gs.get_system(DialogueManager)

        if dm is None or self._dialogue_node is None:
            self._close_dialogue()
            return

        if not self._dialogue_node.choices:
            start_fight   = self._dialogue_node.effects.get("start_combat", False)
            npc_to_fight  = getattr(self, "_predialogue_npc", None)
            npc_name_dial = getattr(self, "_dialogue_npc", None)

            self._close_dialogue()

            if start_fight:
                if npc_to_fight:
                    gs.start_battle(npc_to_fight)
                elif npc_name_dial:
                    npc_data = next(
                        (n for n in getattr(self, "_zone_npcs", []) if n.get("name") == npc_name_dial),
                        {"name": npc_name_dial}
                    )
                    gs.start_battle(npc_data)
            return

        try:
            choice_tuple = self._dialogue_node.choices[self._dialogue_cursor]
            target_id    = choice_tuple[1]
            target_node  = dm._active_tree._nodes.get(target_id)
            combined_effects = self._dialogue_node.effects.copy()
            choice_effects   = choice_tuple[2] if len(choice_tuple) > 2 else {}
            combined_effects.update(choice_effects)
        except Exception:
            combined_effects = {}

        next_node, _is_ended = dm.choose(self._dialogue_cursor)
        self._dialogue_cursor = 0

        if next_node:
            self._apply_dialogue_effects(combined_effects)
            self._dialogue_node = next_node
        else:
            self._close_dialogue()

    def _close_dialogue(self):
        """Chiude il pannello dialogo e azzera tutto lo stato predialogue."""
        npc_name_closing = getattr(self, "_dialogue_npc", "") or ""
        if npc_name_closing:
            try:
                gs = GameManager.get_instance()
                gs.bus.publish(EventType.DIALOGUE_ENDED, {"npc_name": npc_name_closing})
            except Exception:
                pass
        self._dialogue_node       = None
        self._dialogue_cursor     = 0
        self._dialogue_npc        = ""
        self._in_predialogue      = False
        self._predialogue_npc     = None
        self._predialogue_options = []
        self._predialogue_cursor  = 0

    def _apply_dialogue_effects(self, effects: dict):
        """Elabora gli effetti del nodo di dialogo appena raggiunto.

        La mutazione di stato (flags, inventari, quest) è delegata al
        Controller via gs.apply_dialogue_effects().
        Questo metodo gestisce solo il feedback visivo (flash, bark).
        """
        if not effects:
            return

        gs = GameManager.get_instance()

        feedback = gs.apply_dialogue_effects(effects)

        if feedback.get("map_unlocked"):
            gs.flash("🗺  MAPPA SBLOCCATA — premi M per aprirla", 220)
            self._wbark(get_bark(EXPLORE_BARKS, "map_unlocked"))

        for item_id, qty in feedback.get("item_cost_ok", {}).items():
            gs.flash(f"Consegnato: {qty}x {item_id}", 80)
        for item_id, remaining in feedback.get("item_cost_fail", {}).items():
            gs.flash(f"ERRORE: Non hai abbastanza {item_id}!", 80)

        if "ethics" in effects:
            eth_delta = effects["ethics"]
            if eth_delta:
                sign = "+" if eth_delta > 0 else ""
                gs.flash(f"Etica {sign}{eth_delta}  →  {gs.ethics:+d}", 120)

        if "reputation" in effects:
            for faction_id, rep_delta in effects["reputation"].items():
                if rep_delta:
                    sign = "+" if rep_delta > 0 else ""
                    gs.flash(
                        f"Rep {faction_id.capitalize()} {sign}{rep_delta}"
                        f"  →  {gs.reps.get(faction_id, 0):+d}", 120)

        if feedback.get("combat_trigger"):
            gs.flash("La tensione è esplosa in violenza!", 90)
            npc_to_fight = getattr(self, "_predialogue_npc", None)
            self._close_dialogue()
            if npc_to_fight:
                gs.start_battle(npc_to_fight)

        if "flee_success" in feedback:
            npc_to_fight = getattr(self, "_predialogue_npc", None)
            self._close_dialogue()
            if feedback["flee_success"]:
                gs.flash("Siete riusciti a fuggire!", 90)
            else:
                gs.flash("La fuga è fallita! Combattimento inevitabile!", 90)
                if npc_to_fight:
                    gs.start_battle(npc_to_fight)

    def _handle_predialogue_input(self, key):
        gs = GameManager.get_instance()
        if key == pygame.K_ESCAPE:
            self._in_predialogue = False
            gs.start_battle(self._predialogue_npc)
        elif key in (pygame.K_UP, pygame.K_w):
            self._predialogue_cursor = (self._predialogue_cursor - 1) % len(self._predialogue_options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._predialogue_cursor = (self._predialogue_cursor + 1) % len(self._predialogue_options)
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._resolve_predialogue(self._predialogue_cursor)
        elif pygame.K_1 <= key <= pygame.K_4:
            idx = key - pygame.K_1
            if idx < len(self._predialogue_options):
                self._resolve_predialogue(idx)

    def _resolve_predialogue(self, idx):
        gs = GameManager.get_instance()
        self._in_predialogue = False
        label, tone_id = self._predialogue_options[idx]
        npc = self._predialogue_npc

        if tone_id in ("ATTACK", "IGNORE"):
            gs.start_battle(npc)
        else:
            self._start_dialogue_at(npc, tone_id)

    def _start_dialogue_at(self, npc, root_id):
        gs = GameManager.get_instance()
        dm = gs.get_system(DialogueManager)
        npc_name = npc["name"]
        if dm is None:
            gs.start_battle(npc)
            return
        tree = dm._TREES.get(npc_name)
        if tree is None:
            gs.start_battle(npc); return
        active_tree = tree()
        root_node = active_tree.start(root_id)
        if root_node is None:
            gs.start_battle(npc); return

        self._apply_dialogue_effects(root_node.effects)

        dm._active_tree = active_tree
        self._dialogue_node   = root_node
        self._dialogue_cursor = 0
        self._dialogue_npc    = npc_name


    def _interact(self):
        gs = GameManager.get_instance()
        import math

        p1_pos = tuple(gs.p1)
        p2_pos = tuple(gs.p2)

        door_for_rivet = self._find_nearby_door(p1_pos, (9999, 9999))

        if door_for_rivet is not None:
            self._try_breach_door(door_for_rivet)
            return

        import math as _math
        if not gs.flags.get("power_plant_door_blown", False) and not getattr(self, "_mine_placed", False):
            dist_place = _math.hypot(p1_pos[0] - MINE_PLACEMENT_SPOT[0],
                                     p1_pos[1] - MINE_PLACEMENT_SPOT[1])
            if dist_place <= 2.5:
                if not gs.flags.get("Q01_done", False):
                    pass
                else:
                    has_mine = any(
                        getattr(i, "item_id", "") == "landmine_01"
                        for i in gs.Rivet.inventory.all_items()
                    )
                    if has_mine:
                        gs.Rivet.inventory.remove_item("landmine_01", 1)
                        self._mine_placed = True
                        self._mine_timer  = self.MINE_FUSE_TIME
                        self._wbark(get_bark(EXPLORE_BARKS, "quest_mine_place"))
                        gs.flash("MINA ATTIVATA — 3 secondi all'esplosione!", 180)
                        return
                    else:
                        self._wbark(get_bark(EXPLORE_BARKS, "quest_mine_hint"))
                        gs.flash("Nessuna mina — vai nell'Aeroporto Militare.", 110)
                        return

        tutti_i_mob = []
        if hasattr(self, 'maps'):
            for m in self.maps:
                offset_tiles_x = round(m.offset_x / MAP_TILE_PX)
                offset_tiles_y = round(m.offset_y / MAP_TILE_PX)
                for npc in m.mobs:
                    npc_global = npc.copy()
                    npc_global["_local_pos"] = tuple(npc["pos"])
                    npc_global["pos"] = (
                        npc["pos"][0] + offset_tiles_x,
                        npc["pos"][1] + offset_tiles_y
                    )
                    tutti_i_mob.append(npc_global)

        best_npc = None
        best_npc_dist = 999
        best_npc_char = None

        for npc in tutti_i_mob:
            npc_pos = tuple(npc["pos"])
            npc_key = (npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"]))
            if npc_key in gs.defeated_npcs:
                continue
            for char_obj, pos in [(gs.Rivet, p1_pos), (gs.Echo, p2_pos)]:
                d = math.hypot(pos[0] - npc_pos[0], pos[1] - npc_pos[1])
                if d <= 2.0 and d < best_npc_dist:
                    best_npc_dist = d
                    best_npc = npc
                    best_npc_char = char_obj

        best_loot = None
        best_loot_dist = 999
        best_loot_char = None

        def _near_any_terminal(pos):
            return any(
                abs(pos[0] - tx) <= 1 and abs(pos[1] - ty) <= 1
                for (tx, ty) in TERMINALS
            )
        _player_near_terminal = _near_any_terminal(p1_pos) or _near_any_terminal(p2_pos)

        available_loot = [l for l in getattr(self, '_dynamic_loot_spots', []) if tuple(l["pos"]) not in gs.looted]
        for loot in available_loot:
            loot_pos = tuple(loot["pos"])
            label_check = loot.get("label", "").lower()
            if _player_near_terminal and "cassaforte" not in label_check:
                continue
            for char_obj, pos in [(gs.Rivet, p1_pos), (gs.Echo, p2_pos)]:
                d = math.hypot(pos[0] - loot_pos[0], pos[1] - loot_pos[1])
                if d <= 2.0 and d < best_loot_dist:
                    best_loot_dist = d
                    best_loot = loot
                    best_loot_char = char_obj

        target_obj = None
        target_type = None
        active_char = None

        if best_npc and best_loot:
            if best_npc_dist <= best_loot_dist:
                target_obj, target_type, active_char = best_npc, "npc", best_npc_char
            else:
                target_obj, target_type, active_char = best_loot, "loot", best_loot_char
        elif best_npc:
            target_obj, target_type, active_char = best_npc, "npc", best_npc_char
        elif best_loot:
            target_obj, target_type, active_char = best_loot, "loot", best_loot_char

        if target_type == "npc":
            hostile = npc_is_hostile(target_obj, gs.reps)
            if hostile:
                self._wbark(get_bark(EXPLORE_BARKS, "ambush"))
                gs.flash(f"AGGUATO! {target_obj['name']} attacca!", 100)
                self._fight_npc(target_obj)
            else:
                self._start_dialogue(target_obj)
        elif target_type == "loot":
            label_loot = target_obj.get("label", "").lower() if target_obj.get("label") else ""
            if "cassaforte" in label_loot:
                if not gs.flags.get("skyscraper_terminal_hacked", False):
                    self._wbark(get_bark(EXPLORE_BARKS, "safe_needs_echo"))
                    gs.flash("BLOCCO ELETTRONICO", 80)
                elif not gs.flags.get("safe_breached", False):
                    if active_char.name == "Rivet":
                        _SAFE_SOGLIA = 10
                        rivet_forza_safe = gs.Rivet.stats.forza if gs.Rivet else 0
                        if rivet_forza_safe < _SAFE_SOGLIA:
                            gap = _SAFE_SOGLIA - rivet_forza_safe
                            self._wbark(get_bark(EXPLORE_BARKS, "safe_needs_rivet"))
                            gs.flash(f"FORZA INSUFFICIENTE (-{gap}) — Aumenta il livello di Rivet!", 120)
                            return
                        else:
                            gs.flags["safe_breached"] = True
                            if hasattr(gs, "quest_sys"):
                                gs.quest_sys.notify_flag_set("safe_breached", True)

                            target_obj["looted"] = True
                        gs.looted.add(tuple(target_obj["pos"]))

                        loot_sys = gs.get_system(LootSystem)
                        if loot_sys:
                            ctx = LootContext(zone_type="cassaforte")
                            drops = loot_sys.generate_loot(ctx)
                            for item in drops:
                                gs.Rivet.inventory.add_item(item.clone())
                            nomi = ", ".join(it.name for it in drops)
                            self._wbark(get_bark(EXPLORE_BARKS, "safe_success"))
                            gs.flash(f"CASSAFORTE SFONDATA — {nomi} acquisiti!", 150)
                        else:
                            rifle = get_item_proto("heavy_rifle_01")
                            if rifle:
                                gs.Rivet.inventory.add_item(rifle.clone())
                            self._wbark(get_bark(EXPLORE_BARKS, "safe_success"))
                            gs.flash("CASSAFORTE SFONDATA — Fucile d'Assalto acquisito!", 150)
                    else:
                        self._wbark(get_bark(EXPLORE_BARKS, "safe_needs_rivet"))
                        gs.flash("Serve Rivet per sfondarla!", 80)
                else:
                    self._wbark(get_bark(EXPLORE_BARKS, "safe_empty", char=active_char.name))
            else:
                self._collect_loot(target_obj, active_char)
        else:
            _safe_spot = next(
                (s for s in getattr(self, '_dynamic_loot_spots', [])
                 if "cassaforte" in (s.get("label", "") or "").lower()),
                None
            )
            def _rivet_near_safe():
                if _safe_spot is None:
                    return False
                sp = _safe_spot["pos"]
                return math.hypot(gs.p1[0] - sp[0], gs.p1[1] - sp[1]) <= 2.0
            if (gs.flags.get("skyscraper_terminal_hacked", False)
                    and not gs.flags.get("safe_breached", False)):
                if _rivet_near_safe():
                    _SAFE_SOGLIA = 10
                    rivet_forza_safe = gs.Rivet.stats.forza if gs.Rivet else 0
                    if rivet_forza_safe < _SAFE_SOGLIA:
                        gap = _SAFE_SOGLIA - rivet_forza_safe
                        self._wbark(get_bark(EXPLORE_BARKS, "safe_needs_rivet"))
                        gs.flash(f"FORZA INSUFFICIENTE (-{gap}) — Aumenta il livello di Rivet!", 120)
                        return
                    gs.flags["safe_breached"] = True
                    if hasattr(gs, "quest_sys"):
                        gs.quest_sys.notify_flag_set("safe_breached", True)
                    loot_sys = gs.get_system(LootSystem)
                    if loot_sys:
                        ctx = LootContext(zone_type="cassaforte")
                        drops = loot_sys.generate_loot(ctx)
                        for item in drops:
                            gs.Rivet.inventory.add_item(item.clone())
                        nomi = ", ".join(it.name for it in drops)
                        self._wbark(get_bark(EXPLORE_BARKS, "safe_success"))
                        gs.flash(f"CASSAFORTE APERTA — {nomi} acquisiti!", 150)
                    else:
                        rifle = get_item_proto("heavy_rifle_01")
                        if rifle:
                            gs.Rivet.inventory.add_item(rifle.clone())
                        self._wbark(get_bark(EXPLORE_BARKS, "safe_success"))
                        gs.flash("CASSAFORTE APERTA — Fucile d'Assalto acquisito!", 150)
                    return

            if gs.flags.get("Q01_done", False) and not gs.flags.get("landmine_collected", False):
                import math as _math
                for mine_pos in MINE_SPOTS:
                    if tuple(mine_pos) in getattr(self, "_mines_gone", set()):
                        continue
                    dist_r = _math.hypot(p1_pos[0] - mine_pos[0], p1_pos[1] - mine_pos[1])
                    if dist_r <= 2.5:
                        import random as _rnd
                        self._mines_gone.add(tuple(mine_pos))

                        if _rnd.random() < 0.30:
                            dmg_r = _rnd.randint(15, 35)
                            dmg_e = _rnd.randint(5, 20)
                            if gs.Rivet: gs.Rivet.stats.hp = max(0, gs.Rivet.stats.hp - dmg_r)
                            if gs.Echo:  gs.Echo.stats.hp  = max(0, gs.Echo.stats.hp  - dmg_e)
                            gs.modify_ethics(-1)
                            self._wbark(get_bark(EXPLORE_BARKS, "mine_fail"))
                            gs.flash(f"ERRORE DISINNESCO!  Etica {gs.ethics:+d}", 140)
                        else:
                            mine_proto = get_item_proto("landmine_01")
                            if mine_proto and gs.Rivet:
                                gs.Rivet.inventory.add_item(mine_proto.clone())
                                if gs.bus:
                                    gs.bus.publish(EventType.ITEM_PICKUP, {"item_id": "landmine_01"})
                            gs.flags["landmine_collected"] = True
                            if hasattr(gs, "quest_sys"):
                                gs.quest_sys.notify_flag_set("landmine_collected", True)
                            self._wbark(get_bark(EXPLORE_BARKS, "mine_success"))
                            gs.flash("MINA MILITARE RECUPERATA", 130)
                        return

            if (gs.flags.get("power_plant_door_blown", False)
                    and not gs.flags.get("power_panel_activated", False)):
                import math as _math
                dist_echo_panel = _math.hypot(p2_pos[0] - wd.POWER_PANEL_SPOT[0],
                                               p2_pos[1] - wd.POWER_PANEL_SPOT[1])
                dist_rivet_panel = _math.hypot(p1_pos[0] - wd.POWER_PANEL_SPOT[0],
                                                p1_pos[1] - wd.POWER_PANEL_SPOT[1])
                if dist_echo_panel <= 2.0:
                    gs.flags["power_panel_activated"] = True
                    if hasattr(gs, "quest_sys"):
                        gs.quest_sys.notify_flag_set("power_panel_activated", True)
                    self._wbark(get_bark(EXPLORE_BARKS, "quest_panel_echo"))
                    gs.flash("CENTRALE RIATTIVATA — Ora hackerate la Torre Radar!", 160)
                    return
                elif dist_rivet_panel <= 2.0:
                    self._wbark(get_bark(EXPLORE_BARKS, "quest_panel_rivet"))
                    gs.flash("Solo Echo può attivare il pannello elettrico!", 100)
                    return

            if not gs.flags.get("factory_inner_door_breached", False):
                try:
                    _, (_, dcode, _) = cur_district(gs.p1)
                except Exception:
                    dcode = ""
                if dcode == "F":
                    gs.breach_door({"pos": (0, 0)}, district_code="F")
                    self._wbark(get_bark(EXPLORE_BARKS, "quest_door_factory"))
                    gs.flash("PORTA INTERNA SFONDATA — Elimina gli infetti!", 150)
                    return

            active = gs.Rivet if gs.player is gs.Rivet else gs.Echo
            self._wbark(get_bark(EXPLORE_BARKS, "nothing_here", char=active.name))

    def _restore_dropped_spots_from_save(self):
        """
        Reinserisce in _dynamic_loot_spots gli oggetti lasciati a terra
        nel salvataggio corrente (gs.dropped_spots).
        """
        gs = GameManager.get_instance()
        saved = getattr(gs, "dropped_spots", [])
        if not saved:
            return
        existing_positions = {
            tuple(s["pos"]) for s in self._dynamic_loot_spots
            if s.get("zone_type") == "dropped"
        }
        for spot in saved:
            if tuple(spot["pos"]) not in existing_positions:
                self._dynamic_loot_spots.append(spot)

    def _apply_breached_doors_from_flags(self):
        """
        Ripristina fisicamente lo stato delle porte dopo il caricamento della mappa.
        Senza questo metodo, le porte salvate come 'sfondabili' nei flags
        rimangono fisicamente chiuse (collision_cells intatte) dopo un load.
        """
        gs = GameManager.get_instance()
        if not hasattr(gs, "flags") or not self.maps:
            return

        flags = gs.flags

        for m in self.maps:
            offset_tx = round(m.offset_x / MAP_TILE_PX)
            offset_ty = round(m.offset_y / MAP_TILE_PX)

            for door in m.door_labels:
                if door.get("breached"):
                    for cell in door.get("collision_cells", []):
                        m.collision_cells.discard(cell)
                    continue

                dx, dy = door["pos"]
                flag_key = f"door_breached_{dx}_{dy}"
                if flags.get(flag_key, False):
                    door["breached"] = True
                    for cell in door.get("collision_cells", []):
                        m.collision_cells.discard(cell)
                    continue

                gx = dx + offset_tx
                gy = dy + offset_ty
                if 55 <= gx <= 70 and 50 <= gy <= 63:
                    if flags.get("skyscraper_door_opened", False) or flags.get("skyscraper_terminal_hacked", False):
                        door["breached"] = True
                        for cell in door.get("collision_cells", []):
                            m.collision_cells.discard(cell)

            if flags.get("power_plant_door_blown", False):
                for mine_door in m.mine_door_labels:
                    if not mine_door.get("blown"):
                        mine_door["blown"] = True
                    for cell in mine_door.get("collision_cells", []):
                        m.collision_cells.discard(cell)

    def _find_nearby_door(self, p1_pos: tuple, p2_pos: tuple):
        """Restituisce la prima porta non sfondata entro 2 tile da p1 o p2, o None."""
        import math
        if not hasattr(self, "maps"):
            return None
        for m in self.maps:
            for door in m.door_labels:
                if door["breached"]:
                    continue
                dx, dy = door["pos"]
                offset_tx = round(m.offset_x / MAP_TILE_PX)
                offset_ty = round(m.offset_y / MAP_TILE_PX)
                gx = dx + offset_tx
                gy = dy + offset_ty
                for pos in (p1_pos, p2_pos):
                    if math.hypot(pos[0] - gx, pos[1] - gy) <= 2.5:
                        return (door, m)
        return None

    def _try_breach_door(self, door_ref: tuple):
        """Tenta di sfondare la porta. Controlla stat Forza di Rivet."""
        gs = GameManager.get_instance()
        door, m = door_ref

        rivet_forza = gs.Rivet.stats.forza if gs.Rivet else 0
        soglia = door["strength_threshold"]

        _SKY_X0, _SKY_X1 = 55, 70
        _SKY_Y0, _SKY_Y1 = 50, 63

        offset_tx = round(m.offset_x / MAP_TILE_PX)
        offset_ty = round(m.offset_y / MAP_TILE_PX)
        gx = door["pos"][0] + offset_tx
        gy = door["pos"][1] + offset_ty

        _door_in_skyscraper = (_SKY_X0 <= gx <= _SKY_X1 and _SKY_Y0 <= gy <= _SKY_Y1)

        if _door_in_skyscraper:
            if not gs.flags.get("skyscraper_terminal_hacked", False):
                self._wbark(get_bark(EXPLORE_BARKS, "door_needs_echo"))
                gs.flash("BLOCCO ELETTRONICO", 100)
            return

        quest_bypass = gs.flags.get("can_breach_doors", False) if hasattr(gs, "flags") else False

        if quest_bypass or rivet_forza >= soglia:
            door["breached"] = True
            for cell in door["collision_cells"]:
                m.collision_cells.discard(cell)

            nome_porta = door["label"]
            self._wbark(get_bark(EXPLORE_BARKS, "door_success"))
            gs.flash(f"PORTA SFONDATA — {door['label']}!", 120)

            try:
                _, (_, dcode, _) = cur_district(tuple(gs.p1))
            except Exception:
                dcode = ""
            gs.breach_door(door, district_code=dcode)
        else:
            gap = soglia - rivet_forza
            self._wbark(get_bark(EXPLORE_BARKS, "door_fail"))
            gs.flash(f"FORZA INSUFFICIENTE (-{gap}) — Aumenta il livello di Rivet!", 120)

    def _collect_loot(self, spot: dict, target_char):
        """Genera il loot e apre il menu. Mantiene in memoria gli oggetti se non presi tutti."""
        gs = GameManager.get_instance()
        spot_pos = tuple(spot["pos"])

        if not hasattr(gs, "partial_loot"):
            gs.partial_loot = {}

        if spot.get("zone_type") == "dropped":
            items = spot.get("items", [])
            gs.partial_loot[spot_pos] = items
        elif spot_pos in gs.partial_loot:
            items = gs.partial_loot[spot_pos]
        else:
            ctx = LootContext(zone_type=spot["zone_type"], source_type="map")
            loot_sys = gs.get_system(LootSystem)
            items = loot_sys.generate_loot(ctx)
            gs.partial_loot[spot_pos] = items

        if not items:
            self._wbark(get_bark(EXPLORE_BARKS, "nothing_here", char=target_char.name))
            spot["looted"] = True
            gs.looted.add(spot_pos)
            return

        self._current_loot_stash = items
        self._in_loot_menu = True
        self._loot_cursor = 0
        self._current_loot_spot = spot
        self._loot_target_idx = 0

        label_zona = spot.get('label', 'questa zona')
        self._wbark(get_bark(EXPLORE_BARKS, "found_loot_stash"))

    def _hack(self):
        gs = GameManager.get_instance()
        import math

        p1_pos = tuple(gs.p1)
        p2_pos = tuple(gs.p2)

        best_term = None
        best_dist = 999
        best_char = None

        all_terminals = list(TERMINALS)

        for term in all_terminals:
            t_pos = tuple(term)
            for char_name, pos in [("Rivet", p1_pos), ("Echo", p2_pos)]:
                d = math.hypot(pos[0] - t_pos[0], pos[1] - t_pos[1])
                if d <= 2.0 and d < best_dist:
                    best_dist = d
                    best_term = term
                    best_char = char_name

        if best_term:
            if best_char == "Rivet":
                self._wbark(get_bark(EXPLORE_BARKS, "terminal_rivet_fail"))
                gs.flash("SOLO ECHO PUÒ HACKERARE", 80)
            else:
                _RADAR_TOWER     = (162, 31)
                _SKYSCRAPER_TERM = (61, 56)
                _CENTRAL_TERM    = (171, 103)

                if best_term == _RADAR_TOWER:
                    if not gs.flags.get("power_panel_activated", False):
                        self._wbark(get_bark(EXPLORE_BARKS, "terminal_no_power"))
                        gs.flash("ERRORE: Centrale Offline!", 100)
                        return
                    ok, reason = gs.hack_sys.can_hack(_RADAR_TOWER)
                    if not ok:
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash(reason, 100)
                        return
                    if not gs.activate_terminal(_RADAR_TOWER):
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash("Terminale non attivabile.", 80)
                        return

                elif best_term == _SKYSCRAPER_TERM:
                    if gs.flags.get("skyscraper_terminal_hacked", False):
                        self._wbark(get_bark(EXPLORE_BARKS, "terminal_already_hacked"))
                        gs.flash("Terminale già sbloccato.", 80)
                        return
                    ok, reason = gs.hack_sys.can_hack(_SKYSCRAPER_TERM)
                    if not ok:
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash(reason, 100)
                        return
                    if not gs.activate_terminal(_SKYSCRAPER_TERM):
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash("Terminale non attivabile.", 80)
                        return

                elif best_term == _CENTRAL_TERM:
                    _door_done  = gs.flags.get("factory_inner_door_breached", False)
                    _kills_done = False
                    if gs.quest_sys:
                        q03 = gs.quest_sys._states.get("Q03_fabbrica")
                        if q03:
                            obj_kills = q03.get_objective("Q03_o2")
                            _kills_done = obj_kills.completed if obj_kills else False
                    if not _door_done:
                        self._wbark(get_bark(EXPLORE_BARKS, "terminal_need_door"))
                        gs.flash("Prima sfonda la porta interna!", 100)
                        return
                    if not _kills_done:
                        self._wbark(get_bark(EXPLORE_BARKS, "terminal_need_clear"))
                        gs.flash("Elimina prima tutti gli infetti!", 100)
                        return
                    ok, reason = gs.hack_sys.can_hack(_CENTRAL_TERM)
                    if not ok:
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash(reason, 100)
                        return
                    if not gs.activate_terminal(_CENTRAL_TERM):
                        self._wbark(get_bark(EXPLORE_BARKS, "system_locked"))
                        gs.flash("Terminale non attivabile.", 80)
                        return

                else:
                    self._wbark(get_bark(EXPLORE_BARKS, "terminal_dead"))
                    gs.flash("Terminale non identificato.", 80)
        else:
            self._wbark(get_bark(EXPLORE_BARKS, "no_terminal_nearby"))

    def _start_dialogue(self, npc: dict):
        """Avvia un dialogo strutturato via DialogueManager.

        Se l'NPC ha un albero registrato in DialogueManager._TREES lo usa;
        altrimenti cade sul comportamento legacy (linea random + rep +3).
        """
        gs = GameManager.get_instance()
        dm = gs.get_system(DialogueManager)

        npc_name = npc["name"]
        root_node = dm.start_dialogue(npc_name) if dm else None

        if root_node is not None:
            self._dialogue_node   = root_node
            self._dialogue_cursor = 0
            self._dialogue_npc    = npc_name
        else:
            lines = npc.get("lines", [])
            line = random.choice(lines) if lines else "Non ha molto da dire."

            self._wbark(f"{npc_name}: '{line}'")

    def _get_closest_character(self, target_pos):
        """Restituisce il personaggio più vicino alle coordinate target."""
        gs = GameManager.get_instance()
        import math
        d_rivet = math.hypot(gs.p1[0] - target_pos[0], gs.p1[1] - target_pos[1])
        d_echo  = math.hypot(gs.p2[0] - target_pos[0], gs.p2[1] - target_pos[1])
        return gs.Rivet if d_rivet <= d_echo else gs.Echo

    def _fight_npc(self, npc):
        gs = GameManager.get_instance()
        faction = npc.get("faction", "zombie")
        if faction == "zombie":
            gs.start_battle(npc)
            return

        npc_name = npc.get("name", "").lower()
        is_standby = False

        if hasattr(gs, "flags"):
            for key, val in gs.flags.items():
                if npc_name in key and "quest_active" in key and val is True:
                    is_standby = True
                    break

        if is_standby:
            self._start_dialogue_at(npc, "root_pragmatic")
            return

        npc_pos = npc.get("pos", (0, 0))

        if hasattr(self, '_get_closest_character'):
            closest_char = self._get_closest_character(npc_pos)
            role = "Rivet" if closest_char is gs.Rivet else "Echo"
        else:
            role = "Rivet" if (gs.player is gs.Rivet or gs.player is None) else "Echo"
            closest_char = gs.Rivet if role == "Rivet" else gs.Echo

        if role == "Rivet":
            tone_options = [
                ("Minaccioso",  "root_aggressive"),
                ("Pragmatico",  "root_pragmatic"),
                ("Attacca",     "ATTACK"),
                ("Ignora",      "IGNORE"),
            ]
        else:
            tone_options = [
                ("Empatico",    "root_empathic"),
                ("Diplomatico", "root_diplomatic"),
                ("Attacca",     "ATTACK"),
                ("Ignora",      "IGNORE"),
            ]

        self._in_predialogue      = True
        self._predialogue_npc     = npc
        self._predialogue_options = tone_options
        self._predialogue_char    = closest_char
        self._predialogue_cursor  = 0


    def _check_mine_stepped(self):
        """Controlla se i giocatori calpestano una mina attiva, facendola esplodere."""
        gs = GameManager.get_instance()
        import math

        for mp in MINE_SPOTS:
            if tuple(mp) in getattr(self, "_mines_gone", set()):
                continue

            for char_obj, pos in [(gs.Rivet, gs.p1), (gs.Echo, gs.p2)]:
                if char_obj:
                    distanza = math.hypot(pos[0] - mp[0], pos[1] - mp[1])

                    if distanza <= 1.2:
                        self._mines_gone.add(tuple(mp))

                        import random
                        dmg = random.randint(25, 45)
                        char_obj.stats.hp = max(0, char_obj.stats.hp - dmg)
                        gs.modify_ethics(-1)
                        gs.flash(f"MINA ESPLOSA!  Etica {gs.ethics:+d}", 120)

                        if gs.audio:
                            gs.audio.play_sound("explosion")

                        self._wbark(get_bark(EXPLORE_BARKS, "mine_stepped", char=char_obj.name))

    def update(self):
        if not self._maps_loaded:
            self._load_city_and_collisions()

        gs = GameManager.get_instance()
        self._anim += 0.03

        _now = pygame.time.get_ticks()

        if not hasattr(self, '_last_input_time'):
            self._last_input_time = _now

        if _now - self._last_input_time > 30000:
            import random
            if random.random() < 0.01:
                self._wbark(get_bark(EXPLORE_BARKS, "idle_waiting"))
                self._last_input_time = _now

        if _now - getattr(self, "_last_hp_bark_time", 0) > 20000:
            if gs.Rivet and gs.Rivet.stats.hp > 0 and (gs.Rivet.stats.hp / max(1, gs.Rivet.stats.max_hp)) < 0.25:
                self._wbark(get_bark(EXPLORE_BARKS, "low_hp_rivet"))
                self._last_hp_bark_time = _now
            elif gs.Echo and gs.Echo.stats.hp > 0 and (gs.Echo.stats.hp / max(1, gs.Echo.stats.max_hp)) < 0.25:
                self._wbark(get_bark(EXPLORE_BARKS, "low_hp_echo"))
                self._last_hp_bark_time = _now

        if gs.Rivet and gs.Echo and gs.ethics <= -10:
            gs.set_gameover("Il vostro legame si è spezzato irrimediabilmente. La missione è fallita.")
            return


        if getattr(self, '_dialogue_node', None) is not None or getattr(self, '_in_predialogue', False):
            return

        if not self._maps_loaded:
            return

        if self._rain_active:
            for drop in self._rain_drops:
                drop.update()
            import random
            if random.random() < 0.0005:
                self._wbark(get_bark(EXPLORE_BARKS, "raining"))

        if gs.Rivet and gs.Echo:
            if not gs.Rivet.is_alive() or not gs.Echo.is_alive():
                fallen = "Rivet" if not gs.Rivet.is_alive() else "Echo"
                caduto = "caduto" if not gs.Rivet.is_alive() else "caduta"
                gs.set_gameover(f"{fallen} è {caduto} durante l'esplorazione. La missione è fallita.")
                return
            if gs.ethics <= -10:
                gs.set_gameover("Il vostro legame si è spezzato irrimediabilmente. La missione è fallita.")
                return


        movement = gs.get_system(MovementSystem)
        if not movement:
            return

        raw_keys = pygame.key.get_pressed()

        blocked_keys = set()

        if getattr(self, '_in_loot_menu', False) or getattr(self, '_in_drop_menu', False) or getattr(self, '_in_use_menu', False):
            blocked_keys.update([
                pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT
            ])

        st1 = movement._players.get("p1") or movement._players.get("Rivet")
        st2 = movement._players.get("p2") or movement._players.get("Echo")

        if st1 and st2:
            dx = st1.pixel_x - st2.pixel_x
            dy = st1.pixel_y - st2.pixel_y

            MAX_DX = self.MAP_VIEW_W - 140
            MAX_DY = self.MAP_VIEW_H - 140

            show_warning = False

            if dx > MAX_DX:
                blocked_keys.update([pygame.K_d, pygame.K_LEFT])
                show_warning = True
            elif dx < -MAX_DX:
                blocked_keys.update([pygame.K_a, pygame.K_RIGHT])
                show_warning = True

            if dy > MAX_DY:
                blocked_keys.update([pygame.K_s, pygame.K_UP])
                show_warning = True
            elif dy < -MAX_DY:
                blocked_keys.update([pygame.K_w, pygame.K_DOWN])
                show_warning = True

            if show_warning and not getattr(self, '_was_warning_active', False):
                self._wbark(get_bark(EXPLORE_BARKS, "coop_too_far"))
            self._was_warning_active = show_warning

        class FilteredKeys:
            def __getitem__(self, key):
                if key in blocked_keys:
                    return False
                return raw_keys[key]

        results = movement.update(FilteredKeys())

        if gs.flags.get("skyscraper_terminal_hacked", False) and not gs.flags.get("skyscraper_door_opened", False):
            for m in self.maps:
                for door in m.door_labels:
                    dx, dy = door["pos"]
                    gx = dx + round(m.offset_x / MAP_TILE_PX)
                    gy = dy + round(m.offset_y / MAP_TILE_PX)
                    if 55 <= gx <= 70 and 50 <= gy <= 63:
                        door["breached"] = True
                        for cell in door["collision_cells"]:
                            m.collision_cells.discard(cell)
                        gs.flags["skyscraper_door_opened"] = True
                        self._wbark(get_bark(EXPLORE_BARKS, "auto_door_open"))
                        gs.flash("PORTA APERTA — Passaggio sbloccato!", 120)
                        break

        _now_ms = pygame.time.get_ticks()
        _dt_sec = (_now_ms - getattr(self, "_acid_last_tick_ms", _now_ms)) / 1000.0
        self._acid_last_tick_ms = _now_ms
        self._apply_acid_damage(_dt_sec)
        self._tick_mine_timer(_dt_sec)
        self._check_mine_stepped()

        DIR_STATE = {
            "down":  ("walk_dn", "idle_dn"),
            "up":    ("walk_up", "idle_up"),
            "left":  ("walk_l",  "idle_l"),
            "right": ("walk_r",  "idle_r"),
        }

        for r in results:
            pid = r["player"]
            sp  = gs.Rivet_sprite if pid in ("Rivet", "p1") else gs.Echo_sprite
            if not sp:
                continue

            direction = r["last_dir"]
            is_moving = r["is_moving"]
            walk_st, idle_st = DIR_STATE.get(direction, ("walk_dn", "idle_dn"))

            sp.set_state(walk_st if is_moving else idle_st)
            sp.update(16.6)

            if r["moved"]:
                col, row = r["col"], r["row"]
                if pid in ("Rivet", "p1"):
                    gs.p1 = [col, row]
                    player_id_event = "p1"
                elif pid in ("Echo", "p2"):
                    gs.p2 = [col, row]
                    player_id_event = "p2"
                else:
                    continue

                if gs.bus:
                    gs.bus.publish(EventType.PLAYER_MOVED, {
                        "player_id": player_id_event,
                        "position": (col, row),
                        "reps": getattr(gs, "reps", 0),
                    })

                    if pid in ("Rivet", "p1"):

                        _, (_, dcode, _) = cur_district(gs.p1)
                        if getattr(self, "_last_zone_id", None) != dcode:
                            self._last_zone_id = dcode
                            gs.bus.publish(EventType.ZONE_ENTERED, {"zone_id": dcode})

                        p1_pos = (gs.p1[0], gs.p1[1])
                        lista_loot = getattr(self, '_dynamic_loot_spots', [])
                        edificio_vicino = near_obj(p1_pos, lista_loot)

                        label_edificio = edificio_vicino.get("label") if edificio_vicino else None

                        _SKYSCRAPER_X0, _SKYSCRAPER_X1 = 55, 70
                        _SKYSCRAPER_Y0, _SKYSCRAPER_Y1 = 50, 63
                        if _SKYSCRAPER_X0 <= p1_pos[0] <= _SKYSCRAPER_X1 and _SKYSCRAPER_Y0 <= p1_pos[1] <= _SKYSCRAPER_Y1:
                            label_edificio = "Grattacielo"

                        if getattr(self, "_last_building_label", None) != label_edificio:
                            self._last_building_label = label_edificio
                            if label_edificio:
                                gs.bus.publish(EventType.ZONE_ENTERED, {"zone_id": label_edificio})
                                self._wbark(get_bark(EXPLORE_BARKS, "new_location"))

    def _apply_acid_damage(self, dt_sec: float):
        """
        Controlla se p1 (Rivet) e/o p2 (Echo) si trovano su una acid_tile.
        Se sì, accumula il tempo trascorso e applica ACID_DMG_AMOUNT HP
        ogni ACID_DMG_INTERVAL secondi finché il personaggio resta sulla tile.
        Resetta il timer se il personaggio lascia la piscina.
        """
        gs = GameManager.get_instance()

        for player_id, char_obj, timer_attr in (
            ("p1", gs.Rivet, "_acid_timer_p1"),
            ("p2", gs.Echo,  "_acid_timer_p2"),
        ):
            if char_obj is None:
                continue

            pos = gs.p1 if player_id == "p1" else gs.p2
            gtx, gty = int(pos[0]), int(pos[1])

            on_acid = False
            for m in self.maps:
                offset_tx = round(m.offset_x / MAP_TILE_PX)
                offset_ty = round(m.offset_y / MAP_TILE_PX)
                local_tx = gtx - offset_tx
                local_ty = gty - offset_ty

                if 0 <= local_tx < m.w and 0 <= local_ty < m.h:
                    if (local_tx, local_ty) in m.acid_tiles:
                        on_acid = True
                    break

            if on_acid:
                current_timer = getattr(self, timer_attr) + dt_sec
                setattr(self, timer_attr, current_timer)

                if current_timer >= self.ACID_DMG_INTERVAL:
                    setattr(self, timer_attr, 0.0)
                    new_hp = max(0, char_obj.stats.hp - self.ACID_DMG_AMOUNT)
                    char_obj.stats.hp = new_hp
                    import random
                    if random.random() < 0.20:
                        self._wbark(get_bark(EXPLORE_BARKS, "acid_damage"))
            else:
                setattr(self, timer_attr, 0.0)

    def _tick_mine_timer(self, dt_sec: float):
        if not getattr(self, "_mine_placed", False):
            return

        gs = GameManager.get_instance()
        self._mine_timer -= dt_sec

        remaining = self._mine_timer
        if 0.0 < remaining <= 1.0:
            gs.flash(f"MINA — ESPLOSIONE IN {remaining:.1f}s!", 20)
        elif 1.0 < remaining <= 2.0:
            gs.flash(f"MINA — ESPLOSIONE IN {remaining:.0f}s...", 30)

        if self._mine_timer > 0.0:
            return

        self._mine_placed = False

        _BLAST_X, _BLAST_Y = MINE_PLACEMENT_SPOT
        _BLAST_RADIUS = 3

        _PLANT_X0, _PLANT_X1 = 168, 185
        _PLANT_Y0, _PLANT_Y1 = 135, 148

        def _inside_plant(pos):
            return _PLANT_X0 <= pos[0] <= _PLANT_X1 and _PLANT_Y0 <= pos[1] <= _PLANT_Y1

        damage_dealt = False
        for char, pos in [(gs.Rivet, gs.p1), (gs.Echo, gs.p2)]:
            if char:
                if _inside_plant(pos):
                    char.stats.hp = 0
                    self._wbark(get_bark(EXPLORE_BARKS, "trapped_in_explosion"))
                    damage_dealt = True
                elif (abs(pos[0] - _BLAST_X) <= _BLAST_RADIUS and
                      abs(pos[1] - _BLAST_Y) <= _BLAST_RADIUS):
                    import math
                    dist = math.hypot(pos[0] - _BLAST_X, pos[1] - _BLAST_Y)
                    dmg = max(10, int(60 / (dist + 1)))
                    char.stats.hp = max(0, char.stats.hp - dmg)
                    self._wbark(get_bark(EXPLORE_BARKS, "explosion_shockwave", char=char.name))
                    damage_dealt = True

        if damage_dealt:
            gs.modify_ethics(-1)
            gs.flash(f"ESPLOSIONE — Etica {gs.ethics:+d}", 80)

        if gs.audio:
            gs.audio.play_sound("explosion")

        if hasattr(self, "maps"):
            for m in self.maps:
                off_tx = round(m.offset_x / MAP_TILE_PX)
                off_ty = round(m.offset_y / MAP_TILE_PX)
                for dx in range(-1, 2):
                    lx = _BLAST_X - off_tx + dx
                    ly = _BLAST_Y - off_ty
                    if (lx, ly) in m.collision_cells:
                        m.collision_cells.discard((lx, ly))
                for mine_door in m.mine_door_labels:
                    if not mine_door.get("blown"):
                        mine_door["blown"] = True
                    for cell in mine_door.get("collision_cells", []):
                        m.collision_cells.discard(cell)

        if not gs.flags.get("power_plant_door_blown", False):
            gs.flags["power_plant_door_blown"] = True
            if hasattr(gs, "quest_sys"):
                gs.quest_sys.notify_flag_set("power_plant_door_blown", True)

        self._wbark(get_bark(EXPLORE_BARKS, "explosion_door_open"))
        gs.flash("ESPLOSIONE — Portello distrutto! Entrate nella Centrale!", 200)

    def draw(self, surf: Surface):
        if not self._maps_loaded:
            return

        gs = GameManager.get_instance()
        fn = self.fonts
        surf.fill(BG)

        if not hasattr(self, '_prev_ethics'):
            self._prev_ethics = gs.ethics
        if not hasattr(self, '_prev_reps'):
            self._prev_reps = gs.reps.copy()

        import random

        if gs.ethics != self._prev_ethics:
            diff = gs.ethics - self._prev_ethics

            if random.random() < 0.40:
                key = "ethics_up" if diff > 0 else "ethics_down"
                self._wbark(get_bark(EXPLORE_BARKS, key))

            self._prev_ethics = gs.ethics

        for faction, rep in gs.reps.items():
            old_rep = self._prev_reps.get(faction, rep)
            if rep != old_rep:
                diff = rep - old_rep

                if random.random() < 0.50:
                    key = "rep_allied" if diff > 0 else "rep_hostile"
                    self._wbark(get_bark(EXPLORE_BARKS, key, faction=faction.capitalize()))

                self._prev_reps[faction] = rep

        MX = 8
        MY = 8

        viewport = pygame.Surface((self.MAP_VIEW_W, self.MAP_VIEW_H))
        viewport.fill((20, 30, 20))


        _ms_cam = gs.get_system(_MSCam)

        st1 = _ms_cam._players.get("p1") or _ms_cam._players.get("Rivet") if _ms_cam else None
        st2 = _ms_cam._players.get("p2") or _ms_cam._players.get("Echo") if _ms_cam else None

        if st1 and st2:
            follow_x = (st1.pixel_x + st2.pixel_x) / 2
            follow_y = (st1.pixel_y + st2.pixel_y) / 2
        elif st1:
            follow_x = st1.pixel_x
            follow_y = st1.pixel_y
        else:
            follow_x = gs.p1[0] * MAP_TILE_PX + MAP_TILE_PX / 2
            follow_y = gs.p1[1] * MAP_TILE_PX + MAP_TILE_PX / 2

        cam_x = int(follow_x) - self.MAP_VIEW_W // 2
        cam_y = int(follow_y) - self.MAP_VIEW_H // 2

        cam_x = max(0, min(self.city_w - self.MAP_VIEW_W, cam_x))
        cam_y = max(0, min(self.city_h - self.MAP_VIEW_H, cam_y))

        for m in self.maps:
            draw_x = m.offset_x - cam_x
            draw_y = m.offset_y - cam_y

            img_w = m.bg_surface.get_width()
            img_h = m.bg_surface.get_height()

            if (draw_x + img_w < 0 or draw_x > self.MAP_VIEW_W or
                    draw_y + img_h < 0 or draw_y > self.MAP_VIEW_H):
                continue
            viewport.blit(m.bg_surface, (draw_x, draw_y))

        def grid_to_px(col, row):
            sx = int(col * MAP_TILE_PX + MAP_TILE_PX / 2) - cam_x
            sy = int(row * MAP_TILE_PX + MAP_TILE_PX / 2) - cam_y
            return sx, sy

        for spot in self._dynamic_loot_spots:
            if tuple(spot["pos"]) not in gs.looted:
                sx, sy = grid_to_px(spot["pos"][0], spot["pos"][1])
                if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                    color = (100, 200, 255)
                    if spot["zone_type"] in ("trash", "spazzatura"): color = (100, 120, 100)
                    elif spot["zone_type"] in ("crate", "scatolone"): color = (180, 140, 60)

                    pygame.draw.circle(viewport, color, (sx, sy), 5)
                    pygame.draw.circle(viewport, WHITE, (sx, sy), 5, 1)

        import math

        if gs.flags.get("power_plant_door_blown", False) and not gs.flags.get("power_panel_activated", False):
            sx, sy = grid_to_px(wd.POWER_PANEL_SPOT[0], wd.POWER_PANEL_SPOT[1])
            if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                pulse = abs(math.sin(self._anim * 3)) * 4
                pygame.draw.circle(viewport, CYAN, (sx, sy), int(8 + pulse), 2)
                pygame.draw.circle(viewport, WHITE, (sx, sy), 3)

        if gs.flags.get("power_panel_activated", False) and not gs.flags.get("radar_tower_hacked", False):
            _RADAR_TOWER = (162, 31)
            sx, sy = grid_to_px(_RADAR_TOWER[0], _RADAR_TOWER[1])
            if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                pulse = abs(math.sin(self._anim * 3)) * 4
                pygame.draw.circle(viewport, MAGENTA, (sx, sy), int(8 + pulse), 2)
                pygame.draw.circle(viewport, WHITE, (sx, sy), 3)

        if not gs.flags.get("skyscraper_terminal_hacked", False):
            _SKYSCRAPER_TERM = (61, 56)
            sx, sy = grid_to_px(_SKYSCRAPER_TERM[0], _SKYSCRAPER_TERM[1])
            if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                pulse = abs(math.sin(self._anim * 3)) * 4
                pygame.draw.circle(viewport, MAGENTA, (sx, sy), int(8 + pulse), 2)
                pygame.draw.circle(viewport, WHITE, (sx, sy), 3)

        _door_done = gs.flags.get("factory_inner_door_breached", False)
        if _door_done and not gs.flags.get("factory_terminal_hacked", False):
            _CENTRAL_TERM = (171, 103)
            sx, sy = grid_to_px(_CENTRAL_TERM[0], _CENTRAL_TERM[1])
            if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                pulse = abs(math.sin(self._anim * 3)) * 4
                pygame.draw.circle(viewport, MAGENTA, (sx, sy), int(8 + pulse), 2)
                pygame.draw.circle(viewport, WHITE, (sx, sy), 3)

        _mine_collected = gs.flags.get("landmine_collected", False)
        _door_blown = gs.flags.get("power_plant_door_blown", False)
        _mine_active = getattr(self, "_mine_placed", False)

        if _mine_collected and not _door_blown and not _mine_active:
            sx, sy = grid_to_px(MINE_PLACEMENT_SPOT[0], MINE_PLACEMENT_SPOT[1])
            if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                pulse = abs(math.sin(self._anim * 3)) * 4
                pygame.draw.circle(viewport, ORANGE, (sx, sy), int(8 + pulse), 2)
                pygame.draw.circle(viewport, WHITE, (sx, sy), 3)

        if not hasattr(self, "_npc_cache"):
            self._npc_cache = {}

        for m in self.maps:
            for npc in m.mobs:
                npc_key = (npc.get("name", ""), tuple(npc["pos"]))
                if npc_key in gs.defeated_npcs:
                    continue

                sx, sy = grid_to_px(npc["pos"][0], npc["pos"][1])

                sx += m.offset_x
                sy += m.offset_y

                if 0 <= sx <= self.MAP_VIEW_W and 0 <= sy <= self.MAP_VIEW_H:
                    hostile = npc_is_hostile(npc, gs.reps)
                    fcol = RED if hostile else CYAN

                    npc_name = npc.get("name", "Unknown")
                    faction  = npc.get("faction", "")

                    cache_key = f"{faction}_{npc_name}"

                    if cache_key not in self._npc_cache:
                        asset_dir = str(__import__("game.paths", fromlist=["ASSETS_ROOT"]).ASSETS_ROOT)
                        if faction == "zombie":
                            folder = ZombieFactory.sprite_folder(npc_name)
                            char_folder = os.path.join("Character", "Zombie", folder)
                        else:
                            char_folder = os.path.join("Character", faction.capitalize(), npc_name)
                        frames = load_lpc_frames(asset_dir, char_folder, "idle", "down", 1)
                        self._npc_cache[cache_key] = frames[0] if frames else None

                    img = self._npc_cache.get(cache_key)

                    if img:
                        if img.get_size() == (64, 64) and img.get_at((0, 0)) == (255, 0, 0, 150):
                            pygame.draw.circle(viewport, fcol, (sx, sy), 6)
                            pygame.draw.circle(viewport, WHITE, (sx, sy), 6, 1)
                        else:
                            sw, sh = img.get_size()
                            draw_x = sx - sw // 2
                            draw_y = sy - sh + (sh // 2)
                            viewport.blit(img, (draw_x, draw_y))
                            shadow_w = max(sw // 2, 24)
                            shadow_surf = pygame.Surface((shadow_w, 12), pygame.SRCALPHA)
                            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, shadow_w, 12))
                            viewport.blit(shadow_surf, (sx - shadow_w // 2, draw_y + sh - 10))
                    else:
                        pygame.draw.circle(viewport, fcol, (sx, sy), 6)
                        pygame.draw.circle(viewport, WHITE, (sx, sy), 6, 1)

        _movement = gs.get_system(_MS)

        for pid, sp_attr in [("Rivet", "Rivet_sprite"), ("Echo", "Echo_sprite")]:
            sp = getattr(gs, sp_attr, None)
            if not sp:
                continue

            mv_st = _movement._players.get(pid) if _movement else None
            if mv_st is not None:
                sx = int(mv_st.pixel_x) - cam_x
                sy = int(mv_st.pixel_y) - cam_y
            else:
                pos = gs.p1 if pid == "Rivet" else gs.p2
                sx, sy = grid_to_px(pos[0], pos[1])

            img = sp.image
            if img:
                sw, sh = img.get_size()
                sprite_offset = sh // 5
                draw_x = sx - sw // 2
                draw_y = sy - sh + sprite_offset
                viewport.blit(img, (draw_x, draw_y))

                shadow_w = max(sw // 2, 24)
                shadow_surf = pygame.Surface((shadow_w, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, shadow_w, 12))
                viewport.blit(shadow_surf, (sx - shadow_w // 2, draw_y + sh - 10))

        if self._debug_collisions:
            for m in self.maps:
                for (tx, ty) in m.collision_cells:
                    rx = int(m.offset_x + tx * MAP_TILE_PX) - cam_x
                    ry = int(m.offset_y + ty * MAP_TILE_PX) - cam_y
                    rw = int(MAP_TILE_PX)
                    rh = int(MAP_TILE_PX)
                    if rx + rw < 0 or rx > self.MAP_VIEW_W: continue
                    if ry + rh < 0 or ry > self.MAP_VIEW_H: continue
                    dbg = pygame.Surface((rw, rh), pygame.SRCALPHA)
                    dbg.fill((255, 0, 0, 80))
                    viewport.blit(dbg, (rx, ry))
                    pygame.draw.rect(viewport, (255, 60, 60), (rx, ry, rw, rh), 1)
                for ic in m.icon_colliders:
                    irx = ic.rect.x - cam_x
                    iry = ic.rect.y - cam_y
                    irw, irh = ic.rect.w, ic.rect.h
                    if irx + irw < 0 or irx > self.MAP_VIEW_W: continue
                    if iry + irh < 0 or iry > self.MAP_VIEW_H: continue
                    if irw <= 0 or irh <= 0: continue
                    dbg = pygame.Surface((irw, irh), pygame.SRCALPHA)
                    dbg.fill((255, 140, 0, 100))
                    viewport.blit(dbg, (irx, iry))
                    pygame.draw.rect(viewport, (255, 200, 0), (irx, iry, irw, irh), 1)
                _ms_dbg = gs.get_system(_MSDbg)
            if _ms_dbg:
                r_px = int(_ms_dbg._coll_r)
                for st in _ms_dbg._players.values():
                    cx = int(st.pixel_x) - cam_x
                    cy = int(st.pixel_y) - cam_y
                    pygame.draw.circle(viewport, (0, 255, 255), (cx, cy), r_px, 2)
                    pygame.draw.circle(viewport, (0, 255, 255), (cx, cy), 3)

        overlay = build_light_overlay(self.maps, self.city_w, self.city_h, cam_x, cam_y, self.MAP_VIEW_W, self.MAP_VIEW_H)
        viewport.blit(overlay, (0, 0))

        _bubble_positions: dict[str, tuple[int, int]] = {}
        _ms_bubble = gs.get_system(_MSBubble)
        for _pid, _sp_attr in [("Rivet", "Rivet_sprite"), ("Echo", "Echo_sprite")]:
            _sp = getattr(gs, _sp_attr, None)
            if not _sp:
                continue
            _mv_b = _ms_bubble._players.get(_pid) if _ms_bubble else None
            if _mv_b is not None:
                _bsx = int(_mv_b.pixel_x) - cam_x
                _bsy = int(_mv_b.pixel_y) - cam_y
            else:
                _bpos = gs.p1 if _pid == "Rivet" else gs.p2
                _bsx, _bsy = grid_to_px(_bpos[0], _bpos[1])
            _bubble_positions[_pid] = (_bsx, _bsy)
        self._bubbles.draw(viewport, fn["sm"], _bubble_positions)


        if getattr(self, '_show_coop_warning', False):
            warn_msg = "⚠ ATTENZIONE: Non allontanatevi troppo! La sopravvivenza dipende dall'unità."
            w_width = fn["bold"].size(warn_msg)[0]
            w_x = (self.MAP_VIEW_W // 2) - (w_width // 2)
            w_y = self.MAP_VIEW_H - 60

            bg_rect = pygame.Rect(w_x - 10, w_y - 4, w_width + 20, 26)
            pygame.draw.rect(viewport, (15, 15, 15), bg_rect, border_radius=4)
            pygame.draw.rect(viewport, GREEN, bg_rect, 1, border_radius=4)

            txt(viewport, warn_msg, w_x, w_y, GREEN, fn["bold"])

        if gs.quest_sys:
            import math

            if not hasattr(self, '_prev_comp_q'):
                self._prev_comp_q = sum(1 for q in gs.quest_sys._states.values() if q.status.value == "completed")
                self._q_done_timer = 0
                self._q_anim_time = 0.0

            curr_active = len(gs.quest_sys.get_active_quests())
            curr_comp = sum(1 for q in gs.quest_sys._states.values() if q.status.value == "completed")

            if curr_comp > self._prev_comp_q:
                self._q_done_timer = 120
            self._prev_comp_q = curr_comp

            self._q_anim_time += 0.05

            if curr_active > 0 or self._q_done_timer > 0:
                pad = 15
                box_w = 46
                box_h = 46
                box_x = self.MAP_VIEW_W - box_w - pad
                box_y = pad

                color = CYAN
                pulse = 0

                if self._q_done_timer > 0:
                    self._q_done_timer -= 1
                    color = GREEN
                    pulse = math.sin(self._q_done_timer * 0.4) * 4
                elif curr_active > 0:
                    color = CYAN
                    pulse = math.sin(self._q_anim_time) * 1.5

                r = max(4, 10 + pulse)

                bg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
                bg_surf.fill((10, 15, 20, 160))
                viewport.blit(bg_surf, (box_x, box_y))
                pygame.draw.rect(viewport, color, (box_x, box_y, box_w, box_h), 1, border_radius=6)

                ico_quest = self.simboli_font_lg.render("📜", True, color)

                ico_x = box_x + (box_w // 2) - (ico_quest.get_width() // 2)
                ico_y = box_y + (box_h // 2) - (ico_quest.get_height() // 2)
                viewport.blit(ico_quest, (ico_x, ico_y))

                if curr_active > 0:
                    num_str = str(curr_active)
                    num_col = color if self._q_done_timer > 0 else WHITE

                    txt_x = box_x + box_w - 12
                    txt_y = box_y + box_h - 14

                    pygame.draw.circle(viewport, (10, 15, 20), (txt_x + 4, txt_y + 6), 8)
                    txt(viewport, num_str, txt_x, txt_y, num_col, fn["sm"])

        if gs.Rivet and gs.Echo:
            import math

            def _count_unlocked(char):
                if not (char and hasattr(char, "skill_wheel")):
                    return 0
                return len(char.skill_wheel.get_available_skills(char.stats.tech_points))

            curr_skills = _count_unlocked(gs.Rivet) + _count_unlocked(gs.Echo)

            if not hasattr(self, "_prev_skill_count"):
                self._prev_skill_count  = curr_skills
                self._skill_notif_timer = 0
                self._skill_anim_time   = 0.0

            if curr_skills > self._prev_skill_count:
                self._skill_notif_timer = 150
                gs.flash("Nuova abilità sbloccata! Premi R per la ruota.", 150)
                self._wbark(get_bark(EXPLORE_BARKS, "skill_unlocked"))
            self._prev_skill_count  = curr_skills
            self._skill_anim_time  += 0.05

            sk_pad = 15
            sk_w   = 46
            sk_h   = 46
            sk_x   = self.MAP_VIEW_W - sk_w - sk_pad
            sk_y   = sk_pad + 46 + 6

            if self._skill_notif_timer > 0:
                self._skill_notif_timer -= 1
                sk_color = (255, 200, 50)
            else:
                sk_color = (130, 100, 200)

            sk_bg = pygame.Surface((sk_w, sk_h), pygame.SRCALPHA)
            sk_bg.fill((10, 8, 20, 160))
            viewport.blit(sk_bg, (sk_x, sk_y))
            pygame.draw.rect(viewport, sk_color, (sk_x, sk_y, sk_w, sk_h), 1, border_radius=6)

            ico_skill = self.simboli_font_lg.render("⚙", True, sk_color)
            ico_x = sk_x + (sk_w // 2) - (ico_skill.get_width() // 2)
            ico_y = sk_y + (sk_h // 2) - (ico_skill.get_height() // 2)

            if self._skill_notif_timer > 0:
                ico_y += math.sin(self._skill_notif_timer * 0.8) * 2

            viewport.blit(ico_skill, (ico_x, int(ico_y)))

            if curr_skills > 0:
                sk_num_col = (255, 200, 50) if self._skill_notif_timer > 0 else (200, 180, 255)
                pygame.draw.circle(viewport, (10, 8, 20), (sk_x + sk_w - 8, sk_y + sk_h - 8), 8)
                txt(viewport, str(curr_skills),
                    sk_x + sk_w - 12, sk_y + sk_h - 14, sk_num_col, fn["sm"])

        if self._rain_active:
            self._draw_rain(viewport)

        surf.blit(viewport, (MX, MY))

        hx  = MX + self.MAP_VIEW_W + 16
        hw  = W - hx - 8

        pygame.draw.rect(surf, BG2, (hx, MY, hw, H - MY * 2), border_radius=8)
        pygame.draw.rect(surf, (40, 50, 60), (hx, MY, hw, H - MY * 2), 2, border_radius=8)

        hiy = MY + 20

        def get_center_x(text, font):
            text_width = font.size(text)[0]
            return hx + (hw // 2) - (text_width // 2)

        tutti_i_mob = []
        if hasattr(self, 'maps'):
            for m in self.maps:
                otx = round(m.offset_x / MAP_TILE_PX)
                oty = round(m.offset_y / MAP_TILE_PX)
                for npc in m.mobs:
                    ng = npc.copy()
                    ng["_local_pos"] = tuple(npc["pos"])
                    ng["pos"] = (npc["pos"][0] + otx, npc["pos"][1] + oty)
                    tutti_i_mob.append(ng)

        p1_pos = (gs.p1[0], gs.p1[1])
        p2_pos = (gs.p2[0], gs.p2[1])

        tutti_i_mob_attivi = [
            npc for npc in tutti_i_mob
            if (npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"])) not in gs.defeated_npcs
        ]
        near_npc  = near_obj(p1_pos, tutti_i_mob_attivi) or near_obj(p2_pos, tutti_i_mob_attivi)

        all_terms_hud = list(TERMINALS)
        near_term = near_obj(p1_pos, all_terms_hud) or near_obj(p2_pos, all_terms_hud)

        lista_loot = getattr(self, '_dynamic_loot_spots', LOOT_SPOTS)
        avail_loot = [l for l in lista_loot if tuple(l["pos"]) not in gs.looted]

        _hud_near_term = bool(near_term)
        def _avail_loot_filtered(pos):
            if _hud_near_term:
                return near_obj(pos, [l for l in avail_loot if "cassaforte" in (l.get("label","") or "").lower()])
            return near_obj(pos, avail_loot)

        near_loot  = _avail_loot_filtered(p1_pos) or _avail_loot_filtered(p2_pos)

        dcoord, (dname, dcode, _) = cur_district(gs.p1)
        txt(surf, dname.upper(), get_center_x(dname.upper(), fn["bold"]), hiy, CYAN, fn["bold"])
        hiy += 30

        door_for_rivet = self._find_nearby_door(p1_pos, (9999, 9999)) if self._maps_loaded else None

        tip = ""
        tip_col = GREY

        if door_for_rivet is not None:
            door, m_door = door_for_rivet
            soglia = door["strength_threshold"]
            rivet_forza = gs.Rivet.stats.forza if gs.Rivet else 0

            offset_tx = round(m_door.offset_x / MAP_TILE_PX)
            offset_ty = round(m_door.offset_y / MAP_TILE_PX)
            gx = door["pos"][0] + offset_tx
            gy = door["pos"][1] + offset_ty

            _SKY_X0, _SKY_X1, _SKY_Y0, _SKY_Y1 = 55, 70, 50, 63
            _door_sky = (_SKY_X0 <= gx <= _SKY_X1 and _SKY_Y0 <= gy <= _SKY_Y1)

            if _door_sky:
                if not gs.flags.get("skyscraper_terminal_hacked", False):
                    tip = "Porta blindata"
                    tip_col = CYAN
            elif rivet_forza >= soglia:
                tip = f"[E] Porta"; tip_col = ORANGE
            else:
                tip = f"[E] {door['label']} — Forza {rivet_forza}/{soglia}"; tip_col = RED

        elif near_npc:
            hp_info = ""
            if "saved_enemies" in near_npc and near_npc["saved_enemies"]:
                tot_hp = sum(e.stats.hp for e in near_npc["saved_enemies"])
                tot_max = sum(e.stats.max_hp for e in near_npc["saved_enemies"])
                hp_info = f" (Ferito: {tot_hp}/{tot_max} HP)"

            tip = f"[E] {near_npc['name']}{hp_info}"
            tip_col = RED if npc_is_hostile(near_npc, gs.reps) else YELLOW

        elif near_term:
            tip = "[H] Terminale"; tip_col = CYAN

        elif near_loot:
            label_loot = near_loot.get('label', '').lower() if near_loot.get('label') else ""
            if "cassaforte" in label_loot:
                _safe_pos = near_loot["pos"]
                import math as _math_tip
                _rivet_dist_safe = _math_tip.hypot(gs.p1[0] - _safe_pos[0], gs.p1[1] - _safe_pos[1])
                if _rivet_dist_safe <= 1.5:
                    if not gs.flags.get("skyscraper_terminal_hacked", False):
                        tip = "[E] Cassaforte (Bloccata dal Terminale)"; tip_col = RED
                    elif not gs.flags.get("safe_breached", False):
                        tip = "[E] Sfonda la Cassaforte"; tip_col = ORANGE
                    else:
                        tip = "[E] Cassaforte (Vuota)"; tip_col = GREY
            else:
                tip = f"[E] {near_loot.get('label','Luogo')}"; tip_col = YELLOW


        elif (gs.flags.get("Q01_done", False)
            and not gs.flags.get("landmine_collected", False)):
            import math as _m
            for mp in MINE_SPOTS:
                if tuple(mp) not in getattr(self, "_mines_gone", set()):
                    if _m.hypot(gs.p1[0]-mp[0], gs.p1[1]-mp[1]) <= 2.5:
                        tip = "[E] Raccogli la mina (attenzione!)"; tip_col = ORANGE
                        break

        elif (gs.flags.get("landmine_collected", False)
            and not gs.flags.get("power_plant_door_blown", False)
            and not getattr(self, "_mine_placed", False)):
            import math as _m
            if _m.hypot(gs.p1[0]-MINE_PLACEMENT_SPOT[0], gs.p1[1]-MINE_PLACEMENT_SPOT[1]) <= 2.5:
                tip = "[E] Piazza la mina"; tip_col = ORANGE

        elif getattr(self, "_mine_placed", False):
            tip = f"[!] MINA ATTIVA — {getattr(self,'_mine_timer',0):.1f}s all'esplosione!"; tip_col = RED

        elif (gs.flags.get("power_plant_door_blown", False)
            and not gs.flags.get("power_panel_activated", False)):
            import math as _m
            if _m.hypot(gs.p2[0]-wd.POWER_PANEL_SPOT[0], gs.p2[1]-wd.POWER_PANEL_SPOT[1]) <= 2.5:
                tip = "[E] Attiva il pannello di controllo"; tip_col = CYAN

        elif (gs.flags.get("power_panel_activated", False)
              and not gs.flags.get("radar_tower_hacked", False)):
            import math as _m
            _RADAR_TOWER = (162, 31)
            if _m.hypot(gs.p2[0]-_RADAR_TOWER[0], gs.p2[1]-_RADAR_TOWER[1]) <= 2.5:
                tip = "[H] Torre Radar"; tip_col = CYAN

        elif (gs.flags.get("factory_terminal_hacked", False)
              and not gs.flags.get("factory_inner_door_breached", False)
              and dcode == "F"):
            tip = "[E] Porta"; tip_col = ORANGE

        else:
            tip = ""
            tip_col = GREY

        if tip:
            cx_tip = get_center_x(tip, fn["sm"])
            tip_w = fn["sm"].size(tip)[0] + 24

            badge_bg = (tip_col[0]//4, tip_col[1]//4, tip_col[2]//4)
            badge_rect = pygame.Rect(cx_tip - 12, hiy - 4, tip_w, 24)

            pygame.draw.rect(surf, badge_bg, badge_rect, border_radius=12)
            pygame.draw.rect(surf, tip_col, badge_rect, 1, border_radius=12)

            txt(surf, tip, cx_tip, hiy, tip_col, fn["sm"])
            hiy += 36
        else:
            hiy += 10


        for char_idx, (char, label) in enumerate([(gs.Rivet, "Rivet"), (gs.Echo, "Echo")]):
            if char is None: continue

            card_h = 145
            card_y = hiy

            card_bg = (20, 25, 32) if char_idx == 0 else (28, 20, 32)
            card_border = (40, 50, 60)
            pygame.draw.rect(surf, card_bg, (hx + 10, card_y, hw - 20, card_h), border_radius=6)
            pygame.draw.rect(surf, card_border, (hx + 10, card_y, hw - 20, card_h), 1, border_radius=6)

            hiy += 10

            hp_ratio = char.stats.hp / max(1, char.stats.max_hp)
            name_col = GREEN if hp_ratio > 0.5 else (YELLOW if hp_ratio > 0.2 else RED)

            lbl_text = f"{label}  Lv.{char.stats.level}"
            txt(surf, lbl_text, hx + 20, hiy, name_col, fn["bold"])

            hiy += 20
            weapon = getattr(char, "equipped_weapon", None)
            start_x = hx + 20

            ico_wpn = self.simboli_font.render("⚔", True, YELLOW)
            surf.blit(ico_wpn, (start_x, hiy - 2))

            text_x = start_x + ico_wpn.get_width() + 6
            if weapon:
                ammo_str = "[INF]" if weapon.ammo < 0 else f"[{weapon.ammo}]"
                txt(surf, f"{weapon.display_name[:15]} {ammo_str}", text_x, hiy, YELLOW, fn["sm"])
            else:
                txt(surf, "Disarmato", text_x, hiy, DARKGREY, fn["sm"])

            hiy += 25

            bar_margin = 35
            bar_w = hw - bar_margin - 20

            ico_hp = self.simboli_font.render("❤", True, RED)
            surf.blit(ico_hp, (hx + 15, hiy - 2))
            hp_bar(surf, hx + bar_margin, hiy, char.stats.hp, char.stats.max_hp, bar_w, 8, fn["sm"])

            gloss = pygame.Surface((bar_w, 4), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 30))
            surf.blit(gloss, (hx + bar_margin, hiy))

            hiy += 24

            ico_xp = self.simboli_font.render("⚡", True, CYAN)
            surf.blit(ico_xp, (hx + 15, hiy - 2))
            xp_threshold = char.stats.level * 100
            hp_bar(surf, hx + bar_margin, hiy, char.stats.xp, xp_threshold, bar_w, 4, fn["sm"])

            hiy += 20

            all_items = char.inventory.all_items()
            NUM_SLOTS = 5
            sel_slot = self._selected_slot[char_idx]

            if not hasattr(self, "_inv_offset"):
                self._inv_offset = [0, 0]
            max_offset = max(0, len(all_items) - NUM_SLOTS)
            self._inv_offset[char_idx] = min(self._inv_offset[char_idx], max_offset)

            slot_w = (bar_w - (NUM_SLOTS - 1) * 4) // NUM_SLOTS
            slot_h = 32

            for s in range(NUM_SLOTS):
                sx = hx + bar_margin + s * (slot_w + 4)
                item_idx = self._inv_offset[char_idx] + s
                is_sel = (item_idx == sel_slot)

                bg_col = (10, 60, 80) if is_sel else (10, 12, 18)
                brd_col = CYAN if is_sel else (50, 60, 70)
                sr = pygame.Rect(sx, hiy, slot_w, slot_h)

                pygame.draw.rect(surf, bg_col, sr, border_radius=4)
                pygame.draw.rect(surf, brd_col, sr, 1, border_radius=4)

                if item_idx < len(all_items):
                    item = all_items[item_idx]
                    qty_col = WHITE if is_sel else GREY

                    ico_str = "📦"

                    if item.item_type == ItemType.WEAPON:
                        ico_str = "🔫"
                    elif item.item_type == ItemType.CONSUMABLE:
                        if getattr(item, 'hp_restore', 0) > 0:
                            ico_str = "💊"
                        elif getattr(item, 'damage', 0) > 0:
                            ico_str = "💣"
                        else:
                            ico_str = "💉"
                    elif item.item_type == ItemType.MATERIAL:
                        ico_str = "⚙"

                    ico_item = self.simboli_font.render(ico_str, True, qty_col)
                    ix = sx + (slot_w // 2) - (ico_item.get_width() // 2)
                    surf.blit(ico_item, (ix, hiy + 2))

                    txt(surf, f"x{item.quantity}", sx + 4, hiy + 18, qty_col, fn["sm"])
                else:
                    pygame.draw.circle(surf, (40, 50, 60), (sx + slot_w//2, hiy + slot_h//2), 2)

            hiy += slot_h + 20

        eth = gs.ethics

        fazioni_scoperte = [(f, r) for f, r in gs.reps.items() if f.lower() != "zombie"]
        alleati = [(f, r) for f, r in fazioni_scoperte if r > 0]
        neutri  = [(f, r) for f, r in fazioni_scoperte if r == 0]
        nemici  = [(f, r) for f, r in fazioni_scoperte if r < 0]

        card_h = 60
        if fazioni_scoperte:
            card_h += 8
            if alleati: card_h += 20 + (((len(alleati) + 1) // 2) * 20) + 4
            if neutri:  card_h += 20 + (((len(neutri) + 1) // 2) * 20) + 4
            if nemici:  card_h += 20 + (((len(nemici) + 1) // 2) * 20) + 4
            card_h += 6

        card_y = hiy
        pygame.draw.rect(surf, (20, 20, 20), (hx + 10, card_y, hw - 20, card_h), border_radius=6)
        pygame.draw.rect(surf, (40, 50, 60), (hx + 10, card_y, hw - 20, card_h), 1, border_radius=6)

        hiy += 10

        if eth <= -8:
            ico_warn = self.simboli_font.render("⚠", True, RED)
            surf.blit(ico_warn, (hx + 20, hiy - 1))
            txt(surf, "LEGAME IN CRISI", hx + 20 + ico_warn.get_width() + 5, hiy, RED, fn["sm"])
        else:
            txt(surf, "Stato Relazione", hx + 20, hiy, RED, fn["sm"])

        if eth >= 0:
            eth_col = GREEN
        elif eth >= -5:
            eth_col = ORANGE
        else:
            eth_col = RED
        eth_text = f"{eth:+d}"
        txt(surf, eth_text, hx + hw - 20 - fn["bold"].size(eth_text)[0], hiy-2, eth_col, fn["bold"])

        hiy += 20
        eth_w = hw - 40
        eth_cx = hx + 20 + eth_w // 2

        if eth <= -8 and hasattr(self, '_anim') and int(self._anim * 8) % 2 == 0:
            bar_bg = (80, 10, 10)
        else:
            bar_bg = (10, 10, 10)
        pygame.draw.rect(surf, bar_bg, (hx + 20, hiy, eth_w, 6), border_radius=3)

        MAX_ETH = 10
        fill_px = int((abs(eth) / MAX_ETH) * (eth_w // 2))
        fill_px = min(fill_px, eth_w // 2)
        if eth >= 0:
            pygame.draw.rect(surf, GREEN, (eth_cx, hiy, fill_px, 6), border_radius=3)
        else:
            pygame.draw.rect(surf, RED, (eth_cx - fill_px, hiy, fill_px, 6), border_radius=3)
        pygame.draw.line(surf, WHITE, (eth_cx, hiy-2), (eth_cx, hiy+8))

        hiy += 18

        if fazioni_scoperte:
            pygame.draw.line(surf, (40, 50, 60), (hx + 20, hiy), (hx + hw - 20, hiy))
            hiy += 8

            col_w = eth_w // 2

            def draw_faction_group(title, faction_list, color, current_y):
                if not faction_list:
                    return current_y

                txt(surf, title, hx + 20, current_y, color, fn["bold"])
                current_y += 20

                for i, (f_name, f_rep) in enumerate(faction_list):
                    col_idx = i % 2
                    row_idx = i // 2
                    fx = hx + 20 + (col_idx * col_w)
                    fy = current_y + (row_idx * 20)
                    txt(surf, f"{f_name.capitalize()}: {f_rep:+d}", fx, fy, color, fn["sm"])

                return current_y + (((len(faction_list) + 1) // 2) * 20) + 4

            hiy = draw_faction_group("Alleati", alleati, GREEN, hiy)
            hiy = draw_faction_group("Neutri", neutri, GREY, hiy)
            hiy = draw_faction_group("Nemici", nemici, RED, hiy)

            hiy += 6
        else:
            hiy += 10

        nav_y = (MY + H - MY * 2) - 100

        txt(surf, "MENU RAPIDO", get_center_x("MENU RAPIDO", fn["sm"]), nav_y - 20, (100, 110, 120), fn["sm"])

        buttons = [
            {"key": "C", "label": "Craft", "col": YELLOW, "sym": "⚒"},
            {"key": "M", "label": "Mappa", "col": CYAN, "sym": "🗺"},
            {"key": "Q", "label": "Diario", "col": GREEN, "sym": "📜"},
            {"key": "R", "label": "Abilità", "col": MAGENTA, "sym": "⚙"},
            {"key": "U", "label": "Usa", "col": WHITE, "sym": "🎒"},
            {"key": "P", "label": "Pausa", "col": RED, "sym": "⏻"}
        ]

        btn_w = (hw - 40) // 3
        btn_h = 36
        gap_x = 10
        gap_y = 10

        for i, btn in enumerate(buttons):
            col_idx = i % 3
            row_idx = i // 3

            bx = hx + 10 + col_idx * (btn_w + gap_x)
            by = nav_y + row_idx * (btn_h + gap_y)

            pygame.draw.rect(surf, (25, 30, 35), (bx, by, btn_w, btn_h), border_radius=6)
            pygame.draw.line(surf, btn["col"], (bx + 4, by), (bx + btn_w - 4, by), 2)

            ico_surf = self.simboli_font_lg.render(btn["sym"], True, btn["col"])
            surf.blit(ico_surf, (bx + btn_w - 30, by + 6))

            txt(surf, f"[{btn['key']}]", bx + 6, by + 4, WHITE, fn["sm"])
            txt(surf, btn["label"], bx + 6, by + 18, (150, 160, 170), fn["sm"])

        if self._dialogue_node is not None:
            self._draw_dialogue(surf, self.MAP_VIEW_W, self.MAP_VIEW_H, MX, MY, fn)
        if self._in_predialogue:
            self._draw_predialogue(surf, self.MAP_VIEW_W, self.MAP_VIEW_H, MX, MY, fn)
        if getattr(self, '_in_loot_menu', False):
            self._draw_loot_menu(surf)
        if getattr(self, '_in_drop_menu', False):
            self._draw_drop_menu(surf)
        if getattr(self, '_in_use_menu', False):
            self._draw_use_menu(surf)
        if self._debug_node_puzzle:
            self._draw_debug_node_puzzle(surf)
        if getattr(gs, 'pending_battle_loot', None):
            self._current_loot_stash = gs.pending_battle_loot
            self._in_loot_menu = True
            self._loot_cursor = 0
            self._current_loot_spot = None
            self._loot_target_idx = 0

            gs.pending_battle_loot = None
            self._wbark(get_bark(EXPLORE_BARKS, "loot_enemies_post_battle"))

    def _draw_dialogue(self, surf, map_w, map_h, ox, oy, fn):
        """Disegna il pannello dialogo con cursore a icone e box model moderno."""
        node = self._dialogue_node

        pw = min(map_w - 60, 750)
        max_text_w = pw - 40

        def wrap_text(text, font, max_w, indent=""):
            words = text.split()
            lines, cur = [], ""
            for w in words:
                test = cur + w
                if font.size(test)[0] > max_w and cur:
                    lines.append(cur.rstrip())
                    cur = indent + w + " "
                else:
                    cur += w + " "
            if cur.strip(): lines.append(cur.rstrip())
            return lines if lines else [""]

        lines_txt = wrap_text(node.text, fn["sm"], max_text_w)

        wrapped_choices = []
        indent_spaces = "   "
        for i, choice_tuple in enumerate(node.choices):
            choice_txt = choice_tuple[0]
            target = choice_tuple[1]
            lines = wrap_text(choice_txt, fn["sm"], max_text_w - 20, indent=indent_spaces)
            wrapped_choices.append((i, lines, target))

        text_height    = len(lines_txt) * 22
        choices_height = sum(len(wc[1]) * 22 + 6 for wc in wrapped_choices)
        ph = 60 + text_height + 20 + choices_height + 15

        px = ox + (map_w - pw) // 2
        py = oy + map_h - ph - 30

        overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
        overlay.fill((15, 18, 25, 230))
        surf.blit(overlay, (px, py))
        pygame.draw.rect(surf, CYAN, (px, py, pw, ph), 2, border_radius=8)

        ico_chat = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18)).render("💬", True, CYAN)
        surf.blit(ico_chat, (px + 16, py + 14))
        txt(surf, f"{self._dialogue_npc.upper()}", px + 16 + ico_chat.get_width() + 8, py + 16, CYAN, fn["bold"])
        pygame.draw.line(surf, (40, 60, 80), (px + 16, py + 38), (px + pw - 16, py + 38))

        ty = py + 50
        for lt in lines_txt:
            txt(surf, lt, px + 20, ty, (230, 240, 255), fn["sm"])
            ty += 22

        ty += 15

        font_simboli = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18))
        for i, lines, _ in wrapped_choices:
            sel = (i == self._dialogue_cursor)
            col = GREEN if sel else GREY

            if sel:
                pygame.draw.rect(surf, (20, 40, 30), (px + 10, ty - 4, pw - 20, len(lines)*22 + 4), border_radius=4)
                ico_cursor = font_simboli.render("➤", True, GREEN)

                text_h = fn["sm"].get_height()
                arrow_h = ico_cursor.get_height()
                arrow_y = ty + (text_h // 2) - (arrow_h // 2)
                surf.blit(ico_cursor, (px + 16, arrow_y))

            for j, line in enumerate(lines):
                offset_x = 36 if j == 0 else 16
                txt(surf, line, px + offset_x, ty, col, fn["sm"])
                ty += 22
            ty += 6

    def _draw_predialogue(self, surf, map_w, map_h, ox, oy, fn):
        """Pannello pre-dialogo con icone per i toni."""
        npc  = self._predialogue_npc
        opts = self._predialogue_options
        role = "Rivet" if len(opts) == 4 and opts[0][0] == "Minaccioso" else "Echo"

        pw = min(map_w - 20, 480)
        ph = 70 + len(opts) * 30 + 20
        px = ox + (map_w - pw) // 2
        py = oy + map_h - ph - 30

        overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
        overlay.fill((25, 15, 10, 230))
        surf.blit(overlay, (px, py))
        pygame.draw.rect(surf, ORANGE, (px, py, pw, ph), 2, border_radius=8)

        npc_name = npc["name"] if npc else "?"
        txt(surf, f"APPROCCIO: {npc_name.upper()}", px + 20, py + 15, ORANGE, fn["bold"])
        txt(surf, f"Interlocutore: {role}", px + 20, py + 35, (200, 150, 100), fn["sm"])
        pygame.draw.line(surf, (100, 50, 30), (px + 16, py + 55), (px + pw - 16, py + 55))

        ty = py + 65
        font_simboli = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18))

        for i, (label, tone_id) in enumerate(opts):
            sel = (i == self._predialogue_cursor)
            col = GREEN if sel else GREY
            ico_str = "💬"

            if tone_id == "ATTACK":   col = RED if sel else (180,60,60); ico_str = "⚔"
            elif tone_id == "IGNORE": col = CYAN if sel else (60,160,160); ico_str = "🏃"
            elif "aggressive" in tone_id or "Minaccioso" in label: ico_str = "💢"
            elif "diplomatic" in tone_id or "Pragmatico" in label: ico_str = "⚖"

            if sel:
                pygame.draw.rect(surf, (40, 20, 10) if tone_id=="ATTACK" else (20, 30, 20),
                                 (px + 10, ty - 4, pw - 20, 28), border_radius=4)
                ico_cursor = font_simboli.render("➤", True, col)
                surf.blit(ico_cursor, (px + 16, ty))

            ico_tone = font_simboli.render(ico_str, True, col)
            surf.blit(ico_tone, (px + 40, ty - 2))

            txt(surf, label, px + 70, ty, col, fn["sm"])
            ty += 30

        pygame.draw.line(surf, (100, 50, 30), (px + 16, ty), (px + pw - 16, ty))
        txt(surf, "↑↓ Naviga   INVIO Conferma   ESC Combatti", px + pw//2, ty + 10, GREY, fn["sm"], center=True)

    def _draw_loot_menu(self, screen: Surface) -> None:
        """Menu Loot con Icone Oggetti."""
        import pygame

        gs = GameManager.get_instance()
        target_char = gs.Rivet if getattr(self, '_loot_target_idx', 0) == 0 else gs.Echo
        color_char = CYAN if getattr(self, '_loot_target_idx', 0) == 0 else MAGENTA

        cur_w = InventoryWeightManager.current_weight(target_char.inventory, target_char.weapons)
        max_w = InventoryWeightManager.max_weight(target_char.name)

        items = getattr(self, '_current_loot_stash', [])
        max_vis = getattr(self, 'MAX_VISIBLE_ITEMS', 8)
        visible_count = min(len(items), max_vis)
        offset = getattr(self, '_loot_offset', 0)

        ph_items = max(1, visible_count) * 28
        pw, ph = 480, 140 + ph_items
        px = 8 + (self.MAP_VIEW_W - pw) // 2
        py = 8 + (self.MAP_VIEW_H - ph) // 2

        pygame.draw.rect(screen, (15, 20, 25, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(screen, CYAN, (px, py, pw, ph), 2, border_radius=8)

        txt(screen, "BOTTINO TROVATO", px + pw//2, py + 15, WHITE, self.fonts["bold"], center=True)
        txt(screen, f"Destinazione: {target_char.name} (Peso: {cur_w}/{max_w})", px + pw//2, py + 40, color_char, self.fonts["sm"], center=True)
        sep(screen, px + 10, py + 60, pw - 20, CYAN)

        if not items:
            txt(screen, "Contenitore vuoto.", px + pw//2, py + 85, GREY, self.fonts["sm"], center=True)
        else:
            font_simboli = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18))
            for i in range(visible_count):
                idx = offset + i
                if idx >= len(items): break

                item = items[idx]
                iy = py + 75 + (i * 28)
                is_sel = (idx == self._loot_cursor)

                col = WHITE if is_sel else GREY
                item_col = col
                if not InventoryWeightManager.can_add(target_char.name, target_char.inventory, item.quantity, target_char.weapons):
                    item_col = RED if is_sel else (150, 50, 50)

                if is_sel:
                    pygame.draw.rect(screen, (30, 50, 60), (px + 10, iy - 2, pw - 20, 26), border_radius=4)
                    ico_cursor = font_simboli.render("➤", True, CYAN)
                    screen.blit(ico_cursor, (px + 14, iy))

                ico_str = "📦"
                if getattr(item, 'item_type', None) == ItemType.WEAPON: ico_str = "🔫"
                elif getattr(item, 'item_type', None) == ItemType.CONSUMABLE:
                    if getattr(item, 'hp_restore', 0) > 0: ico_str = "💊"
                    elif getattr(item, 'damage', 0) > 0:   ico_str = "💣"
                    else: ico_str = "💉"
                elif getattr(item, 'item_type', None) == ItemType.MATERIAL: ico_str = "⚙"

                ico_item = font_simboli.render(ico_str, True, item_col)
                screen.blit(ico_item, (px + 36, iy - 2))

                txt(screen, f"{item.name} x{item.quantity}", px + 66, iy, item_col, self.fonts["sm"])

        sep(screen, px + 10, py + ph - 40, pw - 20, CYAN)
        txt(screen, "INVIO Prendi   TAB Cambia PG   ESC Lascia", px + pw//2, py + ph - 25, GREY, self.fonts["sm"], center=True)

    def _draw_drop_menu(self, surf: Surface) -> None:
        """Menu Drop con Icone."""
        import pygame

        gs = GameManager.get_instance()
        char_idx = getattr(self, '_drop_char_idx', 0)
        char = gs.Rivet if char_idx == 0 else gs.Echo
        items = char.inventory.all_items()

        max_vis = getattr(self, 'MAX_VISIBLE_ITEMS', 8)
        visible_count = min(len(items), max_vis)
        offset = getattr(self, '_drop_offset', 0)
        cursor = getattr(self, '_drop_cursor', 0)

        ph_items = max(1, visible_count) * 28
        pw, ph = 460, 110 + ph_items
        px = 8 + (self.MAP_VIEW_W - pw) // 2
        py = 8 + (self.MAP_VIEW_H - ph) // 2

        border_col = CYAN if char.name == "Rivet" else MAGENTA

        pygame.draw.rect(surf, (15, 15, 20, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, border_col, (px, py, pw, ph), 2, border_radius=8)

        txt(surf, f"ZAINO DI {char.name.upper()} - Lascia Oggetti", px + pw//2, py + 15, WHITE, self.fonts["bold"], center=True)
        sep(surf, px + 10, py + 35, pw - 20, border_col)

        if not items:
            txt(surf, "Lo zaino è vuoto.", px + pw//2, py + 60, GREY, self.fonts["sm"], center=True)
        else:
            font_simboli = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18))
            for i in range(visible_count):
                idx = offset + i
                if idx >= len(items): break

                item = items[idx]
                iy = py + 50 + (i * 28)
                is_sel = (idx == cursor)
                col = WHITE if is_sel else GREY

                if is_sel:
                    bg_sel = (20, 50, 60) if char_idx == 0 else (50, 20, 50)
                    pygame.draw.rect(surf, bg_sel, (px + 10, iy - 2, pw - 20, 26), border_radius=4)
                    ico_cursor = font_simboli.render("➤", True, border_col)
                    surf.blit(ico_cursor, (px + 14, iy))

                ico_str = "📦"
                if getattr(item, 'item_type', None) == ItemType.WEAPON: ico_str = "🔫"
                elif getattr(item, 'item_type', None) == ItemType.CONSUMABLE:
                    if getattr(item, 'hp_restore', 0) > 0: ico_str = "💊"
                    elif getattr(item, 'damage', 0) > 0:   ico_str = "💣"
                    else: ico_str = "💉"
                elif getattr(item, 'item_type', None) == ItemType.MATERIAL: ico_str = "⚙"

                ico_item = font_simboli.render(ico_str, True, col)
                surf.blit(ico_item, (px + 36, iy - 2))

                txt(surf, f"{item.name} x{item.quantity}", px + 66, iy, col, self.fonts["sm"])

        sep(surf, px + 10, py + ph - 40, pw - 20, border_col)
        txt(surf, "INVIO Butta 1   SPAZIO Butta Tutti   ESC Chiudi", px + pw//2, py + ph - 25, GREY, self.fonts["sm"], center=True)

    def _draw_use_menu(self, surf: Surface) -> None:
        """Menu Usa con Icone e Tag contestuali."""
        import pygame

        gs = GameManager.get_instance()
        items = getattr(self, '_use_item_list', [])
        max_vis = self.MAX_VISIBLE_ITEMS
        visible_count = min(len(items), max_vis)
        offset = getattr(self, '_use_item_offset', 0)
        cursor = getattr(self, '_use_item_cursor', 0)

        chars_alive = [c for c in [gs.Rivet, gs.Echo] if c.is_alive()]
        heal_target = (min(chars_alive, key=lambda c: c.stats.hp / max(c.stats.max_hp, 1))
                       if chars_alive else None)

        ph_items = max(1, visible_count) * 28
        pw, ph = 480, 130 + ph_items
        px = 8 + (self.MAP_VIEW_W - pw) // 2
        py = 8 + (self.MAP_VIEW_H - ph) // 2
        pygame.draw.rect(surf, (15, 25, 20, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, GREEN, (px, py, pw, ph), 2, border_radius=8)

        txt(surf, "USA OGGETTO", px + pw // 2, py + 14, WHITE, self.fonts["bold"], center=True)

        if heal_target:
            hp_pct = int(heal_target.stats.hp / max(heal_target.stats.max_hp, 1) * 100)
            txt(surf, f"Bersaglio: {heal_target.name}  HP {heal_target.stats.hp}/{heal_target.stats.max_hp} ({hp_pct}%)",
                px + pw // 2, py + 34, YELLOW, self.fonts["sm"], center=True)

        sep(surf, px + 10, py + 50, pw - 20, GREEN)

        if not items:
            txt(surf, "Nessun consumabile disponibile.", px + pw // 2, py + 75, GREY, self.fonts["sm"], center=True)
        else:
            font_simboli = getattr(self, "simboli_font", pygame.font.SysFont("arial", 18))
            for i in range(visible_count):
                idx = offset + i
                if idx >= len(items): break
                item = items[idx]
                iy = py + 60 + (i * 28)
                is_sel = (idx == cursor)
                col = WHITE if is_sel else GREY

                if is_sel:
                    pygame.draw.rect(surf, (20, 50, 30), (px + 10, iy - 2, pw - 20, 26), border_radius=4)
                    ico_cursor = font_simboli.render("➤", True, GREEN)
                    surf.blit(ico_cursor, (px + 14, iy))

                ico_str = "💊"
                if item.hp_restore > 0 and item.damage == 0:
                    tag = f"+{item.hp_restore} HP"
                    tag_col = GREEN
                elif item.damage > 0 and item.hp_restore == 0:
                    tag = f"DMG {item.damage}"
                    tag_col = YELLOW
                    ico_str = "💣"
                else:
                    tag = f"+{item.hp_restore}HP / {item.damage}DMG"
                    tag_col = CYAN

                ico_item = font_simboli.render(ico_str, True, col)
                surf.blit(ico_item, (px + 36, iy - 2))

                txt(surf, f"{item.name} x{item.quantity}", px + 66, iy, col, self.fonts["sm"])
                txt(surf, tag, px + pw - 90, iy, tag_col, self.fonts["sm"])

        sep(surf, px + 10, py + ph - 42, pw - 20, GREEN)
        txt(surf, "↑↓ Naviga   INVIO Usa   ESC Chiudi", px + pw // 2, py + ph - 26, GREY, self.fonts["sm"], center=True)

    def _draw_debug_node_puzzle(self, surf: Surface) -> None:
        """Overlay debug F2 — stato interno del puzzle Node/Mastermind.
        NOTA: non cambia gs.screen; avvia il puzzle in background solo se non già attivo.
        """
        gs   = GameManager.get_instance()
        hack = gs.hack_sys
        if hack and not hack._current_puzzle:
            gs.activate_terminal((171, 103))
        p    = hack._current_puzzle if hack else None

        fn   = self.fonts
        pad  = 10
        pw   = 340
        lh   = 18

        rows = []
        rows.append(("[NODE PUZZLE DEBUG]", CYAN))
        rows.append((f"puzzle_type : {getattr(gs, 'puzzle_type', '—')}", WHITE))

        if p is None:
            rows.append(("_current_puzzle : None", YELLOW))
        else:
            rows.append((f"tipo puzzle     : {type(p).__name__}", WHITE))
            secret = getattr(p, "_secret", None) or getattr(p, "_target", None)
            if secret is not None:
                rows.append((f"_secret/target  : {list(secret) if hasattr(secret, '__iter__') else secret}", GREEN))
            entered = getattr(p, "_entered", [])
            rows.append((f"_entered        : {list(entered)}", YELLOW))
            history = getattr(p, "_history", [])
            rows.append((f"_history ({len(history)} righe):", WHITE))
            for i, (digits, colors) in enumerate(history[-6:]):
                short_colors = [c[0].upper() for c in colors]
                rows.append((f"  [{i+1}] {list(digits)}  {short_colors}", GREY))
            rows.append((f"is_solved       : {p.is_solved()}", GREEN if p.is_solved() else WHITE))
            rows.append((f"failed_attempts : {hack.failed_attempts} / {hack.MAX_ATTEMPTS}", RED if hack.failed_attempts > 0 else WHITE))
            rows.append((f"is_locked_out   : {hack.is_locked_out}", RED if hack.is_locked_out else WHITE))

        ph = pad * 2 + len(rows) * lh + (len(rows) - 1) * 2
        px = W - pw - 8
        py = 8

        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((8, 12, 20, 210))
        surf.blit(bg, (px, py))
        pygame.draw.rect(surf, CYAN, (px, py, pw, ph), 1, border_radius=4)
        pygame.draw.rect(surf, YELLOW, (px, py, 3, ph), border_radius=2)

        ry = py + pad
        for text, col in rows:
            s = fn["sm"].render(text, True, col)
            surf.blit(s, (px + pad + 4, ry))
            ry += lh + 2

        lbl = fn["sm"].render("[F2] debug node", True, (80, 80, 80))
        surf.blit(lbl, (px + pw - lbl.get_width() - pad, py + ph - lbl.get_height() - 4))

    def _draw_rain(self, surf: Surface) -> None:
        """Disegna l'overlay pioggia con gocce + velo semitrasparente."""
        sw, sh = surf.get_size()

        veil = pygame.Surface((sw, sh), pygame.SRCALPHA)
        veil.fill((100, 130, 180, 18))
        surf.blit(veil, (0, 0))

        rain_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for drop in self._rain_drops:
            drop.draw(rain_surf)
        surf.blit(rain_surf, (0, 0))