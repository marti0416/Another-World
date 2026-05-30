"""
speech_bubble.py — Fumetto di dialogo per i messaggi degli NPC durante l'esplorazione.

Gestisce il wrapping del testo, la coda di messaggio e il fade-out automatico.
"""

from __future__ import annotations
import pygame
import math
import textwrap
from dataclasses import dataclass, field
from typing import Optional

BUBBLE_DURATION_MS  = 3500
BUBBLE_FADE_MS      = 600
BUBBLE_MIN_W        = 80
BUBBLE_MAX_W        = 220
BUBBLE_PAD_X        = 10
BUBBLE_PAD_Y        = 7
BUBBLE_TAIL_H       = 10
BUBBLE_FONT_SIZE    = 13
BUBBLE_OFFSET_Y     = 70

SPEAKER_COLORS = {
    "Rivet": {
        "bg":     (30,  20,  20,  215),
        "border": (220, 80,  50),
        "text":   (255, 230, 200),
        "tail":   (220, 80,  50),
    },
    "Echo": {
        "bg":     (15,  25,  35,  215),
        "border": (60,  180, 255),
        "text":   (200, 230, 255),
        "tail":   (60,  180, 255),
    },
    "default": {
        "bg":     (20,  20,  20,  200),
        "border": (160, 160, 160),
        "text":   (230, 230, 230),
        "tail":   (160, 160, 160),
    },
    "enemy": {
        "bg":     (35,  10,  10,  220),
        "border": (200, 50,  50),
        "text":   (255, 200, 190),
        "tail":   (200, 50,  50),
    },
}


@dataclass
class SpeechBubble:
    """Una singola nuvoletta di dialogo."""
    owner_id:   str
    raw_text:   str
    created_at: int
    duration:   int = BUBBLE_DURATION_MS

    stack_offset: int = 0

    _lines:    list[str]  = field(default_factory=list, init=False)
    _rendered: bool       = False

    def get_display_text(self) -> str:
        """Rimuove il prefisso 'Nome: ' dal testo per la nuvoletta."""
        t = self.raw_text
        if ": " in t:
            t = t.split(": ", 1)[1]
        t = t.strip()
        if len(t) >= 2 and t[0] in ("'", '"') and t[-1] in ("'", '"'):
            t = t[1:-1]
        return t

    def alpha(self, now: int) -> int:
        """Calcola l'alpha 0-255 in base all'età della nuvoletta."""
        age = now - self.created_at
        remaining = self.duration - age
        if remaining <= 0:
            return 0
        if remaining < BUBBLE_FADE_MS:
            return int(255 * remaining / BUBBLE_FADE_MS)
        if age < 150:
            return int(255 * age / 150)
        return 255

    def is_expired(self, now: int) -> bool:
        return (now - self.created_at) >= self.duration


