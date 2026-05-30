"""
victory_screen.py — Screen di vittoria (State GoF).

Mostra le statistiche finali (danni, quest completate, etica di coppia)
e la sequenza di crediti animata.
"""

from __future__ import annotations
import math
import random
import os
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.paths import asset
from game.world.world_data import (
    W, H, BG, GREEN, CYAN, YELLOW, GREY, WHITE, DARKGREY
)
from game.view.draw_utils import txt, panel, sep
from game.controller.game_manager import GameManager

_ENDINGS = {
    "purify": {
        "title": "FINALE I — ALBA DESOLATA",
        "color": GREEN,
        "epilogue": [
            ("Narratore", "Echo e Rivet indossano le tute protettive e collegano il silo al sistema di ventilazione della fabbrica."),
            ("Narratore", "Invertito il flusso d'aria verso l'esterno,"),
            ("Narratore", "l'acido nebulizzato si sparge per la città sottoforma di nube."),
            ("Narratore", "Mucillagine, infetti, superstiti, piante e animali — ogni forma di vita si dissolve completamente."),
            ("Narratore", "La città è vuota."),
            ("Narratore", "Pronta per essere ripopolata e fortificata."),
        ],
        "image_map": [
            "purify_1", "purify_1", "purify_2",
            "purify_3", "purify_4", "purify_4",
        ],
        "result_image": "purify_4",
        "final_message": "Siete al sicuro, ma c'è ancora tanto lavoro da fare per riconquistare la città."
    },
    "battle": {
        "title": "FINALE II — GUERRA SENZA FINE",
        "color": CYAN,
        "epilogue": [
            ("Narratore", "Echo e Rivet non se la sentono di condannare a morte tutti indiscriminatamente."),
            ("Narratore", "Razziatori, Solidali, persone innocenti — non importa."),
            ("Narratore", "Fatto scorta di acido per usarlo contro obiettivi specifici,"),
            ("Narratore", "i due escono dall'impianto consapevoli di dover combattere ancora per molto."),
            ("Narratore", "Ma anche di poter aiutare altri sopravvissuti come loro a cavarsela in questo incubo."),
        ],
        "image_map": [
            "battle_1", "battle_1",
            "battle_2", "battle_3",
            "battle_3",
        ],
        "result_image": "battle_3",
        "final_message": "Con difficoltà continuerete a lottare per la sopravvivenza degli umani."
    },
}
_DEFAULT_ENDING = "purify"
_OPT_LABELS  = ["Torna al menu", "Esci dal gioco"]
_OPT_COUNT   = len(_OPT_LABELS)

