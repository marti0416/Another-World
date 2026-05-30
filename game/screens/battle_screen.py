"""
battle_screen.py — Screen di battaglia a turni (State GoF).

Gestisce il ciclo attacco-difesa tra il gruppo e i nemici: menu comandi,
esecuzione dei Command GoF (Attack/Weapon/Skill/Item/Flee), turni dei nemici,
animazioni e log di battaglia.
"""

from __future__ import annotations
import math
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.paths import asset
from game.world.world_data import (
    W, H,
    BG, BG2, BG3, RED, GREEN, CYAN, YELLOW, MAGENTA, GREY, DARKGREY, WHITE
)
from game.view.draw_utils import txt, hp_bar, panel, sep
from game.controller.game_manager import GameManager
from game.dialogue.dialogue_barks import get_bark, ENEMY_BARKS, BATTLE_PLAYER_BARKS
from game.view.speech_bubble import SpeechBubbleManager
from game.model.enemy import EnemyFactory
from game.model.item import ItemType
from game.model.stats import StatusEffect
from game.events.event_types import EventType
from game.systems.battle_system import (
    AttackCommand, WeaponCommand, ComboCommand, ItemCommand, SkillCommand
)
from game.view.renderer import BattleRenderer
from game.view.ui_widgets import HealthBar, WidgetGroup

_GM = GameManager
_BR = BattleRenderer

BATTLE_ACTIONS = [
    ("Attacca",  "attack"),
    ("Abilità",  "skill"),
    ("Arma",     "weapon"),
    ("Oggetto",  "item"),
    ("Combo",    "combo"),
    ("Fuggi",    "flee")
]

BATTLE_ACTION_META = [
    {"key": "C", "sym": "⚔"},
    {"key": "K", "sym": "✨"},
    {"key": "N", "sym": "🔫"},
    {"key": "I", "sym": "💊"},
    {"key": "Z", "sym": "💥"},
    {"key": "F", "sym": "🏃"},
]

_BATTLE_TOOLTIPS = {
    "Fucile d'Assalto": "Danno: 25. Inceppamento: 5% (ridotto da ATK). L'attacco abbassa il rinculo.",
    "Rail Gun": "Danno: 35. Colpisce fino a 2 nemici. Inceppamento: 5% (ridotto da ATK).",
    "Acid Gun": "Danno: 15 + Corrosione (6 HP/turno x3). Inceppamento: 8%.",
    "Missile Incendiario": "Danno: 45 fisso (ignora DIF) + Fuoco (10 HP/turno x2). Mira calcolata su ATK.",
    "Colpo Artiglieria": "Danno: 65 fisso (ignora DIF) sul nemico più forte. Mira calcolata su ATK.",
    "Razzo Termobarico": "Danno: 95 fisso (ignora DIF) a TUTTI i nemici. Precisione bassa (migliora con ATK).",
    "Granata Antimateria": "Danno: 50. Splash damage su altri nemici (ATK) e alleati (DIF).",
    "Pistola Leggera": "Danno: 15. Inceppamento: 5% (ridotto da ATK). Bersaglio casuale.",
    "Pistola Arrugginita": "Danno: 20. Inceppamento: 10% (ridotto da ATK). Bersaglio casuale.",
    "Arma Recuperata": "Danno: 25. Inceppamento: 3% fisso. Colpisce il nemico più debole.",
    "Mazza di Fortuna": "Danno: 18 + tuo ATK. Nessun inceppamento.",
    "Coltello Improvvisato": "Danno: 14 + tuo ATK. Nessun inceppamento.",
    "Kit medico": "Cura 30 HP.",
    "Kit med. avanzato": "Cura 60 HP.",
    "Antibiotici": "Cura 20 HP e contrasta alcune infezioni.",
    "Bende Mediche": "Cura 15 HP.",
    "Razioni": "Cura 10 HP.",
    "Cibo in Scatola": "Cura 15 HP.",
    "Cocktail Molotov": "Danno: 15. Possibile splash su nemici e autoferimento.",
    "Termite": "Danno: 15 su tutti. Il danno si dimezza ad ogni turno.",
    "Carica C4": "Esplode al turno successivo, infliggendo 50 danni a tutti i nemici.",
    "Mina Militare": "Danno: 80 a tutti i nemici. Alta probabilità di ferire il gruppo (ridotta da DEF).",
    "Piranha Solution": "Danno: 10 + Vulnerabilità (+10 danni extra ricevuti ad ogni turno). 1x per battaglia.",
    "Esplosivo Combatt.": "Danno: 25. Possibile splash e autoferimento.",
    "Granata Flash": "Nessun danno. Elevata probabilità di applicare Confusione a tutti i nemici.",
    "Schianto Brutale": "Colpo devastante su bersaglio casuale. Danno ATK×1.5.",
    "Rattoppo d'Emergenza": "Ripara ferite lievi. 1× per battaglia.",
    "Onda al Plasma": "ATK×1.5 al nemico con più HP e ATK a tutti gli altri.",
    "Punto di Fusione": "ATK×3 al nemico con più HP, ATK×1.5 agli altri. 1× per battaglia.",
    "Manovra Evasiva": "Garantisce Evasione: il prossimo attacco verrà schivato al 100%.",
    "Interferenza Cognitiva": "Confonde il bersaglio facendogli saltare il turno.",
    "Miraggio Tattico": "Confonde il bersaglio + 35% probabilità di infliggere danno bonus pari ad ATK.",
    "Cortocircuito Sinaptico": "Danno ATK×2.5 + applica Shock (salta il turno)."
}


