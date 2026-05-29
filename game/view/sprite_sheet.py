"""
sprite_sheet.py — Caricamento e slicing di sprite sheet (grid e custom frames).

Supporta sprite sheet a griglia uniforme e fogli con frame di dimensioni diverse.
Espone ``get_frame(row, col)`` e ``get_animation(name)`` per le animazioni.
"""

from __future__ import annotations
import pygame
from pathlib import Path


class SpriteSheet:
    """Carica un'immagine e fornisce subsurface per ogni frame."""

    def __init__(self, path: str | Path,
                 color_key: tuple | None = (0, 0, 0)) -> None:
        self._sheet = pygame.image.load(str(path)).convert()
        if color_key is not None:
            self._sheet.set_colorkey(color_key)

    def get_frame(self, x: int, y: int, w: int, h: int,
                  scale: float = 1.0) -> pygame.Surface:
        frame = self._sheet.subsurface(pygame.Rect(x, y, w, h))
        if scale != 1.0:
            nw = max(1, int(w * scale))
            nh = max(1, int(h * scale))
            frame = pygame.transform.scale(frame, (nw, nh))
        return frame

    def get_row(self, row: int, frame_w: int, frame_h: int,
                count: int | None = None,
                scale: float = 1.0) -> list[pygame.Surface]:
        """Estrae una riga intera di frame."""
        n = count or (self._sheet.get_width() // frame_w)
        return [
            self.get_frame(i * frame_w, row * frame_h, frame_w, frame_h, scale)
            for i in range(n)
        ]


class Animation:
    """
    Sequenza di frame con fps configurabile.
    dt in millisecondi (da clock.tick()).
    """

    def __init__(self, frames: list[pygame.Surface],
                 fps: float = 8.0, loop: bool = True) -> None:
        self.frames  = frames
        self.fps     = fps
        self.loop    = loop
        self._t      = 0.0
        self.done    = False

    def update(self, dt: float) -> None:
        if self.done:
            return
        self._t += self.fps * dt / 1000.0
        if self._t >= len(self.frames):
            if self.loop:
                self._t %= len(self.frames)
            else:
                self._t  = len(self.frames) - 1
                self.done = True

    def reset(self) -> None:
        self._t  = 0.0
        self.done = False

    @property
    def current_frame(self) -> pygame.Surface:
        return self.frames[int(self._t)]

    def draw(self, surf: pygame.Surface, pos: tuple,
             flip_x: bool = False) -> None:
        frame = self.current_frame
        if flip_x:
            frame = pygame.transform.flip(frame, True, False)
        surf.blit(frame, pos)


class AnimatedSprite:
    """
    Gestisce più animazioni (idle, walk, attack, hurt) con transizioni.

    Uso:
        sprite = AnimatedSprite()
        sprite.add_state("idle",   Animation(idle_frames,   fps=6))
        sprite.add_state("walk",   Animation(walk_frames,   fps=10))
        sprite.add_state("attack", Animation(attack_frames, fps=12, loop=False))
        sprite.set_state("idle")
        sprite.update(dt)
        sprite.draw(surf, (x, y))
    """

    def __init__(self) -> None:
        self._states: dict[str, Animation] = {}
        self._current: str = ""
        self._prev:    str = ""
        self.flip_x        = False
        self.scale         = 1.0

    @property
    def image(self) -> pygame.Surface:
        """Restituisce il frame corrente dell'animazione attiva."""
        if not self._current or self._current not in self._states:
            return None
        return self._states[self._current].current_frame

    def add_state(self, name: str, anim: Animation) -> None:
        self._states[name] = anim

    def set_state(self, name: str, force: bool = False) -> None:
        if name not in self._states:
            return
        if name == self._current and not force:
            return
        self._prev    = self._current
        self._current = name
        self._states[name].reset()

    def update(self, dt: float) -> None:
        if not self._current:
            return
        anim = self._states[self._current]
        anim.update(dt)
        if anim.done and "idle" in self._states:
            self.set_state("idle")

    def draw(self, surf: pygame.Surface, pos: tuple) -> None:
        if not self._current:
            return
        anim = self._states[self._current]
        frame = anim.current_frame
        if self.flip_x:
            frame = pygame.transform.flip(frame, True, False)
        if self.scale != 1.0:
            w = max(1, int(frame.get_width()  * self.scale))
            h = max(1, int(frame.get_height() * self.scale))
            frame = pygame.transform.scale(frame, (w, h))
        surf.blit(frame, pos)

    @property
    def current_state(self) -> str:
        return self._current


class Tileset:
    """
    Carica un tileset a griglia uniforme e fornisce tile per indice.

    Esempio con un tileset 16×16 px per tile:
        ts = Tileset("assets/tileset.png", tile_w=16, tile_h=16)
        floor = ts.get(0)
        wall  = ts.get(1)
    """

    def __init__(self, path: str | Path,
                 tile_w: int = 16, tile_h: int = 16,
                 scale: int = 2,
                 color_key: tuple | None = (0, 0, 0)) -> None:
        self._sheet  = pygame.image.load(str(path)).convert()
        if color_key:
            self._sheet.set_colorkey(color_key)
        self.tile_w  = tile_w
        self.tile_h  = tile_h
        self.scale   = scale
        cols         = self._sheet.get_width()  // tile_w
        rows         = self._sheet.get_height() // tile_h
        self._tiles: list[pygame.Surface] = []
        for r in range(rows):
            for c in range(cols):
                t = self._sheet.subsurface(
                    pygame.Rect(c * tile_w, r * tile_h, tile_w, tile_h)
                )
                if scale != 1:
                    t = pygame.transform.scale(t, (tile_w * scale, tile_h * scale))
                self._tiles.append(t)

    def get(self, index: int) -> pygame.Surface | None:
        if 0 <= index < len(self._tiles):
            return self._tiles[index]
        return None

    def get_by_coord(self, col: int, row: int) -> pygame.Surface | None:
        cols = self._sheet.get_width() // self.tile_w
        return self.get(row * cols + col)

    @property
    def count(self) -> int:
        return len(self._tiles)



