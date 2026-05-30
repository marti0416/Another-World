"""
effects.py — Effetti visivi di animazione per il layer di rendering.

Contiene effetti come flash di colore, fade-in/out, particelle e testi fluttuanti.
Ogni effetto espone ``update()`` e ``draw(surf)`` e ha una property ``active``.
"""

from __future__ import annotations
import math
import random
import pygame
from game.view.compat import draw_aa_circle, draw_aa_line, make_alpha_surface


class Effect:
    def update(self) -> None: ...
    def draw(self, surf: pygame.Surface) -> None: ...
    def is_done(self) -> bool: return True


class Particle:
    __slots__ = ("x","y","vx","vy","life","max_life","color","radius")

    def __init__(self, pos: tuple, color: tuple,
                 speed: float = 3.0, life: int = 35) -> None:
        self.x, self.y = float(pos[0]), float(pos[1])
        angle     = random.uniform(0, math.tau)
        spd       = random.uniform(speed * 0.4, speed)
        self.vx   = math.cos(angle) * spd
        self.vy   = math.sin(angle) * spd - random.uniform(0, speed * 0.5)
        self.life = self.max_life = life + random.randint(-8, 8)
        self.color  = color
        self.radius = random.randint(2, 5)

    def update(self) -> None:
        self.x    += self.vx
        self.y    += self.vy
        self.vy   += 0.18
        self.vx   *= 0.97
        self.life -= 1

    def draw(self, surf: pygame.Surface) -> None:
        if self.life <= 0:
            return
        t     = self.life / self.max_life
        alpha = int(255 * t)
        r     = max(1, int(self.radius * t))
        c = (*self.color[:3], alpha)
        draw_aa_circle(surf, c, (int(self.x), int(self.y)), r)

    def is_done(self) -> bool:
        return self.life <= 0


class ParticleBurst(Effect):
    def __init__(self, pos: tuple, color: tuple,
                 count: int = 18, speed: float = 4.0) -> None:
        self._particles = [Particle(pos, color, speed) for _ in range(count)]

    def update(self) -> None:
        for p in self._particles:
            p.update()

    def draw(self, surf: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surf)

    def is_done(self) -> bool:
        return all(p.is_done() for p in self._particles)


class FloatingText(Effect):
    def __init__(self, text: str, pos: tuple, color: tuple,
                 font: pygame.font.Font, duration: int = 55) -> None:
        self._text     = text
        self._x        = float(pos[0])
        self._y        = float(pos[1])
        self._color    = color
        self._font     = font
        self._duration = duration
        self._timer    = duration
        self._surf     = font.render(text, True, color)

    def update(self) -> None:
        self._y    -= 1.2
        self._timer -= 1

    def draw(self, surf: pygame.Surface) -> None:
        if self._timer <= 0:
            return
        t     = self._timer / self._duration
        alpha = int(255 * min(1.0, t * 2))
        s     = self._surf.copy()
        s.set_alpha(alpha)
        r     = s.get_rect(center=(int(self._x), int(self._y)))
        surf.blit(s, r)

    def is_done(self) -> bool:
        return self._timer <= 0


class ScreenFlash(Effect):
    def __init__(self, color: tuple = (255, 255, 255),
                 duration: int = 12, size: tuple = (1200, 750)) -> None:
        self._color    = color
        self._duration = duration
        self._timer    = duration
        self._size     = size

    def update(self) -> None:
        self._timer -= 1

    def draw(self, surf: pygame.Surface) -> None:
        if self._timer <= 0:
            return
        t     = self._timer / self._duration
        alpha = int(180 * t)
        flash = make_alpha_surface(*self._size)
        flash.fill((*self._color[:3], alpha))
        surf.blit(flash, (0, 0))

    def is_done(self) -> bool:
        return self._timer <= 0


class HitRing(Effect):
    def __init__(self, pos: tuple, color: tuple = (255, 60, 60),
                 duration: int = 20, max_radius: int = 40) -> None:
        self._pos        = pos
        self._color      = color
        self._duration   = duration
        self._timer      = duration
        self._max_radius = max_radius

    def update(self) -> None:
        self._timer -= 1

    def draw(self, surf: pygame.Surface) -> None:
        if self._timer <= 0:
            return
        t      = 1.0 - self._timer / self._duration
        r      = int(self._max_radius * t)
        alpha  = int(255 * (1.0 - t))
        width  = max(1, int(3 * (1.0 - t) + 1))
        c      = (*self._color[:3], alpha)
        draw_aa_circle(surf, c, self._pos, max(1, r), width)

    def is_done(self) -> bool:
        return self._timer <= 0


class CameraShake:
    def __init__(self) -> None:
        self._intensity = 0.0
        self._timer     = 0
        self._offset    = (0, 0)

    def shake(self, intensity: float = 6.0, duration: int = 18) -> None:
        self._intensity = intensity
        self._timer     = duration

    def update(self) -> None:
        if self._timer > 0:
            t = self._timer / 18
            ox = random.uniform(-self._intensity * t, self._intensity * t)
            oy = random.uniform(-self._intensity * t, self._intensity * t)
            self._offset = (int(ox), int(oy))
            self._timer -= 1
        else:
            self._offset = (0, 0)

    @property
    def offset(self) -> tuple:
        return self._offset


class EffectManager:
    """Gestisce il ciclo di vita di tutti gli effetti attivi."""

    def __init__(self) -> None:
        self._effects: list[Effect] = []
        self.camera   = CameraShake()

    def add(self, effect: Effect) -> None:
        self._effects.append(effect)

    def hit(self, pos: tuple, damage: int,
            font: pygame.font.Font, color=(255,60,60)) -> None:
        """Shortcut: burst + numero danno + ring al colpo."""
        self.add(ParticleBurst(pos, color, count=12, speed=3.5))
        self.add(HitRing(pos, color))
        self.add(FloatingText(f"-{damage}", pos, color, font))
        self.camera.shake(5.0, 14)

    def heal(self, pos: tuple, amount: int,
             font: pygame.font.Font) -> None:
        color = (57, 255, 20)
        self.add(ParticleBurst(pos, color, count=10, speed=2.5))
        self.add(FloatingText(f"+{amount}", pos, color, font))

    def combo(self, pos: tuple, font: pygame.font.Font) -> None:
        self.add(ScreenFlash((0, 229, 255), duration=16))
        self.add(ParticleBurst(pos, (0, 229, 255), count=30, speed=5.0))
        self.add(FloatingText("COMBO!", pos, (0, 229, 255), font))
        self.camera.shake(8.0, 20)

    def update(self) -> None:
        self.camera.update()
        self._effects = [e for e in self._effects if not e.is_done()]
        for e in self._effects:
            e.update()

    def draw(self, surf: pygame.Surface) -> None:
        for e in self._effects:
            e.draw(surf)