class BattleScreen(Screen):
    ENEMY_TURN_DELAY = 40

    def __init__(self, fonts):
        self.fonts   = fonts
        self._anim   = 0.0
        self._renderer = None
        self._enemy_timer: int = 0
        self._hbars: dict = {}
        self._hbar_group = None
        self.sel_state  = "main"
        self.sel_cursor = 0
        self._skill_list: list = []
        self._player_acted: bool = False
        self._item_list: list = []
        self._mouse_pos = (0, 0)
        self._hovered_tooltip = None

        self._bubbles = SpeechBubbleManager()
        import os
        import pygame

        base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
        bg_path = asset("images/backgrounds/battle_scene.png")

        raw_bg = pygame.image.load(bg_path).convert()

        self.background = pygame.transform.scale(raw_bg, (W, H))

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)
        self.simboli_font_lg = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 24)

    def handle_event(self, event):
        gs = GameManager.get_instance()
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = getattr(event, "pos", (0, 0))
        if event.type != pygame.KEYDOWN:
            return
        if gs.turn == "enemy" or self._player_acted:
            return
        k = event.key
        if self.sel_state == "main":
            if   k == pygame.K_LEFT   or k == pygame.K_a: gs.bat_cursor = (gs.bat_cursor - 1) % len(BATTLE_ACTIONS)
            elif k == pygame.K_RIGHT or k == pygame.K_d: gs.bat_cursor = (gs.bat_cursor + 1) % len(BATTLE_ACTIONS)
            elif k in (pygame.K_RETURN, pygame.K_SPACE): self._exec_action(BATTLE_ACTIONS[gs.bat_cursor][1])
            elif k == pygame.K_c: self._exec_action("attack")
            elif k == pygame.K_k: self._exec_action("skill")
            elif k == pygame.K_n: self._exec_action("weapon")
            elif k == pygame.K_i: self._exec_action("item")
            elif k == pygame.K_z: self._exec_action("combo")
            elif k == pygame.K_f: self._exec_action("flee")
        elif self.sel_state.startswith("sel_") and self.sel_state not in ("sel_skill_rivet", "sel_skill_echo", "sel_item"):
            char = gs.Rivet if self.sel_state == "sel_rivet" else gs.Echo
            if not char.weapons:
                self.sel_state = "main"
                return
            if k in (pygame.K_UP, pygame.K_w):
                self.sel_cursor = (self.sel_cursor - 1) % len(char.weapons)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.sel_cursor = (self.sel_cursor + 1) % len(char.weapons)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                char.equip_weapon(char.weapons[self.sel_cursor])
                self._next_weapon_step()
            elif k == pygame.K_ESCAPE:
                self.sel_state = "main"
        elif self.sel_state == "sel_item":
            if not self._item_list:
                self.sel_state = "main"
                return
            if k in (pygame.K_UP, pygame.K_w):
                self.sel_cursor = (self.sel_cursor - 1) % len(self._item_list)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.sel_cursor = (self.sel_cursor + 1) % len(self._item_list)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self._use_selected_item()
            elif k == pygame.K_ESCAPE:
                self.sel_state = "main"
                self._item_list = []
                self._player_acted = False
        elif self.sel_state in ("sel_skill_rivet", "sel_skill_echo"):
            if not self._skill_list:
                self.sel_state = "main"
                return
            if k in (pygame.K_UP, pygame.K_w):
                self.sel_cursor = (self.sel_cursor - 1) % len(self._skill_list)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.sel_cursor = (self.sel_cursor + 1) % len(self._skill_list)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_skill_selection()
            elif k == pygame.K_ESCAPE:
                self.sel_state = "main"
                self._skill_list = []

    def _exec_action(self, action):
        gs = GameManager.get_instance()
        alive_enemies = [e for e in gs.enemies if e.is_alive()]

        if action == "weapon":
            if gs.Rivet.is_alive(): self._consolidate_weapons(gs.Rivet)
            if gs.Echo.is_alive(): self._consolidate_weapons(gs.Echo)

            self.needs_rivet = len(gs.Rivet.weapons) > 1 if gs.Rivet.is_alive() else False
            self.needs_echo = len(gs.Echo.weapons) > 1 if gs.Echo.is_alive() else False

            if not self.needs_rivet and not self.needs_echo:
                if gs.Rivet.is_alive() and len(gs.Rivet.weapons) >= 1: gs.Rivet.equip_weapon(gs.Rivet.weapons[0])
                if gs.Echo.is_alive() and len(gs.Echo.weapons) >= 1: gs.Echo.equip_weapon(gs.Echo.weapons[0])
                self._exec_action("attack")
            else:
                self._next_weapon_step()
            return

        if action == "skill":
            rivet_skills = gs.Rivet.skill_wheel.get_combat_skills(gs.Rivet.stats.tech_points) if gs.Rivet.is_alive() else []
            echo_skills  = gs.Echo.skill_wheel.get_combat_skills(gs.Echo.stats.tech_points)  if gs.Echo.is_alive() else []

            if not rivet_skills and not echo_skills:
                gs.log(gs.blog, "Nessuna skill disponibile — entrambi attaccano!")
                self._exec_action("attack")
                return

            self._pending_rivet_skill  = None
            self._pending_echo_skills  = echo_skills

            if rivet_skills:
                self._skill_list = rivet_skills
                self.sel_cursor  = 0
                self.sel_state   = "sel_skill_rivet"
            else:
                self._skill_list = echo_skills
                self.sel_cursor  = 0
                self.sel_state   = "sel_skill_echo"
            return

        self._player_acted = True

        if not alive_enemies:
            self._check_end()
            return

        if action == "attack":

            valid_targets = self._get_valid_targets(alive_enemies)

            def _esegui_attacco_con_report(char, target):
                wpn = getattr(char, "equipped_weapon", None)
                atk_base = char.stats.atk
                def_nemico = target.stats.defense

                if wpn:
                    wpn_dmg = getattr(wpn, 'damage', 0)
                    prob_inceppamento = getattr(wpn, 'jam_chance', 0) * 100
                    bark_dichiarazione = f"{wpn.display_name}! (Atk: {atk_base}+{wpn_dmg} vs Def {def_nemico} | Incepp: {prob_inceppamento}%)"
                    cmd = WeaponCommand(user=char, weapon=wpn, targets=[target], bus=gs.bus)
                else:
                    bark_dichiarazione = f"Pugni nudi! (Mio Atk {atk_base} vs Def nemica {def_nemico})"
                    cmd = AttackCommand(char, target)

                risultato_stringa = cmd.execute()

                if "inceppat" in risultato_stringa.lower():
                    bark = get_bark(BATTLE_PLAYER_BARKS, f"weapon_jam_{char.name.lower()}")
                    self._bubbles.add_from_bark(bark)
                elif "manca" in risultato_stringa.lower():
                    bark = get_bark(BATTLE_PLAYER_BARKS, f"skill_fail_{char.name.lower()}")
                    self._bubbles.add_from_bark(bark)
                else:
                    if wpn:
                        bark = get_bark(BATTLE_PLAYER_BARKS, f"attack_weapon_{char.name.lower()}")
                    else:
                        bark = get_bark(BATTLE_PLAYER_BARKS, f"attack_melee_{char.name.lower()}")
                    self._bubbles.add_from_bark(bark)

            if gs.Rivet.is_alive():
                if self._renderer: self._renderer.trigger_attack("Rivet")
                _esegui_attacco_con_report(gs.Rivet, valid_targets[0])

            if gs.Echo.is_alive():
                target_echo = valid_targets[1] if len(valid_targets) > 1 else valid_targets[0]
                if self._renderer: self._renderer.trigger_attack("Echo")
                _esegui_attacco_con_report(gs.Echo, target_echo)

            self._advance_turn(gs)

        elif action == "item":
            self._item_list = []
            aggregated = {}

            for char in [gs.Rivet, gs.Echo]:
                if char.is_alive():
                    for it in char.inventory.get_by_type(ItemType.CONSUMABLE):
                        if it.item_id == "piranha_solution" and getattr(gs, "_piranha_used_this_battle", False):
                            continue
                        if it.item_id not in aggregated:
                            aggregated[it.item_id] = it.clone()
                        else:
                            aggregated[it.item_id].quantity += it.quantity

            if not aggregated:
                gs.log(gs.blog, "Nessun consumabile disponibile!")
                self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, "item_empty"))
                self._player_acted = False
            else:
                self._item_list = list(aggregated.values())
                self.sel_state  = "sel_item"
                self.sel_cursor = 0
                self._player_acted = False

        elif action == "combo":

            if not gs.Rivet.is_alive() or not gs.Echo.is_alive():
                gs.log(gs.blog, "COMBO impossibile: entrambi devono essere vivi!")
                self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, "combo_fail"))
                self._player_acted = False
                return

            if getattr(gs, "_combo_used_this_battle", False):
                gs.log(gs.blog, "COMBO non disponibile: può essere usata solo 1 volta per battaglia!")
                self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, "combo_fail"))
                self._player_acted = False
                return

            r_hp = gs.Rivet.stats.hp
            e_hp = gs.Echo.stats.hp

            condizione_disperazione = (r_hp < 30 and e_hp < 30)

            condizione_sacrificio = ((r_hp <= 10 or e_hp <= 10) and gs.ethics == 10)

            if not (condizione_disperazione or condizione_sacrificio):
                gs.log(gs.blog, "COMBO bloccata: HP troppo alti o Etica insufficiente!")
                self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, "combo_fail"))
                self._player_acted = False
                return

            target = min(alive_enemies, key=lambda e: e.stats.hp)

            gs._combo_used_this_battle = True

            cmd = ComboCommand(initiator=gs.Rivet, partner=gs.Echo, target=target)
            result = cmd.execute()
            gs.log(gs.blog, result)

            self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, "combo_exec"))
            self._advance_turn(gs)

        elif action == "flee":
            import random
            if random.random() < 0.5:
                _bark_flee_ok = get_bark(BATTLE_PLAYER_BARKS, "flee_success")
                gs.log(gs.blog, _bark_flee_ok)
                self._bubbles.add_from_bark(_bark_flee_ok)

                npc = getattr(gs, "current_battle_npc", None)
                if npc is not None:
                    npc["saved_enemies"] = [e for e in alive_enemies]

                gs.end_battle(victory=True, fled=True)

                if npc is not None:
                    npc_key = (npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"]))
                    if npc_key in gs.defeated_npcs:
                        gs.defeated_npcs.remove(npc_key)
            else:
                _bark_flee_fail = get_bark(BATTLE_PLAYER_BARKS, "flee_fail")
                gs.log(gs.blog, _bark_flee_fail)
                self._bubbles.add_from_bark(_bark_flee_fail)
                self._advance_turn(gs)


    def _use_selected_item(self):
        gs = GameManager.get_instance()

        if not self._item_list or self.sel_cursor >= len(self._item_list):
            self.sel_state = "main"
            return

        item_info     = self._item_list[self.sel_cursor]
        alive_enemies = [e for e in gs.enemies if e.is_alive()]
        chars_alive   = [c for c in [gs.Rivet, gs.Echo] if c.is_alive()]

        item_owner = None
        for char in [gs.Rivet, gs.Echo]:
            if char.inventory.get_item(item_info.item_id):
                item_owner = char
                break

        if not item_owner:
            self.sel_state = "main"; return

        heal_target = min(chars_alive, key=lambda c: c.stats.hp / c.stats.max_hp) if chars_alive else item_owner

        bark_key = "use_item_rivet" if item_owner.name == "Rivet" else "use_item_echo"
        self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, bark_key))

        cmd = ItemCommand(
            user=item_owner,
            item_id=item_info.item_id,
            targets=alive_enemies,
            heal_target=heal_target,
        )
        cmd.execute()

        _item_obj = item_owner.inventory.get_item(item_info.item_id) or __import__('types').SimpleNamespace(hp_restore=0)
        _heals = getattr(_item_obj, 'hp_restore', 0) > 0
        if _heals:
            if heal_target is gs.Rivet:
                gs._rivet_healed_in_battle = True
            elif heal_target is gs.Echo:
                gs._echo_healed_in_battle = True

        self.sel_state  = "main"
        self._item_list = []
        self._advance_turn(gs)

    def _exec_skill_direct(self, rivet_skill, echo_skill):
        gs  = GameManager.get_instance()
        alive_enemies = [e for e in gs.enemies if e.is_alive()]
        if not alive_enemies:
            return

        self._player_acted = True
        valid_targets = self._get_valid_targets(alive_enemies)

        def _esegui_skill_con_report(char, skill, target):
            if skill:
                cmd = SkillCommand(user=char, skill_node=skill, target=target, targets_list=alive_enemies)
                result = cmd.execute()

                if any(parola in result.lower() for parola in ["manca", "fallisce", "nessun effetto"]):
                    bark = get_bark(BATTLE_PLAYER_BARKS, f"skill_fail_{char.name.lower()}")
                    self._bubbles.add_from_bark(bark)
                else:
                    bark = get_bark(BATTLE_PLAYER_BARKS, f"use_skill_{char.name.lower()}")
                    self._bubbles.add_from_bark(bark)
            else:
                wpn = getattr(char, "equipped_weapon", None)
                if wpn:
                    WeaponCommand(user=char, weapon=wpn, targets=[target], bus=gs.bus).execute()
                    self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, f"attack_weapon_{char.name.lower()}"))
                else:
                    AttackCommand(char, target).execute()
                    self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, f"attack_melee_{char.name.lower()}"))

        if gs.Rivet.is_alive():
            if self._renderer: self._renderer.trigger_attack("Rivet")
            _esegui_skill_con_report(gs.Rivet, rivet_skill, valid_targets[0])

        if gs.Echo.is_alive():
            target_echo = valid_targets[1] if len(valid_targets) > 1 else valid_targets[0]
            if self._renderer: self._renderer.trigger_attack("Echo")
            _esegui_skill_con_report(gs.Echo, echo_skill, target_echo)

        self._advance_turn(gs)

    def _next_weapon_step(self):
        """Gestisce il passaggio tra le selezioni di Rivet ed Echo."""
        if self.needs_rivet:
            self.needs_rivet = False
            self.sel_state = "sel_rivet"
            self.sel_cursor = 0
        elif self.needs_echo:
            self.needs_echo = False
            self.sel_state = "sel_echo"
            self.sel_cursor = 0
        else:
            self.sel_state = "main"
            self._exec_action("attack")

    def _confirm_skill_selection(self):
        """Chiamato quando il giocatore conferma una skill (Rivet o Echo)."""
        gs = GameManager.get_instance()
        if not self._skill_list or self.sel_cursor >= len(self._skill_list):
            self.sel_state = "main"
            return

        chosen = self._skill_list[self.sel_cursor]

        if self.sel_state == "sel_skill_rivet":
            self._pending_rivet_skill = chosen
            echo_skills = gs.Echo.skill_wheel.get_combat_skills(gs.Echo.stats.tech_points) if gs.Echo.is_alive() else []
            if echo_skills:
                self._skill_list = echo_skills
                self.sel_cursor  = 0
                self.sel_state   = "sel_skill_echo"
            else:
                self.sel_state   = "main"
                self._skill_list = []
                self._exec_skill_direct(rivet_skill=self._pending_rivet_skill, echo_skill=None)

        elif self.sel_state == "sel_skill_echo":
            echo_skill  = chosen
            rivet_skill = getattr(self, "_pending_rivet_skill", None)
            self.sel_state   = "main"
            self._skill_list = []
            self._exec_skill_direct(rivet_skill=rivet_skill, echo_skill=echo_skill)


    def _advance_turn(self, gs) -> None:
        """Forza l'alternanza rigida: giocatore -> piccola pausa -> nemico -> giocatore."""

        if gs.turn == "player":
            gs.turn = "enemy"
            self._enemy_timer = self.ENEMY_TURN_DELAY
            alive_e = [e for e in gs.enemies if e.is_alive()]
            if alive_e:
                nomi = ", ".join(e.name for e in alive_e)
                gs.log(gs.blog, f"⚠ {nomi} sta per contrattaccare…")
        else:
            gs.turn = "player"
            self._player_acted = False

            if gs.Rivet.is_alive():
                gs.Rivet.stats.process_turn_effects()
            if gs.Echo.is_alive():
                gs.Echo.stats.process_turn_effects()

            if gs.Rivet.is_alive():
                gs.Rivet.skill_wheel.tick()
            if gs.Echo.is_alive():
                gs.Echo.skill_wheel.tick()

    def _enemy_turn(self):
        gs = GameManager.get_instance()
        alive_e = [e for e in gs.enemies if e.is_alive()]

        for e in alive_e:
            if not e.is_alive(): continue

            faction = getattr(e, 'faction', 'zombie').lower()

            if hasattr(e.stats, "has_skip_effect") and e.stats.has_skip_effect():
                gs.log(gs.blog, f"  {e.name} è stordito/confuso e perde il turno!")
                continue

            if hasattr(e.stats, "process_turn_effects"):
                e.stats.process_turn_effects()

            tgts = [c for c in [gs.Rivet, gs.Echo] if c.is_alive()]
            if not tgts: break

            mv = e.decide_battle_move(tgts)
            action = mv.get("action")

            if action == "flee":
                e.stats.hp = 0
                _bark_e_flee = f"{e.name}: {get_bark(ENEMY_BARKS[faction], 'flee')}"
                gs.log(gs.blog, _bark_e_flee)
                self._bubbles.add("enemy", _bark_e_flee, duration=2500)
                continue

            if action == "summon" or action == "summon_and_flee":
                _bark_e_summon = f"{e.name}: {get_bark(ENEMY_BARKS[faction], 'summon')}"
                gs.log(gs.blog, _bark_e_summon)
                self._bubbles.add("enemy", _bark_e_summon, duration=2500)

                MAX_ENEMIES = 3
                entity = mv.get("entity", "infetto")
                qty    = mv.get("qty", 1)
                spawned = 0
                for _ in range(qty):
                    if len(gs.enemies) >= MAX_ENEMIES:
                        break
                    if entity == "infetto":
                        new_e = EnemyFactory.create_infetto()
                    elif entity == "orda":
                        new_e = EnemyFactory.create_orda(commander=e)
                    else:
                        new_e = EnemyFactory.create_infetto()
                    gs.enemies.append(new_e)
                    gs.log(gs.blog, f"  \u21b3 {new_e.name} entra in battaglia!")
                    spawned += 1

                if spawned > 0 and self._renderer:
                    self._renderer.setup_enemies(gs.enemies)

                if action == "summon_and_flee":
                    e.stats.hp = 0
                    gs.log(gs.blog, f"  \u21b3 {e.name} fugge approfittando della confusione!")

            elif action in ["attack", "special", "tentacle"]:
                targets_hit = mv.get("targets", [mv.get("target")] if mv.get("target") else [])
                targets_hit = [t for t in targets_hit if t is not None and t.is_alive()]
                power = mv.get("power", e.stats.atk)

                _bark_e_atk = get_bark(ENEMY_BARKS.get(faction, ENEMY_BARKS["zombie"]), "attack")
                self._bubbles.add("enemy", _bark_e_atk, duration=3500)

                for tgt in targets_hit:
                    if self._renderer:
                        idx = gs.enemies.index(e)
                        self._renderer.trigger_enemy_attack(idx)

                    has_evasione = any(getattr(eff, "name", "") == "Evasione" for eff in getattr(tgt.stats, "active_effects", []))
                    if has_evasione:
                        tgt.stats.active_effects = [eff for eff in tgt.stats.active_effects if getattr(eff, "name", "") != "Evasione"]

                        bark_evade = get_bark(BATTLE_PLAYER_BARKS, f"evade_success_{tgt.name.lower()}")
                        self._bubbles.add_from_bark(bark_evade)
                        continue

                    if power > 0:
                        dmg = tgt.stats.take_damage(power)

                        if dmg > 0:
                            bark_dmg = get_bark(BATTLE_PLAYER_BARKS, f"take_damage_{tgt.name.lower()}")
                            self._bubbles.add_from_bark(bark_dmg)
                        else:
                            bark_zero = get_bark(BATTLE_PLAYER_BARKS, f"zero_damage_{tgt.name.lower()}")
                            self._bubbles.add_from_bark(bark_zero)

                    st_effect = mv.get("status_effect")
                    if st_effect:
                        if hasattr(tgt.stats, "add_effect"):
                            tgt.stats.add_effect(StatusEffect(name=st_effect["name"], duration=st_effect["duration"], delta_hp=-st_effect["damage"]))

                        bark_status = get_bark(BATTLE_PLAYER_BARKS, "status_effect_hit")
                        self._bubbles.add_from_bark(bark_status)

        self._advance_turn(gs)
        if gs.turn == "enemy":
            gs.turn = "player"
        self._check_end()

    def _check_end(self):
        gs = GameManager.get_instance()

        for e in list(gs.enemies):
            if not e.is_alive() and hasattr(e, "respawn_chance") and e.respawn_chance > 0:
                if not getattr(e, "_has_reanimated", False):
                    import random
                    if random.random() < e.respawn_chance:
                        e.stats.hp = max(1, e.stats.max_hp // 3)
                        e._has_reanimated = True
                        gs.log(gs.blog, f"  ↳ {e.name} si RIANIMA! HP ripristinati parzialmente!")

        if all(not e.is_alive() for e in gs.enemies):
            raw_xp = sum(e.stats.max_hp // 5 for e in gs.enemies)
            if not gs.Rivet or not gs.Echo:
                return
            total_atk = gs.Rivet.stats.atk + gs.Echo.stats.atk
            xp_r = int(raw_xp * gs.Rivet.stats.atk / total_atk * 2) if total_atk else raw_xp // 2
            xp_e = int(raw_xp * gs.Echo.stats.atk  / total_atk * 2) if total_atk else raw_xp // 2
            rivet_healed = getattr(gs, '_rivet_healed_in_battle', False)
            echo_healed  = getattr(gs, '_echo_healed_in_battle',  False)
            msgs_r = gs.Rivet.stats.gain_xp(xp_r, healed_in_battle=rivet_healed)
            msgs_e = gs.Echo.stats.gain_xp(xp_e,  healed_in_battle=echo_healed)
            gs._rivet_healed_in_battle = False
            gs._echo_healed_in_battle  = False
            gs.modify_ethics(+1)
            heal_note_r = " (malus cura)" if rivet_healed else ""
            heal_note_e = " (malus cura)" if echo_healed  else ""
            gs.log(gs.wlog, f"✔ Vittoria! Rivet +{xp_r} XP{heal_note_r}  Echo +{xp_e} XP{heal_note_e}  Etica {gs.ethics:+d}")
            for m in msgs_r: gs.log(gs.wlog, f"[Rivet] {m}")
            for m in msgs_e: gs.log(gs.wlog, f"[Echo] {m}")
            import random
            bark_win = "battle_won_rivet" if random.random() < 0.5 else "battle_won_echo"
            self._bubbles.add_from_bark(get_bark(BATTLE_PLAYER_BARKS, bark_win))
            if gs.bus:
                for e in gs.enemies:
                    enemy_type = "zombie"
                    name_lower = e.name.lower()
                    if "gigante" in name_lower: enemy_type = "giant"
                    elif "sulfureo" in name_lower: enemy_type = "sulfur_zombie"
                    elif "razziatore" in name_lower: enemy_type = "razziatore"
                    elif "solidale" in name_lower: enemy_type = "solidale"
                    elif "corazzato" in name_lower: enemy_type = "corazzato"
                    elif "orda" in name_lower: enemy_type = "orda"
                    elif "infetto" in name_lower: enemy_type = "infetto"

                    gs.bus.publish(EventType.ENEMY_KILLED, {"enemy_type": enemy_type})
            if gs.combo_cooldown > 0:
                gs.combo_cooldown -= 1
                if gs.combo_cooldown > 0:
                    gs.log(gs.wlog, f"⚡ Combo disponibile tra {gs.combo_cooldown} battaglia/e.")
                else:
                    gs.log(gs.wlog, "⚡ Combo nuovamente disponibile!")
            npc = getattr(gs, "current_battle_npc", None)
            if npc and "pos" in npc:
                gs.defeated_npcs.add((npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"])))
            gs.end_battle(victory=True)

        elif gs.Rivet and gs.Echo and (not gs.Rivet.is_alive() or not gs.Echo.is_alive()):
            fallen = "Rivet" if not gs.Rivet.is_alive() else "Echo"
            gs.set_gameover(f"{fallen} è caduto in battaglia. La missione è fallita.")
            gs.end_battle(victory=False)

    def on_enter(self):
        """Chiamato ogni volta che si entra nella schermata battaglia — resetta renderer e hbar."""
        _gs = _GM.get_instance()
        _gs._piranha_used_this_battle   = False
        _gs._combo_used_this_battle     = False
        _gs._rivet_healed_in_battle     = False
        _gs._echo_healed_in_battle      = False
        _gs._rattoppo_used_this_battle  = False
        _gs._fusione_used_this_battle   = False
        _gs._miraggio_used_this_battle  = False
        self._renderer    = None
        self._hbars       = {}
        self._hbar_group  = None
        self._enemy_timer = 0
        self._player_acted = False

        npc = getattr(_gs, "current_battle_npc", None)
        if npc and "saved_enemies" in npc:
            _gs.enemies = npc["saved_enemies"]
        elif npc and "pos" in npc:
            # Ripristina gli HP dei nemici parzialmente danneggiati (dopo fuga)
            npc_key = (npc.get("name", ""), tuple(npc.get("_local_pos") or npc["pos"]))
            hp_list = getattr(_gs, "fled_npc_hp", {}).get(npc_key)
            if hp_list:
                for enemy, saved_hp in zip(_gs.enemies, hp_list):
                    if hasattr(enemy, "stats"):
                        enemy.stats.hp = max(1, saved_hp)

        self._ensure_renderer()

    def _ensure_renderer(self):
        gs = GameManager.get_instance()
        if self._renderer is not None:
            return
        if gs.Rivet_sprite is None or gs.Echo_sprite is None:
            return
        self._renderer = BattleRenderer(gs.Rivet_sprite, gs.Echo_sprite)
        if gs.enemies:
            self._renderer.setup_enemies(gs.enemies)

    def _ensure_hbars(self, gs) -> None:
        """Costruisce le HealthBar lazily la prima volta o se cambiano i nemici.

        Composite GoF: le HealthBar vengono aggiunte a un WidgetGroup.
        Il ciclo di draw/update usa _hbar_group.draw(surf) e _hbar_group.update()
        invece di iterare manualmente su _hbars.values().
        """
        fn = self.fonts["sm"]
        bar_w, bar_h = 200, 14
        if "Rivet" not in self._hbars:
            self._hbars["Rivet"] = HealthBar((100, 85, bar_w, bar_h), fn)
            self._hbars["Echo"]  = HealthBar((100, 115, bar_w, bar_h), fn)
        n_enemies = len(gs.enemies)
        if sum(1 for k in self._hbars if k.startswith("e")) != n_enemies:
            for i in range(n_enemies):
                self._hbars[f"e{i}"] = HealthBar((180, 145 + i * 30, bar_w, bar_h), fn)
        self._hbar_group = WidgetGroup()
        for hb in self._hbars.values():
            self._hbar_group.add(hb)

    def _get_valid_targets(self, alive_enemies: list) -> list:
        """Filtra i nemici vivi: se c'è un nemico in 'taunt' (es. Orda), forza la mira su di lui."""
        taunters = [e for e in alive_enemies if getattr(e, "is_taunting", False)]
        if taunters:
            return taunters
        return alive_enemies

    def _consolidate_weapons(self, char) -> None:
        """Riunisce le armi duplicate sommando le munizioni e rimuovendo i cloni."""
        if not char or not hasattr(char, "weapons"):
            return

        unique_weapons = {}
        to_remove = []

        for w in char.weapons:
            if w.item_id in unique_weapons:
                existing = unique_weapons[w.item_id]
                if existing.ammo >= 0 and w.ammo >= 0:
                    existing.ammo += w.ammo
                else:
                    existing.ammo = -1
                to_remove.append(w)
            else:
                unique_weapons[w.item_id] = w

        for dup in to_remove:
            if dup in char.weapons:
                char.weapons.remove(dup)

        if getattr(char, "equipped_weapon", None) in to_remove:
            char.equipped_weapon = unique_weapons[char.equipped_weapon.item_id]

    def update(self):
        self._anim += 0.05
        if self._hbar_group:
            self._hbar_group.update()
        gs = GameManager.get_instance()
        if gs.turn == "enemy":
            if self._enemy_timer > 0:
                self._enemy_timer -= 1

            if self._enemy_timer <= 0:
                self._enemy_turn()

    def draw(self, surf: Surface):
        self._hovered_tooltip = None

        gs = GameManager.get_instance()
        fn  = self.fonts

        surf.blit(self.background, (0, 0))

        is_player = (gs.turn == "player")
        if is_player:
            turn_txt     = "IL TUO TURNO"
            instruct_txt = "Scegli un'azione"
            turn_col     = GREEN
        else:
            secs = max(1, round(self._enemy_timer / 60))
            turn_txt     = "TURNO NEMICI"
            instruct_txt = f"Attacco tra {secs}s…"
            turn_col     = RED

        pulse = int(200 + 55 * math.sin(self._anim * 3))
        tc    = (0, pulse, 0) if is_player else (pulse, 0, 0)

        p_w, p_h = 380, 56
        p_x, p_y = W // 2 - 190, 12
        p_center_y = p_y + (p_h // 2)

        top_panel = pygame.Surface((p_w, p_h), pygame.SRCALPHA)
        top_panel.fill((15, 18, 25, 215))

        pygame.draw.rect(top_panel, tc, (0, 0, p_w, p_h), 2, border_radius=8)
        pygame.draw.line(top_panel, tc, (4, 0), (p_w - 4, 0), 2)
        surf.blit(top_panel, (p_x, p_y))

        pygame.draw.circle(surf, tc, (p_x + 18, p_center_y), 7)
        pygame.draw.circle(surf, (15, 18, 25), (p_x + 18, p_center_y), 4)

        txt(surf, turn_txt, W // 2, p_y + 18, tc, fn["bold"], center=True)
        txt(surf, instruct_txt, W // 2, p_y + 38, GREY, fn["sm"], center=True)

        self._ensure_renderer()
        if self._renderer:
            self._renderer.draw(
                surf, x=0, y=0, w=W, h=H, dt=50,
                Rivet=gs.Rivet, Echo=gs.Echo, enemies=gs.enemies,
                font_sm=fn["sm"],
            )

        self._draw_party_cards(surf, gs, fn)
        self._draw_enemy_cards(surf, gs, fn)

        self._draw_action_bar(surf, gs, fn, is_player)

        _bubble_pos_battle: dict[str, tuple[int, int]] = {
            "Rivet": (_BR.PARTY_POSITIONS[0][0] + 30, _BR.PARTY_POSITIONS[0][1] + 70),
            "Echo":  (_BR.PARTY_POSITIONS[1][0] + 30, _BR.PARTY_POSITIONS[1][1] + 70),
            "enemy": (_BR.ENEMY_POSITIONS[0][0] + 30, _BR.ENEMY_POSITIONS[0][1] + 70),
        }
        self._bubbles.draw(surf, fn["sm"], _bubble_pos_battle)

        if self.sel_state == "sel_item":
            self._draw_item_popup(surf, gs, fn)
        elif self.sel_state in ("sel_rivet", "sel_echo"):
            self._draw_weapon_popup(surf, gs, fn)
        elif self.sel_state in ("sel_skill_rivet", "sel_skill_echo"):
            self._draw_skill_popup(surf, gs, fn)

        if self._hovered_tooltip:
            self._draw_hover_tooltip(surf, self._hovered_tooltip, self._mouse_pos)

    def _draw_party_cards(self, surf, gs, fn):
        bar_w = 200
        py0   = 90

        for char_idx, (char, label) in enumerate([(gs.Rivet, "Rivet"), (gs.Echo, "Echo")]):
            if char is None or not char.is_alive():
                py0 += 90
                continue

            card_h  = 80
            card_bg = (20, 25, 32) if char_idx == 0 else (28, 20, 32)
            card_border = (40, 50, 60)

            pygame.draw.rect(surf, card_bg, (14, py0, bar_w + 24, card_h), border_radius=6)
            pygame.draw.rect(surf, card_border, (14, py0, bar_w + 24, card_h), 1, border_radius=6)

            hp_ratio = char.stats.hp / max(1, char.stats.max_hp)
            name_col = GREEN if hp_ratio > 0.5 else (YELLOW if hp_ratio > 0.2 else RED)

            pygame.draw.rect(surf, name_col, (20, py0 + 12, 4, 16), border_radius=2)
            txt(surf, f"{label}  Lv.{char.stats.level}", 30, py0 + 10, name_col, fn["bold"])

            weapon = getattr(char, "equipped_weapon", None)
            card_inner_w = bar_w + 24 - 16
            if weapon:
                ammo_str = "[inf]" if weapon.ammo < 0 else f"[{weapon.ammo}]"
                full_wpn = f"{weapon.display_name} {ammo_str}"
                max_chars = max(10, (card_inner_w - 8) // 7)
                if len(full_wpn) > max_chars:
                    full_wpn = full_wpn[:max_chars - 1] + "…"
                txt(surf, full_wpn, 28, py0 + 30, YELLOW, fn["sm"])
            else:
                txt(surf, "Disarmato", 28, py0 + 30, DARKGREY, fn["sm"])

            pygame.draw.rect(surf, RED, (20, py0 + 52, 8, 8), border_radius=2)
            hp_bar(surf, 32, py0 + 52, char.stats.hp, char.stats.max_hp, bar_w, 8, fn["sm"])

            gloss = pygame.Surface((bar_w, 4), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 30))
            surf.blit(gloss, (32, py0 + 52))

            py0 += card_h + 10

    def _draw_enemy_cards(self, surf, gs, fn):
        bar_w = 200
        ey0   = 90

        for i, e in enumerate(gs.enemies):
            if not e.is_alive():
                ey0 += 90
                continue

            card_h     = 68
            card_bg    = (30, 14, 14)
            card_border = (80, 30, 30)

            cx = W - bar_w - 38
            pygame.draw.rect(surf, card_bg, (cx, ey0, bar_w + 24, card_h), border_radius=6)
            pygame.draw.rect(surf, card_border, (cx, ey0, bar_w + 24, card_h), 1, border_radius=6)

            txt(surf, f"[{i+1}] {e.name}", cx + 12, ey0 + 10, RED, fn["bold"])

            pygame.draw.rect(surf, RED, (cx + 8, ey0 + 40, 8, 8), border_radius=2)

            hp_bar(surf, cx + 20, ey0 + 40, e.stats.hp, e.stats.max_hp, bar_w, 8, fn["sm"])

            gloss = pygame.Surface((bar_w, 4), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 30))
            surf.blit(gloss, (cx + 20, ey0 + 40))

            ey0 += card_h + 10

    def _draw_action_bar(self, surf, gs, fn, is_player):
        panel_h = 120
        panel_y = H - panel_h

        bot_panel = pygame.Surface((W, panel_h), pygame.SRCALPHA)
        bot_panel.fill((10, 12, 18, 235))
        surf.blit(bot_panel, (0, panel_y))
        pygame.draw.line(surf, CYAN, (0, panel_y), (W, panel_y), 2)

        txt(surf, "AZIONI DI BATTAGLIA", W // 2, panel_y + 12, (100, 110, 120), fn["sm"], center=True)

        buttons_locked = not is_player or self._player_acted

        btn_w  = (W - 60) // 6
        btn_h  = 58
        gap_x  = 6
        total_w = 6 * btn_w + 5 * gap_x
        ax0    = (W - total_w) // 2
        ay0    = panel_y + 28

        _btn_colors = [RED, MAGENTA, GREEN, CYAN, YELLOW, GREY]

        for i, ((label, act), meta) in enumerate(zip(BATTLE_ACTIONS, BATTLE_ACTION_META)):
            bx = ax0 + i * (btn_w + gap_x)
            by = ay0

            is_sel = (i == gs.bat_cursor and not buttons_locked)
            is_combo_locked = False

            if act == "combo":
                if getattr(gs, "_combo_used_this_battle", False):
                    is_combo_locked = True
                else:
                    r_hp = gs.Rivet.stats.hp if gs.Rivet and gs.Rivet.is_alive() else 100
                    e_hp = gs.Echo.stats.hp if gs.Echo and gs.Echo.is_alive() else 100
                    cond_a = (r_hp < 30 and e_hp < 30)
                    cond_b = ((r_hp <= 10 or e_hp <= 10) and gs.ethics == 10)
                    if not (cond_a or cond_b):
                        is_combo_locked = True

            if buttons_locked:
                bcol = DARKGREY
            else:
                bcol = _btn_colors[i % len(_btn_colors)]
                if act == "combo" and is_combo_locked:
                    bcol = GREY

            bg_col = (10, 60, 80) if is_sel else (25, 30, 35)
            pygame.draw.rect(surf, bg_col, (bx, by, btn_w, btn_h), border_radius=6)
            pygame.draw.line(surf, bcol, (bx + 4, by), (bx + btn_w - 4, by), 2)
            if is_sel:
                pygame.draw.rect(surf, bcol, (bx, by, btn_w, btn_h), 1, border_radius=6)

            ico = self.simboli_font_lg.render(meta["sym"], True, bcol)
            surf.blit(ico, (bx + btn_w - ico.get_width() - 4, by + 6))
            txt(surf, f"[{meta['key']}]", bx + 6, by + 6, WHITE, fn["sm"])

            disp_label = label
            if act == "combo":
                if getattr(gs, "_combo_used_this_battle", False):
                    disp_label = "Combo (Usata)"
                elif is_combo_locked:
                    disp_label = "Combo (Bloccata)"

            txt(surf, disp_label, bx + 6, by + 22, (150, 160, 170) if not is_sel else bcol, fn["sm"])

        self._draw_hint_with_bold_keys(surf, W // 2, H - 12, GREY, [
            ("⇆ ", True), ("naviga   ", False),
            ("INVIO ", True), ("conferma   ", False),
            ("(o tasto rapido)", False),
        ])

    def _draw_item_popup(self, surf, gs, fn):
        items = self._item_list
        max_vis = min(len(items), 8)
        ph = max(160, 100 + max_vis * 30 + 40)
        pw = 500
        px = (W - pw) // 2
        py = max(120, H // 2 - ph // 2)

        pygame.draw.rect(surf, (15, 25, 20, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, YELLOW, (px, py, pw, ph), 2, border_radius=8)
        pygame.draw.line(surf, YELLOW, (px + 4, py), (px + pw - 4, py), 2)

        ico_title = self.simboli_font.render("💊", True, YELLOW)
        surf.blit(ico_title, (px + 16, py + 14))
        txt(surf, "Usa Consumabile", px + 16 + ico_title.get_width() + 8, py + 16, YELLOW, fn["bold"])
        sep(surf, px + 10, py + 38, pw - 20, YELLOW)

        for i, it in enumerate(items[:max_vis]):
            iy  = py + 50 + i * 30
            sel = (i == self.sel_cursor)
            col = WHITE if sel else GREY

            rect = pygame.Rect(px + 10, iy - 2, pw - 20, 28)
            if rect.collidepoint(self._mouse_pos):
                self._hovered_tooltip = _BATTLE_TOOLTIPS.get(it.name, f"Oggetto: {it.name}")

            if sel:
                pygame.draw.rect(surf, (20, 50, 30), (px + 10, iy - 2, pw - 20, 28), border_radius=4)
                ico_cur = self.simboli_font.render("➤", True, YELLOW)
                surf.blit(ico_cur, (px + 14, iy))

            ico_str = "💊"
            if getattr(it, 'damage', 0) > 0 and getattr(it, 'hp_restore', 0) == 0:
                ico_str = "💣"
            ico_item = self.simboli_font.render(ico_str, True, col)
            surf.blit(ico_item, (px + 36, iy))

            if it.hp_restore > 0 and it.damage > 0: eff = f"+{it.hp_restore}HP / {it.damage}DMG"
            elif it.hp_restore > 0:                  eff = f"+{it.hp_restore} HP"
            else:                                     eff = f"{it.damage} DMG (AoE)"

            txt(surf, f"{it.name} ×{it.quantity}  [Squadra]", px + 66, iy, col, fn["sm"])
            txt(surf, eff, px + pw - 110, iy, GREEN if "HP" in eff else YELLOW, fn["sm"])

        sep(surf, px + 10, py + ph - 38, pw - 20, YELLOW)
        self._draw_hint_with_bold_keys(surf, px + pw // 2, py + ph - 22, DARKGREY, [
            ("↑↓ ", True), ("seleziona   ", False),
            ("INVIO ", True), ("usa   ", False),
            ("ESC ", True), ("annulla", False),
        ])

    def _draw_weapon_popup(self, surf, gs, fn):
        char = gs.Rivet if self.sel_state == "sel_rivet" else gs.Echo
        border_col = CYAN if self.sel_state == "sel_rivet" else MAGENTA
        pw = 440
        ph = max(150, 80 + len(char.weapons) * 28 + 40)
        px = (W - pw) // 2
        py = (H - ph) // 2

        pygame.draw.rect(surf, (15, 18, 25, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, border_col, (px, py, pw, ph), 2, border_radius=8)
        pygame.draw.line(surf, border_col, (px + 4, py), (px + pw - 4, py), 2)

        ico_title = self.simboli_font.render("🔫", True, YELLOW)
        surf.blit(ico_title, (px + 16, py + 14))
        txt(surf, f"Scegli arma — {char.name}", px + 16 + ico_title.get_width() + 8, py + 16, YELLOW, fn["bold"])
        sep(surf, px + 10, py + 38, pw - 20, border_col)

        for i, w in enumerate(char.weapons):
            iy  = py + 50 + i * 28
            sel = (i == self.sel_cursor)
            col = WHITE if sel else GREY

            rect = pygame.Rect(px + 10, iy - 2, pw - 20, 26)
            if rect.collidepoint(self._mouse_pos):
                self._hovered_tooltip = _BATTLE_TOOLTIPS.get(w.display_name, f"Arma: {w.display_name}")

            if sel:
                pygame.draw.rect(surf, (20, 40, 50), (px + 10, iy - 2, pw - 20, 26), border_radius=4)
                ico_cur = self.simboli_font.render("➤", True, border_col)
                surf.blit(ico_cur, (px + 14, iy))

            ico_wpn = self.simboli_font.render("🔫", True, col)
            surf.blit(ico_wpn, (px + 36, iy))
            ammo = f"[{w.ammo}]" if w.ammo >= 0 else "[∞]"
            txt(surf, f"{w.display_name} {ammo}", px + 66, iy, col, fn["sm"])

        sep(surf, px + 10, py + ph - 38, pw - 20, border_col)
        self._draw_hint_with_bold_keys(surf, px + pw // 2, py + ph - 22, DARKGREY, [
            ("↑↓ ", True), ("seleziona   ", False),
            ("INVIO ", True), ("conferma   ", False),
            ("ESC ", True), ("annulla", False),
        ])

    def _draw_skill_popup(self, surf, gs, fn):
        skills      = self._skill_list
        who_label   = "Rivet" if self.sel_state == "sel_skill_rivet" else "Echo"
        border_col  = CYAN if self.sel_state == "sel_skill_rivet" else MAGENTA
        step_txt    = "Passo 1/2" if self.sel_state == "sel_skill_rivet" else "Passo 2/2"

        pw = 480
        ph = max(160, 80 + len(skills) * 30 + 40)
        px = (W - pw) // 2
        py = max(120, H // 2 - ph // 2)

        pygame.draw.rect(surf, (15, 18, 25, 240), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surf, border_col, (px, py, pw, ph), 2, border_radius=8)
        pygame.draw.line(surf, border_col, (px + 4, py), (px + pw - 4, py), 2)

        ico_title = self.simboli_font.render("✨", True, border_col)
        surf.blit(ico_title, (px + 16, py + 14))
        txt(surf, f"Skill — {who_label}  [{step_txt}]", px + 16 + ico_title.get_width() + 8, py + 16, border_col, fn["bold"])
        sep(surf, px + 10, py + 38, pw - 20, border_col)

        for i, sk in enumerate(skills):
            sy  = py + 50 + i * 30
            sel = (i == self.sel_cursor)
            col = WHITE if sel else GREY

            rect = pygame.Rect(px + 10, sy - 2, pw - 20, 28)
            if rect.collidepoint(self._mouse_pos):
                self._hovered_tooltip = _BATTLE_TOOLTIPS.get(sk.name, sk.name)

            if sel:
                pygame.draw.rect(surf, (20, 40, 50), (px + 10, sy - 2, pw - 20, 28), border_radius=4)
                ico_cur = self.simboli_font.render("➤", True, border_col)
                surf.blit(ico_cur, (px + 14, sy))

            ico_sk = self.simboli_font.render("⚡", True, col)
            surf.blit(ico_sk, (px + 36, sy))

            cd_txt   = f"  CD:{sk.max_cooldown}" if sk.max_cooldown > 0 else ""
            rate_txt = f"  {int(sk.success_rate * 100)}%"
            txt(surf, f"{sk.name}{rate_txt}{cd_txt}", px + 66, sy, col, fn["sm"])

        sep(surf, px + 10, py + ph - 38, pw - 20, border_col)
        self._draw_hint_with_bold_keys(surf, px + pw // 2, py + ph - 22, DARKGREY, [
            ("↑↓ ", True), ("seleziona   ", False),
            ("INVIO ", True), ("conferma   ", False),
            ("ESC ", True), ("annulla", False),
        ])

    def _draw_hover_tooltip(self, surf, text, pos):
        fn = self.fonts["sm"]
        max_w = 300

        words = text.split()
        lines = []
        cur = []
        for w in words:
            if fn.size(" ".join(cur + [w]))[0] <= max_w:
                cur.append(w)
            else:
                if cur: lines.append(" ".join(cur))
                cur = [w]
        if cur: lines.append(" ".join(cur))

        line_h = fn.get_height() + 4
        pad = 12
        tw = max((fn.size(line)[0] for line in lines), default=0) + pad * 2
        th = len(lines) * line_h + pad * 2

        tx, ty = pos
        tx += 16
        ty += 16

        if tx + tw > W: tx = W - tw - 5
        if ty + th > H: ty = H - th - 5

        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((10, 15, 25, 230))
        surf.blit(bg, (tx, ty))
        pygame.draw.rect(surf, CYAN, (tx, ty, tw, th), 1, border_radius=4)

        iy = ty + pad
        for line in lines:
            ls = fn.render(line, True, WHITE)
            surf.blit(ls, (tx + pad, iy))
            iy += line_h

    def _draw_hint_with_bold_keys(self, surf, cx, y, color, parts):
        """
        parts = lista di (testo, grassetto: bool)
        Usa simboli_font per caratteri speciali, font bold/sm per il resto.
        """
        fn = self.fonts

        def _pick_font(text, bold):
            special = any(ord(c) > 127 for c in text)
            if special:
                return self.simboli_font
            return fn["bold"] if bold else fn["sm"]

        rendered = [
            _pick_font(t, bold).render(t, True, color)
            for t, bold in parts
        ]

        total_w = sum(s.get_width() for s in rendered)
        x = cx - total_w // 2

        for s in rendered:
            surf.blit(s, (x, y - s.get_height() // 2))
            x += s.get_width()