"""
menu_screen.py — Screen del menu principale (State GoF).

Mostra il titolo, le opzioni Nuova Partita / Continua / Esci e gestisce
la navigazione con tastiera e mouse.
"""

from __future__ import annotations
import sys
import math
import random
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import (
    W, H, BG, BG2, BG3, CYAN, GREEN, RED, YELLOW,
    MAGENTA, GREY, WHITE, DARKGREY, PANEL, ORANGE,
    FPS, TILE, MAP_COLS, MAP_ROWS
)
from game.view.draw_utils import txt, panel, sep
from game.controller.game_manager import GameManager
from game.paths import asset
from game.events.event_types import EventType
from game.effects.screen_effects import GlitchEffect
from game.systems.save_ui import SaveMenuSystem

_OPT_COLORS = [(0, 200, 0), (0, 229, 255), (200, 160, 0), RED]
_OPT_LABELS = ["Nuova Partita", "Carica Partita", "Regole", "Esci"]

class MenuScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        self.cursor = 0
        self._fade = 0
        self._anim = 0.0
        self._subscribed_to_load = False
        self.can_load = False

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)

        try:
            self._title_font = pygame.font.Font(
                asset("fonts/PressStart2P-Regular.ttf"), 40
            )
        except Exception:
            self._title_font = fonts["xl"]

        def _courier(size, bold=False):
            try:
                return pygame.font.SysFont("Courier New", size, bold=bold)
            except Exception:
                return pygame.font.Font(None, size)

        self._courier_sm = _courier(13)
        self._courier_md = _courier(16)
        self._courier_bold = _courier(16, bold=True)

        def _consolas(size, bold=False):
            try:
                path = "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"
                return pygame.font.Font(path, size)
            except Exception:
                return pygame.font.SysFont("Consolas", size, bold=bold)

        self._desc_font = _consolas(13)

        self.particles: list[list] = []

        self._glitch = GlitchEffect()
        self._glitch_timer = 0
        self._glitch_interval = random.randint(FPS * 2, FPS * 3)

        self.bg_img = pygame.image.load(
            asset("images/backgrounds/menu_apocalypse.jpg")
        ).convert()
        self.bg_img = pygame.transform.scale(self.bg_img, (W, H))

    def on_enter(self) -> None:
        self._subscribed_to_load = False
        self.cursor = 0
        self._fade = 0
        self._glitch_timer = 0
        self._glitch_interval = random.randint(FPS * 2, FPS * 3)

        gs = GameManager.get_instance()
        self.can_load = gs.save_manager.has_any_saves()

    def handle_event(self, event):
        gs = GameManager.get_instance()

        if gs.bus and not self._subscribed_to_load:
            gs.bus.subscribe(EventType.GAME_LOADED, self._on_game_loaded)
            gs.bus.subscribe(EventType.SAVE_DELETED, self._on_save_deleted)
            self._subscribed_to_load = True

        if event.type == pygame.KEYDOWN:
            n = len(_OPT_LABELS)

            if event.key in (pygame.K_UP, pygame.K_w):
                self.cursor = (self.cursor - 1) % n
                if self.cursor == 1 and not self.can_load:
                    self.cursor = 0

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.cursor = (self.cursor + 1) % n
                if self.cursor == 1 and not self.can_load:
                    self.cursor = 2

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select(self.cursor)

            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.quit()
                sys.exit()

            elif event.key == pygame.K_F1:
                gs.flags["ending_choice"] = "purify"
                gs.screen = "victory"
            elif event.key == pygame.K_F2:
                gs.screen = "factory_finale"
            elif event.key == pygame.K_F3:
                gs.over_reason = "Siete stati eliminati"
                gs.screen = "gameover"

            elif event.key == pygame.K_F4:
                gs.over_reason = "Rivet è caduto durante l'esplorazione. La missione è fallita."
                gs.screen = "gameover"

            elif event.key == pygame.K_F5:
                gs.over_reason = "Echo è caduta durante l'esplorazione. La missione è fallita."
                gs.screen = "gameover"

            elif event.key == pygame.K_F6:
                gs.over_reason = "Il vostro legame si è spezzato. La missione è fallita."
                gs.screen = "gameover"

            elif event.key == pygame.K_F7:
                gs.start_debug_battle()

    def _select(self, idx: int):
        gs = GameManager.get_instance()
        if idx == 0:
            gs.start_new_game()
            gs._setup_systems()
            gs.screen = "intro"
        elif idx == 1:
            if not self.can_load:
                return
            save_menu = gs.get_system(SaveMenuSystem)
            if save_menu:
                save_menu.toggle(mode="load")
        elif idx == 2:
            gs.flags["help_return_screen"] = "menu"
            gs.screen = "help"
        else:
            pygame.quit()
            sys.exit()

    def _on_game_loaded(self, data: dict):
        pass

    def _on_save_deleted(self, data: dict):
        gs = GameManager.get_instance()
        self.can_load = gs.save_manager.has_any_saves()

    def update(self):
        self._anim += 0.04
        self._fade = min(255, self._fade + 4)

        if len(self.particles) < 40:
            self.particles.append([
                random.randint(0, W),
                random.randint(0, H),
                random.uniform(0.5, 1.5),
                random.randint(3, 6),
            ])

        for p in self.particles:
            p[1] -= p[2]
            if p[1] < 0:
                p[0] = random.randint(0, W)
                p[1] = H

        self._glitch_timer += 1
        if self._glitch_timer >= self._glitch_interval:
            self._glitch.trigger(strength=random.randint(4, 10), duration=random.randint(8, 16))
            self._glitch_timer = 0
            self._glitch_interval = random.randint(FPS * 2, FPS * 3)

        self._glitch.update()

    def draw(self, surf: Surface):
        cx = W // 2
        fade_alpha = self._fade

        surf.blit(self.bg_img, (0, 0))

        for x, y, speed, size in self.particles:
            particle = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle, (200, 200, 200, 80), (size, size), size)
            surf.blit(particle, (x - size, y - size))

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        glow = int(180 + 60 * math.sin(self._anim * 2))
        gc = (0, glow, 255)

        title_y = 130
        title_surf = self._title_font.render("Another World", True, gc)
        title_surf.set_alpha(fade_alpha)
        surf.blit(title_surf, title_surf.get_rect(center=(cx, title_y + 35)))

        sub_surf = self._courier_md.render("Sopravvivi.  Collabora.  Scegli.", True, (255, 255, 255))
        sub_surf.set_alpha(fade_alpha)
        surf.blit(sub_surf, sub_surf.get_rect(center=(cx, title_y + 75)))

        desc_lines = [
            "In un futuro prossimo devastato da un meteorite e dalla sua",
            "Mucillagine Bioattiva, la sopravvivenza nella metropoli",
            "dipende dalla sinergia tra due unici personaggi."
        ]
        start_y = 250
        for i, line in enumerate(desc_lines):
            y = start_y + i * 22
            shadow_surf = self._desc_font.render(line, True, (0, 0, 0))
            shadow_surf.set_alpha(fade_alpha)
            surf.blit(shadow_surf, shadow_surf.get_rect(center=(cx + 2, y + 2)))
            text_surf = self._desc_font.render(line, True, (255, 255, 255))
            text_surf.set_alpha(fade_alpha)
            surf.blit(text_surf, text_surf.get_rect(center=(cx, y)))

        btn_w, btn_h = 320, 46
        start_by = 340

        for i, (label, color) in enumerate(zip(_OPT_LABELS, _OPT_COLORS)):
            by = start_by + i * (btn_h + 12)
            btn_x = cx - btn_w // 2
            is_sel = (i == self.cursor)

            if i == 1 and not self.can_load:
                active_col = GREY
                disp_label = "Nessun Salvataggio"
                is_sel = False
            else:
                active_col = color
                disp_label = label

            btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)

            if is_sel:
                btn_bg.fill((active_col[0]//6, active_col[1]//6, active_col[2]//6, 255))
                surf.blit(btn_bg, (btn_x, by))
                pygame.draw.rect(surf, (active_col[0]//2, active_col[1]//2, active_col[2]//2), (btn_x, by, btn_w, btn_h), 1, border_radius=4)
                pygame.draw.rect(surf, active_col, (btn_x, by, 4, btn_h), border_top_left_radius=4, border_bottom_left_radius=4)

                ico_cursor = self.simboli_font.render("➤", True, active_col)
                surf.blit(ico_cursor, (btn_x + 16, by + (btn_h // 2) - (ico_cursor.get_height() // 2)))
                text_col = WHITE
            else:
                btn_bg.fill((18, 22, 28, 180))
                surf.blit(btn_bg, (btn_x, by))
                pygame.draw.rect(surf, (35, 45, 55), (btn_x, by, btn_w, btn_h), 1, border_radius=4)
                text_col = (130, 140, 150) if (i != 1 or self.can_load) else (80, 80, 80)

            center_y = by + (btn_h // 2)
            txt(surf, disp_label, cx, center_y, text_col, self._courier_bold, center=True)

        self._draw_hint_with_bold_arrows(surf, cx, H - 35, (100, 110, 120))

        dbg_surf = self._courier_sm.render("F7 — DEBUG: Battaglia Gigante di Carne", True, (80, 60, 30))
        surf.blit(dbg_surf, (8, H - 18))

        self._glitch.draw(surf)

    def _draw_hint_with_bold_arrows(self, surf, cx, y, color):
        parts = [
            ("↑↓ ", self._courier_bold),
            ("Naviga   |   ", self._courier_sm),
            ("INVIO ", self._courier_bold),
            ("Seleziona", self._courier_sm),
        ]

        total_w = sum(font.size(text)[0] for text, font in parts)
        x = cx - total_w // 2

        for text, font in parts:
            surf_part = font.render(text, True, color)
            surf.blit(surf_part, (x, y - font.get_height() // 2))
            x += surf_part.get_width()