class VictoryScreen(Screen):
    def __init__(self, fonts):
        self.fonts   = fonts
        self._anim   = 0.0
        self.cursor  = 0
        self._ending_key = _DEFAULT_ENDING

        self._line:      int  = 0
        self._narr_done: bool = False

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont(
            "segoeuisymbol, applesymbols, dejavusans, arial", 18
        )
        self._load_images()

    def _load_images(self):
        """Carica le immagini di cutscene in memoria in modo dinamico."""
        self._bg_imgs = {}

        base_dir = os.path.dirname(__file__)
        img_dir = asset("images/backgrounds")

        paths = {
            "purify_1": os.path.join(img_dir, "finale1_1.png"),
            "purify_2": os.path.join(img_dir, "finale1_2.png"),
            "purify_3": os.path.join(img_dir, "finale1_3.png"),
            "purify_4": os.path.join(img_dir, "finale1_4.png"),
            "battle_1": os.path.join(img_dir, "finale2_1.png"),
            "battle_2": os.path.join(img_dir, "finale2_2.png"),
            "battle_3": os.path.join(img_dir, "finale2_3.png"),
        }
        for key, path in paths.items():
            try:
                img = pygame.image.load(path).convert()
                self._bg_imgs[key] = pygame.transform.scale(img, (W, H))
            except Exception as e:
                print(f"[VictoryScreen] Immagine non trovata: {path}")
                s = pygame.Surface((W, H))
                s.fill((10, 10, 15))
                self._bg_imgs[key] = s

    def on_enter(self):
        self._anim      = 0.0
        self.cursor     = 0
        self._line      = 0
        self._narr_done = False
        gs = GameManager.get_instance()
        raw = gs.flags.get("ending_choice", _DEFAULT_ENDING)
        self._ending_key = raw if raw in _ENDINGS else _DEFAULT_ENDING
        print(f"[VictoryScreen] ending_key={self._ending_key!r}  (flag raw={raw!r})")

    def update(self):
        self._anim += 0.04

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if not self._narr_done:
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                ending = _ENDINGS.get(self._ending_key, _ENDINGS[_DEFAULT_ENDING])
                self._line += 1
                if self._line >= len(ending["epilogue"]):
                    self._narr_done = True
            return

        if   k in (pygame.K_UP,   pygame.K_w): self.cursor = (self.cursor - 1) % _OPT_COUNT
        elif k in (pygame.K_DOWN, pygame.K_s): self.cursor = (self.cursor + 1) % _OPT_COUNT
        elif k in (pygame.K_RETURN, pygame.K_SPACE): self._select_idx(self.cursor)
        elif k == pygame.K_q: self._select_idx(0)

    def _draw_wrapped_text(self, surf, text, x, y, w, color, font, center=False):
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

        line_height = font.get_height() + 4
        for i, line in enumerate(lines):
            if center:
                txt(surf, line, x, y + i * line_height, color, font, center=True)
            else:
                txt(surf, line, x, y + i * line_height, color, font)
        return len(lines) * line_height

    def draw(self, surf: Surface):
        ending = _ENDINGS.get(self._ending_key, _ENDINGS[_DEFAULT_ENDING])
        color  = ending["color"]
        fn     = self.fonts
        cx     = W // 2

        if not self._narr_done:
            self._draw_narration(surf, ending, color, fn, cx)
        else:
            self._draw_results(surf, ending, color, fn, cx)

    def _draw_narration(self, surf: Surface, ending: dict, color, fn: dict, cx: int):
        img_key = ending["image_map"][self._line]
        surf.blit(self._bg_imgs[img_key], (0, 0))

        pw, ph = 860, 160
        px = cx - pw // 2
        py = H - ph - 30

        overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
        overlay.fill((15, 18, 22, 230))
        surf.blit(overlay, (px, py))
        pygame.draw.rect(surf, color, (px, py, pw, ph), 2, border_radius=8)

        speaker, text = ending["epilogue"][self._line]

        base_col = WHITE
        if speaker == "Echo":    base_col = CYAN
        elif speaker == "Rivet": base_col = GREEN

        text_y = py + 35
        if speaker != "Narratore":
            txt(surf, speaker.upper(), px + 30, py + 20, base_col, fn["bold"])
            sep(surf, px + 30, py + 45, pw - 60, base_col)
            text_y = py + 60

        self._draw_wrapped_text(surf, text, px + 30, text_y, pw - 60, WHITE, fn["md"])

        blink    = abs(math.sin(self._anim * 3.0)) > 0.4
        hint_col = color if blink else (100, 100, 100)
        prompt = "[INVIO]  Avanti..."
        prompt_w = fn["bold"].size(prompt)[0]

        text_x = px + pw - prompt_w - 20
        text_y = py + ph - 30

        txt(surf, prompt, text_x, text_y, color, fn["bold"])

    def _draw_results(self, surf: Surface, ending: dict, color, fn: dict, cx: int):
        result_img_key = ending["result_image"]
        surf.blit(self._bg_imgs[result_img_key], (0, 0))

        overlay_bg = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay_bg.fill((0, 0, 0, 180))
        surf.blit(overlay_bg, (0, 0))

        pw, ph = 720, 380
        px  = cx - pw // 2
        py3 = H // 2 - ph // 2

        shadow = pygame.Surface((pw + 12, ph + 12), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 100))
        surf.blit(shadow, (px - 6, py3 - 6))

        glow_surf = pygame.Surface((pw + 40, ph + 40), pygame.SRCALPHA)
        glow_a    = int(40 + 25 * math.sin(self._anim * 1.5))
        pygame.draw.rect(glow_surf, (*color, glow_a), (0, 0, pw + 40, ph + 40), border_radius=22)
        surf.blit(glow_surf, (px - 20, py3 - 20))

        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 22, 240))
        surf.blit(panel_surf, (px, py3))

        pygame.draw.rect(surf, color, (px, py3, pw, ph), 3, border_radius=12)

        inner_rect = pygame.Rect(px + 6, py3 + 6, pw - 12, ph - 12)
        pygame.draw.rect(surf, tuple(max(0, c // 4) for c in color), inner_rect, 1, border_radius=8)

        pulse      = int(200 + 55 * math.sin(self._anim * 2))
        shadow_val = int(30  + 20 * math.sin(self._anim * 2))
        shadow_col = tuple(min(255, int(c * shadow_val / 255)) for c in color)
        title_col  = tuple(min(255, int(c * pulse   / 255)) for c in color)

        txt(surf, ending["title"], cx + 3, py3 + 48, shadow_col, fn["xl"], center=True)
        txt(surf, ending["title"], cx,     py3 + 45, title_col,  fn["xl"], center=True)

        sep(surf, cx - (pw // 2) + 20, py3 + 85, pw - 40, color)
        pygame.draw.circle(surf, color, (cx, py3 + 85), 4)

        wrap_w = pw - 80
        wrap_y = py3 + 110
        message_height = self._draw_wrapped_text(
            surf, ending["final_message"], cx, wrap_y, wrap_w, WHITE, fn["sm"], center=True
        )

        sep_y = wrap_y + message_height + 25
        sep(surf, px + 20, sep_y, pw - 40, GREY)
        pygame.draw.circle(surf, GREY, (cx, sep_y), 3)

        btn_start_y = sep_y + 20
        btn_w = pw - 80
        btn_h = 46
        btn_x = cx - btn_w // 2
        opt_colors = [color, GREY]

        for i, (label, btn_color) in enumerate(zip(_OPT_LABELS, opt_colors)):
            by     = btn_start_y + i * 65
            is_sel = (i == self.cursor)
            btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)

            if is_sel:
                btn_bg.fill((btn_color[0]//6, btn_color[1]//6, btn_color[2]//6, 255))
                surf.blit(btn_bg, (btn_x, by))
                pygame.draw.rect(surf,
                    (btn_color[0]//2, btn_color[1]//2, btn_color[2]//2),
                    (btn_x, by, btn_w, btn_h), 1, border_radius=4)
                pygame.draw.rect(surf, btn_color, (btn_x, by, 4, btn_h),
                    border_top_left_radius=4, border_bottom_left_radius=4)
                ico_cursor = self.simboli_font.render("➤", True, btn_color)
                surf.blit(ico_cursor, (btn_x + 16, by + (btn_h//2) - (ico_cursor.get_height()//2)))
                text_col = WHITE
            else:
                btn_bg.fill((18, 22, 28, 180))
                surf.blit(btn_bg, (btn_x, by))
                pygame.draw.rect(surf, (35, 45, 55),
                    (btn_x, by, btn_w, btn_h), 1, border_radius=4)
                text_col = (130, 140, 150)

            center_y = by + (btn_h // 2)
            txt(surf, label, cx, center_y, text_col, fn["bold"], center=True)

        txt(surf, "↑↓ Naviga   INVIO Conferma   Q Menu", cx, H - 30, GREY, fn["sm"], center=True)

    def _select_idx(self, idx: int):
        gs = GameManager.get_instance()
        if idx == 0:
            gs.screen = "menu"
        elif idx == 1:
            pygame.event.post(pygame.event.Event(pygame.QUIT))