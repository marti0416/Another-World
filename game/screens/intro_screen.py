"""
intro_screen.py — Screen dell'intro animata (State GoF).

Riproduce la sequenza di introduzione con testo a scorrimento e musica.
Al termine transita automaticamente alla SelectScreen.
"""

from __future__ import annotations
import math
import os
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import (
    W, H, CYAN, GREEN, YELLOW, GREY, WHITE
)
from game.view.draw_utils import txt, sep
from game.controller.game_manager import GameManager
from game.paths import asset


_INTRO_LINES = [
    ("Atto I: L'Origine del Male",
     "Il mondo stava per finire così come lo conosciamo. Una minaccia enorme stava per colpire il pianeta, ma non veniva da signori della guerra impazziti o da malattie mortali nate in posti esotici, bensì dallo spazio. Un asteroide era in rotta di collisione col nostro pianeta e nascondeva al suo interno un nemico del tutto inaspettato, che avrebbe causato una vera e propria apocalisse.",
     "intro_1"),

    ("Atto II: L'Infezione",
     "Il meteorite si è schiantato nella metropoli e si è spaccato, rilasciando una mucillagine che, entrando in contatto con masse organiche come le persone, rilascia un virus mutageno che le trasforma in pochi minuti in esseri violenti, senza più umanità, con il solo scopo di infettare altri esseri viventi. Il caos sta prendendo il sopravvento nella città, le vittime sono migliaia ogni giorno, e l'infezione e la mucillagine si propagano più velocemente di quanto i superstiti possano contrastare.",
     "intro_2"),

    ("Atto III: Un Mondo a Pezzi",
     "Della società pre-impatto non rimane molto. La guerra tra infetti e fazioni umane imperversa ad ogni angolo della città e i pochi superstiti rimasti si sono uniti in gruppi con scopi diversi. I Razziatori sono persone violente che uccidono, saccheggiano e non si preoccupano della sopravvivenza umana. I Solidali invece credono ancora di poter vincere un giorno contro l'infezione aliena rimanendo coesi ed empatici, cercando di portare avanti quella civiltà che si stava perdendo nel macello apocalittico.",
     "intro_3"),

    ("Atto IV: Destinazione Salvezza",
     "In mezzo al caos, due fidanzati cercano di sopravvivere, osservando ciò che hanno attorno e studiando un piano per raggiungere il loro obiettivo: trovare un modo per combattere l'infezione e i suoi abomini, senza però perdere di vista la loro parte umana. Dovranno farsi strada tra edifici pieni di nemici e zone pericolose per riuscire nel loro intento, ma insieme potranno avere la meglio.",
     "intro_4"),
]

_SPEAKER_COLORS = {
    "Atto I: L'Origine del Male": YELLOW,
    "Atto II: L'Infezione":       YELLOW,
    "Atto III: Un Mondo a Pezzi": YELLOW,
    "Atto IV: Destinazione Salvezza": YELLOW,
    "Narratore": YELLOW,
    "":          WHITE,
}

