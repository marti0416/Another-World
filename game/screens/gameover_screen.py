"""
gameover_screen.py — Screen di game over (State GoF).

Mostra il messaggio di fine partita con animazione e offre le opzioni
Riprova (dall'ultimo salvataggio) ed Esci al menu.
"""

from __future__ import annotations
import math
import random
import os
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.systems.save_ui import SaveMenuSystem
from game.paths import asset
from game.world.world_data import (
    W, H, BG, RED, WHITE, YELLOW, GREY, CYAN, GREEN, DARKGREY
)
from game.view.draw_utils import txt, sep
from game.controller.game_manager import GameManager


_DEATH_SCENES = {
    "Rivet": {
        "image_map": ["death_rivet.png"],
        "epilogue": [
            ("Narratore", "Rivet barcolla, la vista gli si appanna. Respira a fatica."),
            ("Echo",      "«Rivet! Rivet, rispondimi! Non chiudere gli occhi!»"),
            ("Narratore", "Ma non c'è risposta. Senza di lui, non c'è più missione."),
            ("Narratore", "È finita.")
        ],
        "final_message": "Rivet è caduto. Senza di lui, non c'è via d'uscita."
    },
    "Echo": {
        "image_map": ["death_echo.png"],
        "epilogue": [
            ("Narratore", "Echo crolla a terra."),
            ("Rivet",     "«No... Echo! MALEDETTI, LA PAGHERETE!»"),
            ("Narratore", "Rivet imbraccia l'arma, cieco dalla rabbia e dal dolore."),
            ("Narratore", "Non c'è più nulla da perdere.")
        ],
        "final_message": "Echo è morta. La rabbia di Rivet la rivendicherà."
    },
    "Legame": {
        "image_map": ["death_ethics.png"],
        "epilogue": [
            ("Narratore", "Le divergenze tra voi sono diventate un muro."),
            ("Narratore", "Vi guardate, ormai estranei."),
            ("Narratore", "Il legame si è spezzato. Non c'è più fiducia."),
            ("Narratore", "Da soli, non si sopravvive.")
        ],
        "final_message": "Il vostro legame si è spezzato. Senza collaborazione, non avete avuto scampo."
    },
    "Default": {
        "image_map": ["menu_apocalypse.jpg"],
        "epilogue": [
            ("Narratore", "Il buio si chiude intorno a voi."),
            ("Narratore", "La vostra storia finisce qui, in una città che non esiste più.")
        ],
        "final_message": "Siete stati eliminati."
    }
}

_OPT_LABELS = ["Riprova dal salvataggio", "Torna al menu"]
_OPT_COUNT  = len(_OPT_LABELS)