class SpeechBubbleManager:
    """
    Gestisce la coda di nuvolette attive.
    Una nuvoletta per personaggio alla volta (la nuova sovrascrive la vecchia).
    """

    def __init__(self):
        self._bubbles: dict[str, SpeechBubble] = {}

    def add(self, owner_id: str, text: str, duration: int = BUBBLE_DURATION_MS):
        """Aggiunge o sostituisce la nuvoletta per il personaggio indicato."""
        now = pygame.time.get_ticks()
        other_id = "Echo" if owner_id == "Rivet" else "Rivet"
        stack = 0 if (other_id in self._bubbles and
                       not self._bubbles[other_id].is_expired(now)) else 0
        self._bubbles[owner_id] = SpeechBubble(
            owner_id=owner_id,
            raw_text=text,
            created_at=now,
            duration=duration,
            stack_offset=stack,
        )

    def add_from_bark(self, bark_text: str, duration: int = BUBBLE_DURATION_MS):
        """
        Analizza il testo del bark ('Rivet: ...' / 'Echo: ...') e lo instrada
        al personaggio corretto. Se non riconosce il parlante, usa 'Rivet'.
        """
        if bark_text.startswith("Echo"):
            self.add("Echo", bark_text, duration)
        elif bark_text.startswith("Rivet"):
            self.add("Rivet", bark_text, duration)
        else:
            self.add("Rivet", bark_text, duration)

    def update(self):
        """Rimuove le nuvolette scadute."""
        now = pygame.time.get_ticks()
        expired = [k for k, b in self._bubbles.items() if b.is_expired(now)]
        for k in expired:
            del self._bubbles[k]

    def draw(self,
             viewport: pygame.Surface,
             font: pygame.font.Font,
             positions: dict[str, tuple[int, int]]):
        """
        Disegna le nuvolette attive.

        Args:
            viewport:  la superficie della mappa (MAP_VIEW)
            font:      font piccolo già caricato
            positions: { "Rivet": (screen_x, screen_y), "Echo": (screen_x, screen_y) }
                       screen_y = coordinata Y del CENTRO del personaggio in pixel di viewport
        """
        now = pygame.time.get_ticks()
        self.update()

        for owner_id, bubble in self._bubbles.items():
            alpha = bubble.alpha(now)
            if alpha <= 0:
                continue
            if owner_id not in positions:
                continue

            sx, sy = positions[owner_id]
            display = bubble.get_display_text()
            cols = SPEAKER_COLORS.get(owner_id, SPEAKER_COLORS["default"])

            lines = _wrap_text(display, font, BUBBLE_MAX_W - BUBBLE_PAD_X * 2)
            if not lines:
                continue

            line_h   = font.get_linesize()
            text_w   = max(font.size(l)[0] for l in lines)
            text_h   = line_h * len(lines)
            box_w    = max(BUBBLE_MIN_W, text_w + BUBBLE_PAD_X * 2)
            box_h    = text_h + BUBBLE_PAD_Y * 2

            bx = sx - box_w // 2
            by = sy - BUBBLE_OFFSET_Y - bubble.stack_offset - box_h

            vw, vh = viewport.get_size()
            bx = max(4, min(vw - box_w - 4, bx))
            by = max(4, by)

            total_h = box_h + BUBBLE_TAIL_H
            surf = pygame.Surface((box_w, total_h), pygame.SRCALPHA)

            bg_col  = (*cols["bg"][:3], int(cols["bg"][3] * alpha / 255))
            brd_col = (*cols["border"], alpha)
            pygame.draw.rect(surf, bg_col,  (0, 0, box_w, box_h), border_radius=8)
            pygame.draw.rect(surf, brd_col, (0, 0, box_w, box_h), 2, border_radius=8)

            tail_cx = box_w // 2
            tail_points = [
                (tail_cx - 7, box_h),
                (tail_cx + 7, box_h),
                (tail_cx,     box_h + BUBBLE_TAIL_H),
            ]
            pygame.draw.polygon(surf, bg_col, tail_points)
            pygame.draw.lines(surf, brd_col, False,
                              [(tail_cx - 7, box_h),
                               (tail_cx,     box_h + BUBBLE_TAIL_H),
                               (tail_cx + 7, box_h)], 2)

            txt_col = (*cols["text"], alpha)
            for i, line in enumerate(lines):
                rendered = font.render(line, True, cols["text"])
                rendered.set_alpha(alpha)
                lx = BUBBLE_PAD_X
                ly = BUBBLE_PAD_Y + i * line_h
                surf.blit(rendered, (lx, ly))

            viewport.blit(surf, (bx, by))

    def has_active(self) -> bool:
        now = pygame.time.get_ticks()
        return any(not b.is_expired(now) for b in self._bubbles.values())



def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    """Spezza il testo in righe che non superano max_w pixel."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def infer_owner(bark_text: str) -> str:
    """Deduce il proprietario di un bark dal testo."""
    if bark_text.startswith("Echo"):
        return "Echo"
    return "Rivet"