class IntroScreen(Screen):
    """Schermata narrativa introduttiva prima dell'esplorazione."""

    def __init__(self, fonts):
        self.fonts = fonts
        self._line: int  = 0
        self._done: bool = False
        self._anim: float = 0.0
        self._fade: int   = 0
        self._prev_img_key: str = ""
        self._prev_img_key: str = ""
        self._scroll_y: int = 0

        pygame.font.init()


        def _courier(size, bold=False):
            try:
                return pygame.font.SysFont("Courier New", size, bold=bold)
            except Exception:
                return pygame.font.Font(None, size)

        self._courier_sm   = _courier(13)
        self._courier_md   = _courier(16)
        self._courier_bold = _courier(16, bold=True)

        self._load_images()


    def _load_images(self):
        self._bg_imgs: dict[str, Surface] = {}

        base_dir = os.path.dirname(__file__)
        img_dir  = os.path.join(
            base_dir, "..", "..", "assets", "images", "backgrounds"
        )

        paths = {
            "intro_1": os.path.join(img_dir, "intro_1.png"),
            "intro_2": os.path.join(img_dir, "intro_2.png"),
            "intro_3": os.path.join(img_dir, "intro_3.png"),
            "intro_4": os.path.join(img_dir, "intro_4.png"),
        }

        for key, path in paths.items():
            try:
                img = pygame.image.load(path).convert()
                self._bg_imgs[key] = pygame.transform.scale(img, (W, H))
            except Exception:
                print(f"[IntroScreen] Immagine non trovata: {path}")
                fallback = pygame.Surface((W, H))
                fallback.fill((10, 10, 15))
                self._bg_imgs[key] = fallback

    def on_enter(self) -> None:
        self._line = 0
        self._done = False
        self._anim = 0.0
        self._fade = 0
        self._prev_img_key = _INTRO_LINES[0][2]
        self._scroll_y = 0

        gs = GameManager.get_instance()
        gs.audio.play_music_direct(asset("audio/intro_music.wav"), volume=1.0)

    def update(self):
        self._anim += 0.04

        if self._fade < 255:
            self._fade = min(255, self._fade + 6)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        k = event.key

        if k == pygame.K_RETURN:
            if self._done:
                self._finish()
        elif k == pygame.K_RIGHT:
            self._advance()
        elif k == pygame.K_LEFT:
            self._go_back()
        elif k == pygame.K_DOWN:
            self._scroll_y += 1
        elif k == pygame.K_UP:
            self._scroll_y -= 1
        elif k == pygame.K_SPACE:
            self._finish()
        elif k == pygame.K_ESCAPE:
            gs = GameManager.get_instance()
            gs.audio.stop_music(fade_ms=0)

            gs.screen = "menu"

    def _advance(self):
        if self._done:
            self._finish()
            return

        next_line = self._line + 1
        if next_line >= len(_INTRO_LINES):
            self._done = True
        else:
            cur_key  = _INTRO_LINES[self._line][2]
            next_key = _INTRO_LINES[next_line][2]
            if next_key != cur_key:
                self._fade = 0
            self._line = next_line
            self._scroll_y = 0

    def _go_back(self):
        if self._done or self._line == 0:
            return
        prev_key = _INTRO_LINES[self._line - 1][2]
        cur_key  = _INTRO_LINES[self._line][2]
        if prev_key != cur_key:
            self._fade = 0
        self._line -= 1
        self._scroll_y = 0

    def _finish(self):

        gs = GameManager.get_instance()
        gs.screen = "select"

    def draw(self, surf: Surface):
        cx = W // 2

        if self._done:
            self._draw_end_card(surf, cx)
        else:
            self._draw_narration(surf, cx)

    def _draw_narration(self, surf: Surface, cx: int):
        speaker, text, img_key = _INTRO_LINES[self._line]

        bg = self._bg_imgs.get(img_key)
        if bg:
            faded_bg = bg.copy()
            faded_bg.set_alpha(self._fade)
            surf.fill((0, 0, 0))
            surf.blit(faded_bg, (0, 0))
        else:
            surf.fill((10, 10, 15))

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        surf.blit(overlay, (0, 0))

        pw, ph = 860, 180
        px = cx - pw // 2
        py = H - ph - 30

        accent_col = _SPEAKER_COLORS.get(speaker, WHITE)

        box_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        box_surf.fill((0, 0, 0, 150))
        surf.blit(box_surf, (px, py))
        pygame.draw.rect(surf, accent_col, (px, py, pw, ph), 2, border_radius=8)

        pygame.draw.rect(
            surf, accent_col,
            (px, py, 4, ph),
            border_top_left_radius=4,
            border_bottom_left_radius=4
        )

        text_y = py + 35

        if speaker and speaker != "Narratore":
            txt(surf, speaker.upper(), px + 30, py + 20, accent_col, self._courier_bold)
            sep(surf, px + 30, py + 45, pw - 60, accent_col)
            text_y = py + 60

        max_visible_lines = 3
        wrapped_lines = self._get_wrapped_lines(text, pw - 80, self._courier_md)
        max_scroll = max(0, len(wrapped_lines) - max_visible_lines)

        self._scroll_y = max(0, min(self._scroll_y, max_scroll))

        visible_lines = wrapped_lines[self._scroll_y : self._scroll_y + max_visible_lines]
        lh = self._courier_md.get_height() + 10

        for i, line in enumerate(visible_lines):
            txt(surf, line, px + 30, text_y + i * lh, WHITE, self._courier_md)

        scroll_x = px + pw - 40
        if self._scroll_y > 0:
            txt(surf, "▲", scroll_x, text_y + 4, accent_col, self._courier_sm)
        if self._scroll_y < max_scroll:
            txt(surf, "▼", scroll_x, text_y + (max_visible_lines - 1) * lh + 4, accent_col, self._courier_sm)

        self._draw_image_progress(surf, cx, py - 20)

        blink = abs(math.sin(self._anim * 3.0)) > 0.4
        hint_col = accent_col if blink else (80, 80, 80)
        self._draw_hint_with_bold_arrows(surf, cx, py + ph + 14, hint_col)

    def _draw_end_card(self, surf: Surface, cx: int):
        last_key = _INTRO_LINES[-1][2]
        bg = self._bg_imgs.get(last_key)
        if bg:
            surf.blit(bg, (0, 0))

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surf.blit(overlay, (0, 0))

        pw, ph = 580, 210
        px = cx - pw // 2
        py = H // 2 - ph // 2

        glow_a = int(35 + 25 * math.sin(self._anim * 1.8))
        glow   = pygame.Surface((pw + 40, ph + 40), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*CYAN, glow_a), (0, 0, pw + 40, ph + 40), border_radius=20)
        surf.blit(glow, (px - 20, py - 20))

        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 22, 245))
        surf.blit(panel_surf, (px, py))
        pygame.draw.rect(surf, CYAN, (px, py, pw, ph), 2, border_radius=10)

        pulse     = int(200 + 55 * math.sin(self._anim * 2))
        title_col = (0, pulse, 255)
        txt(surf, "L'AVVENTURA INIZIA", cx, py + 50,
            title_col, self.fonts["xl"], center=True)

        sep(surf, px + 30, py + 85, pw - 60, CYAN)

        txt(surf, "Sei pronto ad affrontare Another World?",
            cx, py + 110, WHITE, self._courier_md, center=True)

        blink = abs(math.sin(self._anim * 3.0)) > 0.4
        btn_col = CYAN if blink else (40, 80, 90)
        txt(surf, "[ PREMI INVIO PER CONTINUARE ]",
            cx, py + 160, btn_col, self._courier_bold, center=True)

        txt(surf, "ESC  Torna al menu",
            cx, H - 30, GREY, self._courier_sm, center=True)

    def _get_wrapped_lines(self, text, max_w, font):
        """Restituisce una lista di stringhe formattate per andare a capo."""
        words = text.split(" ")
        lines, cur = [], ""
        for word in words:
            test = cur + word + " "
            if font.size(test)[0] < max_w:
                cur = test
            else:
                lines.append(cur.strip())
                cur = word + " "
        if cur.strip():
            lines.append(cur.strip())
        return lines

    def _draw_image_progress(self, surf: Surface, cx: int, y: int):
        """Mostra quante immagini distinte ci sono e quale è attiva."""
        seen: list[str] = []
        for _, _, k in _INTRO_LINES:
            if k not in seen:
                seen.append(k)

        cur_key = _INTRO_LINES[self._line][2]
        cur_idx = seen.index(cur_key)

        dot_r   = 5
        spacing = 22
        total_w = len(seen) * spacing
        start_x = cx - total_w // 2

        for i, key in enumerate(seen):
            color  = CYAN  if i == cur_idx else (50, 60, 70)
            radius = dot_r + 2 if i == cur_idx else dot_r
            pygame.draw.circle(surf, color, (start_x + i * spacing, y), radius)

    def _draw_hint_with_bold_arrows(self, surf, cx, y, color):
        parts = [
            ("← ", self._courier_bold),
            ("Indietro   ", self._courier_sm),
            ("→ ", self._courier_bold),
            ("Avanti   ", self._courier_sm),
            ("SPAZIO ", self._courier_bold),
            ("Salta    ", self._courier_sm),
            ("ESC ", self._courier_bold),
            ("Menu", self._courier_sm),
        ]

        total_w = sum(font.size(text)[0] for text, font in parts)
        x = cx - total_w // 2

        for text, font in parts:
            surf_part = font.render(text, True, color)
            surf.blit(surf_part, (x, y - font.get_height() // 2))
            x += surf_part.get_width()