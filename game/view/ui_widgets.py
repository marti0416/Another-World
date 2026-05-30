"""
ui_widgets.py — Componenti UI riutilizzabili (pulsanti, barre, pannelli, dialogo).

Ogni widget espone ``draw(surf)`` e ``handle_event(event)``.
I widget sono indipendenti dalle screen: vengono istanziati e passati come parametri.
"""

from __future__ import annotations
import math
from abc import ABC, abstractmethod
import pygame
from game.view.compat import draw_aa_rect, draw_aa_line, lerp_color



class UIComponent(ABC):
    """Component astratto — interfaccia comune a tutti i widget (Leaf e Composite).

    Garantisce che Leaf e Composite siano trattati uniformemente:
    una Screen può chiamare root.draw(surf) senza conoscere
    se root è un singolo Button o un Panel con decine di figli.
    """

    @abstractmethod
    def draw(self, surf: pygame.Surface) -> None:
        """Disegna il componente (e i suoi figli, se Composite)."""
        ...

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Gestisce un evento pygame. Restituisce True se l'evento è consumato."""
        return False

    def update(self) -> None:
        """Aggiorna lo stato interno (animazioni, hover, ecc.)."""
        pass



class Button(UIComponent):
    def __init__(self, rect: tuple, label: str,
                 color: tuple, font: pygame.font.Font,
                 on_click=None) -> None:
        self.rect      = pygame.Rect(rect)
        self.label     = label
        self.color     = color
        self.font      = font
        self.on_click  = on_click
        self._hovered  = False
        self._pressed  = False
        self._anim     = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN and self._hovered:
            self._pressed = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if self._pressed and self._hovered:
                self._pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self._pressed = False

        return False

    def update(self) -> None:
        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my)
        self._anim += 0.08

    def draw(self, surf: pygame.Surface) -> None:
        scale  = 0.96 if self._pressed else (1.02 if self._hovered else 1.0)
        w  = int(self.rect.width  * scale)
        h  = int(self.rect.height * scale)
        rx = self.rect.centerx - w // 2
        ry = self.rect.centery - h // 2

        bg_color = lerp_color(self.color, (255,255,255), 0.25) if self._hovered else self.color
        if self._pressed:
            bg_color = lerp_color(self.color, (0,0,0), 0.3)
        draw_aa_rect(surf, bg_color, (rx, ry, w, h), border_radius=6)
        border = lerp_color(self.color, (255,255,255), 0.6) if self._hovered else self.color
        draw_aa_rect(surf, border, (rx, ry, w, h), border_radius=6, width=2)
        fg = (10, 10, 10) if self._hovered or self._pressed else (230, 230, 230)
        ts = self.font.render(self.label, True, fg)
        surf.blit(ts, ts.get_rect(center=(rx + w//2, ry + h//2)))



class HealthBar(UIComponent):
    """Barra HP animata con transizione smooth (il fill si sposta gradualmente)."""

    def __init__(self, rect: tuple, font: pygame.font.Font) -> None:
        self.rect    = pygame.Rect(rect)
        self.font    = font
        self._target = 1.0
        self._shown  = 1.0

    def set_values(self, val: int, mx: int) -> None:
        self._target = val / max(1, mx)
        self._val    = val
        self._mx     = mx

    def update(self) -> None:
        self._shown += (self._target - self._shown) * 0.12

    def draw(self, surf: pygame.Surface) -> None:
        x, y, w, h = self.rect

        draw_aa_rect(surf, (34, 34, 34), (x, y, w, h), border_radius=4)

        fill_w = max(0, int(w * self._shown))
        r      = self._shown
        color  = (57,255,20) if r > 0.5 else ((255,214,0) if r > 0.25 else (255,45,45))
        if fill_w > 0:
            draw_aa_rect(surf, color, (x, y, fill_w, h), border_radius=4)

        if self._target < self._shown - 0.01:
            ghost_w = max(0, int(w * self._shown))
            draw_aa_rect(surf, (120, 30, 30),
                         (x + int(w * self._target), y,
                          ghost_w - int(w * self._target), h),
                         border_radius=4)

        draw_aa_rect(surf, (85,85,85), (x, y, w, h), border_radius=4, width=1)

        if hasattr(self, "_val"):
            label = f"{self._val}/{self._mx}"
            ts = self.font.render(label, True, (230, 230, 230))
            surf.blit(ts, ts.get_rect(center=(x + w//2, y + h//2)))



class SelectMenu(UIComponent):
    """Menu verticale navigabile con tastiera e mouse.
    Ogni opzione è (label, color, callback).
    """

    def __init__(self, rect: tuple,
                 options: list[tuple],
                 font: pygame.font.Font,
                 row_h: int = 48) -> None:
        self.rect    = pygame.Rect(rect)
        self.options = options
        self.font    = font
        self.row_h   = row_h
        self.cursor  = 0
        self._anim   = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.cursor = (self.cursor - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.cursor = (self.cursor + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                cb = self.options[self.cursor][2]
                if cb: cb()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            for i in range(len(self.options)):
                row_rect = pygame.Rect(self.rect.x, self.rect.y + i * self.row_h,
                                       self.rect.width, self.row_h - 4)
                if row_rect.collidepoint(mx, my):
                    self.cursor = i
                    cb = self.options[i][2]
                    if cb: cb()
                    return True
        return False

    def update(self) -> None:
        self._anim += 0.06

    def draw(self, surf: pygame.Surface) -> None:
        for i, (label, color, _) in enumerate(self.options):
            ry  = self.rect.y + i * self.row_h
            sel = (i == self.cursor)
            rw  = self.rect.width

            if sel:
                pulse = int(30 + 20 * math.sin(self._anim * 3))
                bg    = (color[0]//6, color[1]//6 + pulse//10, color[2]//6)
                draw_aa_rect(surf, bg,    (self.rect.x, ry, rw, self.row_h-4), border_radius=5)
                draw_aa_rect(surf, color, (self.rect.x, ry, rw, self.row_h-4), border_radius=5, width=2)
                ax = self.rect.x - 18
                ay = ry + (self.row_h - 4) // 2
                pygame.draw.polygon(surf, color,
                                    [(ax, ay), (ax-8, ay-6), (ax-8, ay+6)])
            ts  = self.font.render(label, True, color if sel else (130,130,130))
            surf.blit(ts, (self.rect.x + 16, ry + (self.row_h-4)//2 - ts.get_height()//2))



class LogBox(UIComponent):
    """Box di testo scrollabile con colori per riga.
    entries: list of (text, color)
    """

    def __init__(self, rect: tuple,
                 font: pygame.font.Font,
                 bg: tuple = (18,18,28),
                 line_h: int = 18) -> None:
        self.rect   = pygame.Rect(rect)
        self.font   = font
        self.bg     = bg
        self.line_h = line_h
        self._entries: list[tuple[str, tuple]] = []

    def add(self, text: str, color: tuple = (224, 224, 224)) -> None:
        self._entries.append((text, color))

    def clear(self) -> None:
        self._entries.clear()

    def draw(self, surf: pygame.Surface) -> None:
        draw_aa_rect(surf, self.bg, self.rect, border_radius=4)
        draw_aa_rect(surf, (85,85,85), self.rect, border_radius=4, width=1)

        visible = self.rect.height // self.line_h
        entries = self._entries[-visible:]

        for i, (text, color) in enumerate(entries):
            alpha = min(255, (i + 1) * (255 // max(1, len(entries))))
            ts = self.font.render(text[:52], True, color)
            ts.set_alpha(alpha)
            surf.blit(ts, (self.rect.x + 8,
                           self.rect.y + 4 + i * self.line_h))



class Tooltip(UIComponent):
    def __init__(self, font: pygame.font.Font,
                 padding: int = 8) -> None:
        self.font    = font
        self.padding = padding
        self._text   = ""
        self._active = False

    def show(self, text: str) -> None:
        self._text   = text
        self._active = True

    def hide(self) -> None:
        self._active = False

    def draw(self, surf: pygame.Surface) -> None:
        if not self._active or not self._text:
            return
        mx, my = pygame.mouse.get_pos()
        ts  = self.font.render(self._text, True, (224, 224, 224))
        tw, th = ts.get_size()
        p   = self.padding
        bx  = mx + 14
        by  = my - th - p * 2
        if bx + tw + p * 2 > surf.get_width():
            bx = mx - tw - p * 2 - 14
        if by < 0:
            by = my + 20
        draw_aa_rect(surf, (30, 30, 40), (bx - p, by - p, tw + p*2, th + p*2), border_radius=4)
        draw_aa_rect(surf, (85, 85, 85), (bx - p, by - p, tw + p*2, th + p*2), border_radius=4, width=1)
        surf.blit(ts, (bx, by))



class Panel(UIComponent):
    """Composite GoF: pannello con sfondo e titolo che gestisce una lista di figli.

    draw()         → disegna sfondo/titolo propri, poi delega a ogni figlio
    handle_event() → propaga l'evento a ogni figlio in ordine; si ferma al
                     primo che lo consuma (restituisce True)
    update()       → propaga update() a ogni figlio

    Uso:
        panel = Panel((x, y, w, h), title="Inventario", title_font=font)
        panel.add(HealthBar(...))
        panel.add(Button(...))
        panel.draw(surf)
    """

    def __init__(self, rect: tuple,
                 bg: tuple = (22,22,22),
                 border: tuple = (85,85,85),
                 radius: int = 6,
                 title: str = "",
                 title_font: pygame.font.Font | None = None,
                 title_color: tuple = (0, 229, 255)) -> None:
        self.rect        = pygame.Rect(rect)
        self.bg          = bg
        self.border      = border
        self.radius      = radius
        self.title       = title
        self.title_font  = title_font
        self.title_color = title_color
        self._children: list[UIComponent] = []


    def add(self, child: UIComponent) -> "Panel":
        """Aggiunge un figlio al Composite. Restituisce self per chaining."""
        self._children.append(child)
        return self

    def remove(self, child: UIComponent) -> None:
        """Rimuove un figlio dal Composite."""
        self._children.remove(child)

    def children(self) -> list[UIComponent]:
        """Restituisce la lista dei figli (read-only view)."""
        return list(self._children)


    def draw(self, surf: pygame.Surface) -> None:
        draw_aa_rect(surf, self.bg,     self.rect, border_radius=self.radius)
        draw_aa_rect(surf, self.border, self.rect, border_radius=self.radius, width=1)
        if self.title and self.title_font:
            ts = self.title_font.render(self.title, True, self.title_color)
            surf.blit(ts, (self.rect.x + 12, self.rect.y + 10))
        for child in self._children:
            child.draw(surf)

    def handle_event(self, event: pygame.event.Event) -> bool:
        for child in self._children:
            if child.handle_event(event):
                return True
        return False

    def update(self) -> None:
        for child in self._children:
            child.update()



class WidgetGroup(UIComponent):
    """Composite puro senza sfondo né titolo.

    Raggruppa widget logicamente correlati (es. tutte le HealthBar di battaglia)
    senza aggiungere visual overhead. Utile quando si vuole gestire un insieme
    di Leaf con una singola chiamata ma senza layout visivo.

    Uso:
        hbar_group = WidgetGroup()
        hbar_group.add(HealthBar(...))
        hbar_group.add(HealthBar(...))
        hbar_group.update()
        hbar_group.draw(surf)
    """

    def __init__(self) -> None:
        self._children: list[UIComponent] = []

    def add(self, child: UIComponent) -> "WidgetGroup":
        """Aggiunge un figlio. Restituisce self per chaining."""
        self._children.append(child)
        return self

    def remove(self, child: UIComponent) -> None:
        """Rimuove un figlio. Se il figlio non è presente, l'operazione è no-op."""
        try:
            self._children.remove(child)
        except ValueError:
            pass

    def children(self) -> list[UIComponent]:
        return list(self._children)

    def draw(self, surf: pygame.Surface) -> None:
        for child in self._children:
            child.draw(surf)

    def handle_event(self, event: pygame.event.Event) -> bool:
        for child in self._children:
            if child.handle_event(event):
                return True
        return False

    def update(self) -> None:
        for child in self._children:
            child.update()


