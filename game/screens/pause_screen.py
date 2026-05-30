"""
pause_screen.py — Screen di pausa (State GoF).

Sovrappone un overlay semi-trasparente con le opzioni Riprendi / Salva / Esci.
Non interrompe la musica di esplorazione.
"""

from __future__ import annotations
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import W, H, BG, BG2, CYAN, GREEN, RED, YELLOW, GREY, WHITE, DARKGREY
from game.view.draw_utils import txt, sep
from game.controller.game_manager import GameManager
from game.systems.save_ui import SaveMenuSystem

_LABELS = ["Riprendi", "Salvataggio", "Regole / Aiuto", "Menu Principale"]

_OPT_COLORS = [GREEN, CYAN, YELLOW, RED]

class PauseScreen(Screen):

    def __init__(self, fonts):
        self.fonts = fonts
        self.msg = ""
        self.cursor = 0

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)

    def handle_event(self, event):
        gs = GameManager.get_instance()
        if event.type != pygame.KEYDOWN:
            return

        k = event.key
        n = len(_LABELS)

        if k in (pygame.K_UP, pygame.K_w):
            self.cursor = (self.cursor - 1) % n
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.cursor = (self.cursor + 1) % n
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self._select(self.cursor)
        elif k == pygame.K_r:
            gs.screen = "explore"
        elif k in (pygame.K_q, pygame.K_ESCAPE):
            gs.screen = "explore"

    def _select(self, idx: int) -> None:
        gs = GameManager.get_instance()
        if idx == 0:
            gs.screen = "explore"
        elif idx == 1:
            save_menu = gs.get_system(SaveMenuSystem)
            if save_menu:
                save_menu.toggle(mode="save")
            else:
                self.msg = "Sistema di salvataggio non disponibile."
        elif idx == 2:
            gs.flags["help_return_screen"] = "pause"
            gs.screen = "help"
        elif idx == 3:
            gs.screen = "menu"

    def update(self):
        pass

    def draw(self, surf: Surface):
        fn = self.fonts
        cx = W // 2
        cy = H // 2

        overlay_bg = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay_bg.fill((0, 0, 0, 210))
        surf.blit(overlay_bg, (0, 0))

        pw, ph = 400, 390
        px, py = cx - pw // 2, cy - ph // 2

        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((12, 15, 20, 240))
        surf.blit(panel_surf, (px, py))

        pygame.draw.rect(surf, (45, 55, 70), (px, py, pw, ph), 1, border_radius=6)

        pygame.draw.rect(surf, CYAN, (px, py, pw, 4), border_top_left_radius=6, border_top_right_radius=6)

        ico_info = self.simboli_font.render("❖", True, CYAN)
        surf.blit(ico_info, (px + 20, py + 22))
        txt(surf, "MENU DI PAUSA", px + 45, py + 24, CYAN, fn["bold"])
        sep(surf, px + 20, py + 55, pw - 40, (45, 55, 70))

        btn_w, btn_h = pw - 40, 46
        btn_x = px + 20
        start_y = py + 75

        for i, label in enumerate(_LABELS):
            is_sel = (self.cursor == i)
            by = start_y + i * (btn_h + 12)

            active_col = _OPT_COLORS[i]
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

                text_col = (130, 140, 150)

            center_y = by + (btn_h // 2)
            txt(surf, label, cx, center_y, text_col, fn["bold"], center=True)

        if self.msg:
            txt(surf, self.msg, cx, py + ph - 65, YELLOW, fn["sm"], center=True)

        sep(surf, px + 20, py + ph - 45, pw - 40, (45, 55, 70))
        txt(surf, "↑↓ Naviga   |   INVIO Conferma   |   ESC Riprendi", cx, py + ph - 28, (100, 110, 120), fn["sm"], center=True)