"""
select_screen.py — Screen di selezione del personaggio (State GoF).

Permette al giocatore di scegliere Rivet o Echo come personaggio principale
e come secondo personaggio controllato dall'utente.
"""

from __future__ import annotations
import pygame
import os
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import W, H, BG, BG3, CYAN, GREEN, GREY, WHITE, YELLOW, RED, DARKGREY, PANEL
from game.view.draw_utils import txt, sep
from game.controller.game_manager import GameManager
from game.paths import asset
from game.view.renderer import make_Rivet_sprite, make_Echo_sprite


class SelectScreen(Screen):

    def __init__(self, fonts):
        self.BG = BG
        self.BG3 = BG3
        self.CYAN = CYAN
        self.GREEN = GREEN
        self.RED = RED
        self.YELLOW = YELLOW
        self.GREY = GREY
        self.WHITE = WHITE
        self.DARKGREY = DARKGREY
        self.PANEL = PANEL
        self.W = W
        self.H = H
        self.fonts = fonts

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)
        self.simboli_font_lg = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 32)

        self.choice_idx = 0

        self.rivet_sprite = make_Rivet_sprite()
        self.echo_sprite = make_Echo_sprite()

        self.rivet_sprite.set_state("walk_r")
        self.echo_sprite.set_state("walk_r")

        self.rivet_sprite.scale = 3.0
        self.echo_sprite.scale = 3.0

        self.lore_coppia = (
            "Siete una coppia legata da un forte legame emotivo, costretta a sopravvivere grazie alla "
            "vostra intelligenza e alle vostre scelte. ATTENZIONE: il gioco termina se uno dei due "
            "muore o se il vostro legame si spezza (Scala Etica a -10)."
        )
        self.lore_lei = (
            "Mente teorica e pacifista. Dà priorità alla vita umana e predilige la negoziazione pacifica. "
            "È in grado di risolvere complessi enigmi informatici e militari."
        )
        self.lore_lui = (
            "Intelligenza pratica e cinica. Orientato alla sopravvivenza della coppia, è disposto a "
            "sacrificare altre vite. Non negozia, lancia ultimatum."
        )

        self.stats_lei = [
            ("HP: 100  |  ATK: 12  |  ARM: 4", self.CYAN, "❤"),
            ("Abilità: Hack", self.WHITE, "⚙"),
            ("Armi: Piccolo Calibro", self.GREY, "🔫")
        ]

        self.stats_lui = [
            ("HP: 120  |  ATK: 20  |  ARM: 8", self.GREEN, "❤"),
            ("Abilità: Supporto Bellico", self.WHITE, "⚙"),
            ("Armi: Pesanti e Piccolo Calibro", self.GREY, "🔫")
        ]

    def on_enter(self):
        self.choice_idx = 0

        gs = GameManager.get_instance()
        if not gs.audio.is_music_busy():
            gs.audio.play_music_direct(asset("audio/intro_music.wav"), volume=1.0)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (
                pygame.K_LEFT, pygame.K_RIGHT,
                pygame.K_a, pygame.K_d,
                pygame.K_UP, pygame.K_DOWN,
                pygame.K_w, pygame.K_s
            ):
                self.choice_idx = 1 if self.choice_idx == 0 else 0
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._pick()
            elif event.key == pygame.K_ESCAPE:
                gs = GameManager.get_instance()
                gs.screen = "menu"

    def update(self):
        self.rivet_sprite.update(16.6)
        self.echo_sprite.update(16.6)

    def _pick(self):
        gs = GameManager.get_instance()
        gs.select_player(self.choice_idx)

    def _draw_wrapped_text(self, surf, text, x, y, w, color, font):
        """Helper per mandare a capo il testo lungo automaticamente."""
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < w:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

        for i, line in enumerate(lines):
            txt(surf, line, x, y + i * 22, color, font)

    def draw(self, surf: Surface):
        surf.fill(self.BG)
        fn = self.fonts
        cx = self.W // 2

        ico_game = self.simboli_font_lg.render("🎮", True, self.CYAN)
        title_w = fn["xl"].size("ASSEGNAZIONE CONTROLLER")[0]

        surf.blit(ico_game, (cx - title_w//2 - 50, 16))
        txt(surf, "ASSEGNAZIONE CONTROLLER", cx, 30, self.CYAN, fn["xl"], center=True)

        txt(surf, "Decidete chi di voi controllerà Echo e chi Rivet (Coop Locale).",
               cx, 75, self.GREY, fn["sm"], center=True)

        opt_y = 115
        for i, (label, role_a, role_b, offset_x) in enumerate([
            ("CONFIGURAZIONE A", "G1: Echo", "G2: Rivet", -350),
            ("CONFIGURAZIONE B", "G1: Rivet", "G2: Echo", 50)
        ]):
            is_sel = (self.choice_idx == i)
            bx, by, bw, bh = cx + offset_x, opt_y, 300, 70

            overlay = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg_col = (20, 40, 50, 220) if is_sel else (15, 18, 25, 180)
            overlay.fill(bg_col)
            surf.blit(overlay, (bx, by))

            border_col = self.CYAN if is_sel else self.DARKGREY
            pygame.draw.rect(surf, border_col, (bx, by, bw, bh), 2, border_radius=8)

            if is_sel:
                ico_cursor = self.simboli_font.render("➤", True, self.CYAN)
                surf.blit(ico_cursor, (bx + 15, by + 25))

            txt(surf, label, bx + bw//2, by + 15, self.WHITE if is_sel else self.GREY, fn["bold"], center=True)
            txt(surf, f"{role_a}  |  {role_b}", bx + bw//2, by + 40, self.CYAN if is_sel else self.DARKGREY, fn["sm"], center=True)

        sprite_y = 290

        shadow_surf = pygame.Surface((360, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 150), (0, 0, 360, 40))
        surf.blit(shadow_surf, (cx - 150, sprite_y + 10))

        self.rivet_sprite.draw(surf, (cx + 30, sprite_y - 160))
        txt(surf, "Echo", cx - 85, sprite_y + 55, self.CYAN, fn["bold"], center=True)

        self.echo_sprite.draw(surf, (cx - 130, sprite_y - 160))
        txt(surf, "Rivet", cx + 85, sprite_y + 55, self.GREEN, fn["bold"], center=True)

        def draw_modern_panel(px, py, pw, ph, title, title_col, border_col, bg_col):
            overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
            overlay.fill(bg_col)
            surf.blit(overlay, (px, py))
            pygame.draw.rect(surf, border_col, (px, py, pw, ph), 2, border_radius=8)

            ico_info = self.simboli_font.render("❖", True, title_col)
            surf.blit(ico_info, (px + 15, py + 14))
            txt(surf, title, px + 40, py + 15, title_col, fn["bold"])
            pygame.draw.line(surf, (40, 50, 60), (px + 15, py + 40), (px + pw - 15, py + 40))

        draw_modern_panel(50, 360, self.W - 100, 100, "DINAMICA DI COPPIA", self.WHITE, self.DARKGREY, (15, 18, 25, 200))
        self._draw_wrapped_text(surf, self.lore_coppia, 70, 410, self.W - 160, self.GREY, fn["sm"])

        pw = (self.W - 140) // 2
        py_cards = 475

        draw_modern_panel(50, py_cards, pw, 210, "L'INGEGNOSA INFORMATICA", self.CYAN, self.CYAN, (10, 25, 35, 210))
        self._draw_wrapped_text(surf, self.lore_lei, 70, py_cards + 45, pw - 40, self.WHITE, fn["sm"])

        for i, (line, col, sym) in enumerate(self.stats_lei):
            ico_surf = self.simboli_font.render(sym, True, col)
            surf.blit(ico_surf, (70, py_cards + 120 + (i * 28) - 4))
            txt(surf, line, 95, py_cards + 120 + (i * 28), col, fn["sm"])

        draw_modern_panel(50 + pw + 40, py_cards, pw, 210, "IL PRAGMATICO SOPRAVVISSUTO", self.GREEN, self.GREEN, (15, 30, 20, 210))
        self._draw_wrapped_text(surf, self.lore_lui, 70 + pw + 40, py_cards + 45, pw - 40, self.WHITE, fn["sm"])

        for i, (line, col, sym) in enumerate(self.stats_lui):
            ico_surf = self.simboli_font.render(sym, True, col)
            surf.blit(ico_surf, (70 + pw + 40, py_cards + 120 + (i * 28) - 4))
            txt(surf, line, 95 + pw + 40, py_cards + 120 + (i * 28), col, fn["sm"])

        footer_y = self.H - 35
        txt(surf, "←→ Scegli   |   INVIO Conferma   |   ESC Menu Principale", cx, footer_y, self.GREY, fn["sm"], center=True)