class GameOverScreen(Screen):
    def __init__(self, fonts):
        self.fonts   = fonts
        self._anim   = 0.0
        self.cursor  = 0
        self._line   = 0
        self._narr_done = False
        self._scene_key = "Default"

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 18)
        self._load_images()

    def _load_images(self):
        """Carica le immagini di morte dalla cartella backgrounds."""
        self._bg_imgs = {}
        base_dir = os.path.dirname(__file__)
        img_dir = asset("images/backgrounds")

        for key, data in _DEATH_SCENES.items():
            img_name = data["image_map"][0]
            path = os.path.join(img_dir, img_name)
            try:
                img = pygame.image.load(path).convert()
                self._bg_imgs[key] = pygame.transform.scale(img, (W, H))
            except:
                s = pygame.Surface((W, H)); s.fill((20, 5, 5))
                self._bg_imgs[key] = s

    def on_enter(self):
        self._anim = 0.0
        self._line = 0
        self._narr_done = False
        self._sound_played = False
        gs = GameManager.get_instance()
        self.can_load = gs.save_manager.has_any_saves()
        self.cursor = 0 if self.can_load else 1

        reason = gs.over_reason.lower()
        if "rivet" in reason: self._scene_key = "Rivet"
        elif "echo" in reason: self._scene_key = "Echo"
        elif "legame" in reason or "etica" in reason: self._scene_key = "Legame"
        else: self._scene_key = "Default"

    def update(self):
        self._anim += 0.04

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        k = event.key

        if not self._narr_done:
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                scene = _DEATH_SCENES[self._scene_key]
                self._line += 1

                if self._line >= len(scene["epilogue"]):
                    self._narr_done = True

            return

        if k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.cursor = 1 - self.cursor
            if self.cursor == 0 and not self.can_load:
                self.cursor = 1
        elif k in (pygame.K_RETURN, pygame.K_SPACE): self._select_idx(self.cursor)
        elif k == pygame.K_q: self._select_idx(1)

    def _draw_wrapped_text(self, surf, text, x, y, w, color, font, center=False, align_left=False):
        """Wrapper universale per il testo (supporta centro e sinistra)."""
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

        line_h = font.get_height() + 4
        total_h = len(lines) * line_h

        start_y = y - (total_h // 2) if center else y

        for i, line in enumerate(lines):
            if align_left:
                l_surf = font.render(line, True, color)
                surf.blit(l_surf, (x, start_y + i * line_h))
            else:
                txt(surf, line, x, start_y + i * line_h + (line_h // 2 if center else 0), color, font, center=center)
        return total_h

    def draw(self, surf: Surface):
        scene = _DEATH_SCENES[self._scene_key]
        color = RED
        fn = self.fonts
        cx = W // 2

        if not self._narr_done:
            self._draw_narration(surf, scene, color, fn, cx)
        else:
            self._draw_results(surf, scene, color, fn, cx)


    def _draw_narration(self, surf: Surface, scene: dict, color, fn: dict, cx: int):
        surf.blit(self._bg_imgs[self._scene_key], (0, 0))

        filter_a = int(30 + 15 * math.sin(self._anim * 2))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((60, 0, 0, filter_a))
        surf.blit(overlay, (0, 0))

        pw, ph = 860, 160
        px, py = cx - pw // 2, H - ph - 30

        box_bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        box_bg.fill((20, 5, 5, 230))
        surf.blit(box_bg, (px, py))
        pygame.draw.rect(surf, color, (px, py, pw, ph), 2, border_radius=8)

        speaker, text = scene["epilogue"][self._line]

        base_col = WHITE
        if speaker == "Echo": base_col = CYAN
        elif speaker == "Rivet": base_col = GREEN

        text_y = py + 35
        if speaker != "Narratore":
            txt(surf, speaker.upper(), px + 30, py + 20, base_col, self.fonts["bold"])
            sep(surf, px + 30, py + 45, pw - 60, base_col)
            text_y = py + 60
        self._draw_wrapped_text(surf, text, px + 30, text_y, pw - 60, WHITE, fn["md"])
        blink = abs(math.sin(self._anim * 3.0)) > 0.4
        hint_col = color if blink else (100, 0, 0)
        prompt = "[INVIO]  Avanti..."
        prompt_w = fn["bold"].size(prompt)[0]

        text_x = px + pw - prompt_w - 20
        text_y = py + ph - 30

        txt(surf, prompt, text_x, text_y, RED, fn["bold"])


    def _draw_results(self, surf: Surface, scene: dict, color, fn: dict, cx: int):

        if not self._sound_played:
            gs = GameManager.get_instance()
            if hasattr(gs, 'audio'):
                gs.audio.play_music("gameover", loops=0, fade_ms=0)
            self._sound_played = True

        surf.blit(self._bg_imgs[self._scene_key], (0, 0))
        overlay_dark = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay_dark.fill((0, 0, 0, 180))
        surf.blit(overlay_dark, (0, 0))

        pw, ph = 720, 380
        px, py = cx - pw // 2, H // 2 - ph // 2

        shadow = pygame.Surface((pw + 12, ph + 12), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 100))
        surf.blit(shadow, (px - 6, py - 6))

        glow_surf = pygame.Surface((pw + 40, ph + 40), pygame.SRCALPHA)
        glow_a = int(40 + 25 * math.sin(self._anim * 1.5))
        pygame.draw.rect(glow_surf, (*color, glow_a), (0, 0, pw + 40, ph + 40), border_radius=22)
        surf.blit(glow_surf, (px - 20, py - 20))

        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((15, 5, 5, 245))
        surf.blit(panel_surf, (px, py))
        pygame.draw.rect(surf, color, (px, py, pw, ph), 3, border_radius=12)
        pygame.draw.rect(surf, (60, 0, 0), (px + 6, py + 6, pw - 12, ph - 12), 1, border_radius=8)

        pulse = int(200 + 55 * math.sin(self._anim * 2))
        title_col = (pulse, 0, 0)
        txt(surf, "G A M E   O V E R", cx + 2, py + 47, (30, 0, 0), fn["xl"], center=True)
        txt(surf, "G A M E   O V E R", cx, py + 45, title_col, fn["xl"], center=True)

        sep(surf, px + 40, py + 85, pw - 80, color)
        pygame.draw.circle(surf, color, (cx, py + 85), 4)

        msg_h = self._draw_wrapped_text(surf, scene["final_message"], cx, py + 130, pw - 80, WHITE, fn["sm"], center=True)

        sep_y = py + 130 + msg_h + 20
        sep(surf, px + 40, sep_y, pw - 80, GREY)
        pygame.draw.circle(surf, GREY, (cx, sep_y), 3)

        btn_w, btn_h = pw - 100, 46
        btn_x = cx - btn_w // 2
        start_y = sep_y + 20

        for i, label in enumerate(_OPT_LABELS):
            by = start_y + i * 65
            is_sel = (i == self.cursor)
            if i == 0 and not self.can_load:
                btn_col = GREY
                disp_label = "Nessun Salvataggio"
                is_sel = False
            else:
                btn_col = RED
                disp_label = label

            if is_sel:
                sel_bg = (btn_col[0]//6, btn_col[1]//6, btn_col[2]//6, 255)
                pygame.draw.rect(surf, sel_bg, (btn_x, by, btn_w, btn_h), border_radius=4)
                pygame.draw.rect(surf, btn_col, (btn_x, by, btn_w, btn_h), 2, border_radius=4)
                pygame.draw.rect(surf, btn_col, (btn_x, by, 5, btn_h), border_radius=2)

                ico = self.simboli_font.render("➤", True, btn_col)
                surf.blit(ico, (btn_x + 16, by + (btn_h // 2) - (ico.get_height() // 2)))
                text_col = WHITE
            else:
                pygame.draw.rect(surf, (25, 5, 5, 180), (btn_x, by, btn_w, btn_h), border_radius=4)
                pygame.draw.rect(surf, (50, 10, 10), (btn_x, by, btn_w, btn_h), 1, border_radius=4)
                text_col = GREY

            t_surf = fn["bold"].render(disp_label, True, text_col)
            t_rect = t_surf.get_rect(center=(cx, by + btn_h // 2))
            surf.blit(t_surf, t_rect)

        txt(surf, "↑↓ Naviga   INVIO Conferma   Q Menu", cx, H - 30, GREY, fn["sm"], center=True)

    def _select_idx(self, idx: int):
        gs = GameManager.get_instance()
        if idx == 0:
            save_menu = gs.get_system(SaveMenuSystem)
            if save_menu: save_menu.toggle(mode="load")
        else:
            gs.screen = "menu"