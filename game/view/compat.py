"""
compat.py — Layer di compatibilità tra pygame vanilla e pygame-ce.

pygame-ce (Community Edition) è la fork attivamente mantenuta di pygame.
Questo modulo fornisce wrapper che usano le API ottimizzate di pygame-ce
quando disponibili, e fallback compatibili con pygame vanilla altrimenti.

Funzioni esposte
----------------
- ``check_pygame_ce``  : verifica e logga la versione di pygame in uso.
- ``draw_aa_rect``     : rettangolo con anti-aliasing (auto in pygame-ce).
- ``draw_aa_circle``   : cerchio con anti-aliasing.
- ``draw_aa_line``     : linea con anti-aliasing (``aaline`` se disponibile).
- ``draw_aa_polygon``  : poligono con anti-aliasing (``aapolygon`` in pygame-ce).
- ``make_alpha_surface``: Surface SRCALPHA con pre-moltiplicazione in pygame-ce.
- ``tint_surface``     : tinta moltiplicativa di una Surface.
- ``render_wrapped``   : testo a capo automatico (``wraplength`` nativo in pygame-ce).
- ``lerp_color``       : interpolazione lineare tra due colori.
- ``darken``           : scurisce un colore con un fattore moltiplicativo.
- ``brighten``         : schiarisce un colore (clampato a 255).
"""

from __future__ import annotations
import sys
import pygame


def check_pygame_ce() -> None:
    """Verifica che sia in uso pygame-ce anziché pygame vanilla.

    Logga una raccomandazione di installazione se viene rilevato pygame vanilla,
    altrimenti conferma la versione pygame-ce attiva.
    """
    is_ce = getattr(pygame, "IS_CE", False)
    if not is_ce:
        print("=" * 60)
        print("ATTENZIONE: stai usando pygame vanilla.")
        print("Disinstalla pygame e installa pygame-ce:")
        print()
        print("    pip uninstall pygame")
        print("    pip install pygame-ce")
        print("=" * 60)
    else:
        print(f"[OK] pygame-ce {pygame.version.ver}")


def draw_aa_rect(surf: pygame.Surface, color, rect,
                 border_radius: int = 0, width: int = 0) -> None:
    """Disegna un rettangolo (con bordo arrotondato opzionale).

    pygame-ce applica anti-aliasing automaticamente.
    In pygame vanilla il comportamento è identico a ``pygame.draw.rect``.

    Args:
        surf:          Surface di destinazione.
        color:         Colore RGB o RGBA.
        rect:          ``pygame.Rect`` o tupla (x, y, w, h).
        border_radius: Raggio degli angoli arrotondati (0 = angoli vivi).
        width:         Spessore del bordo (0 = riempimento).
    """
    pygame.draw.rect(surf, color, rect, width=width, border_radius=border_radius)


def draw_aa_circle(surf: pygame.Surface, color,
                   center, radius: int, width: int = 0) -> None:
    """Disegna un cerchio.

    Args:
        surf:   Surface di destinazione.
        color:  Colore RGB o RGBA.
        center: Coppia (x, y) del centro.
        radius: Raggio in pixel.
        width:  Spessore del bordo (0 = riempimento).
    """
    pygame.draw.circle(surf, color, center, radius, width=width)


def draw_aa_line(surf: pygame.Surface, color,
                 start, end, width: int = 1) -> None:
    """Disegna una linea con anti-aliasing se disponibile.

    Per linee di spessore 1, usa ``pygame.draw.aaline`` (disponibile sia in
    pygame vanilla che in pygame-ce). Per spessori maggiori, usa ``draw.line``.

    Args:
        surf:  Surface di destinazione.
        color: Colore RGB.
        start: Punto di partenza (x, y).
        end:   Punto di arrivo (x, y).
        width: Spessore in pixel.
    """
    if hasattr(pygame.draw, "aaline") and width == 1:
        pygame.draw.aaline(surf, color, start, end)
    else:
        pygame.draw.line(surf, color, start, end, width)


def draw_aa_polygon(surf: pygame.Surface, color, points,
                    width: int = 0) -> None:
    """Disegna un poligono con anti-aliasing se disponibile (pygame-ce).

    Args:
        surf:   Surface di destinazione.
        color:  Colore RGB.
        points: Lista di punti (x, y).
        width:  Spessore del bordo (0 = riempimento).
    """
    if hasattr(pygame.draw, "aapolygon"):
        pygame.draw.aapolygon(surf, color, points)
    else:
        pygame.draw.polygon(surf, color, points, width)


def make_alpha_surface(w: int, h: int) -> pygame.Surface:
    """Crea una Surface con canale alpha.

    In pygame-ce usa la pre-moltiplicazione alpha (``premul_alpha()``)
    per un compositing più accurato. In pygame vanilla usa ``SRCALPHA`` standard.

    Args:
        w: Larghezza in pixel.
        h: Altezza in pixel.

    Returns:
        Nuova ``pygame.Surface`` con supporto alpha.
    """
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if getattr(pygame, "IS_CE", False):
        surf = surf.premul_alpha()
    return surf


def tint_surface(surf: pygame.Surface, color: tuple) -> pygame.Surface:
    """Applica una tinta moltiplicativa a una Surface.

    Moltiplica ogni canale RGB della Surface per il colore fornito
    (``BLEND_RGB_MULT``). Non modifica la Surface originale.

    Args:
        surf:  Surface sorgente.
        color: Colore RGB moltiplicativo (255, 255, 255) = nessun cambiamento.

    Returns:
        Nuova Surface tinta.
    """
    tinted = surf.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return tinted


def render_wrapped(font: pygame.font.Font, text: str,
                   color: tuple, max_width: int) -> pygame.Surface:
    """Renderizza testo con a capo automatico entro ``max_width`` pixel.

    In pygame-ce usa ``wraplength`` nativo di ``Font.render()``.
    In pygame vanilla esegue word-wrapping manuale e impila le righe.

    Args:
        font:      Font pygame da usare.
        text:      Testo da renderizzare.
        color:     Colore RGB del testo.
        max_width: Larghezza massima in pixel prima del a capo.

    Returns:
        Surface con il testo renderizzato (altezza variabile in base al wrapping).
    """
    if getattr(pygame, "IS_CE", False):
        return font.render(text, True, color, wraplength=max_width)
    else:
        # Word-wrap manuale per pygame vanilla
        words  = text.split()
        lines  = []
        line   = ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        surfaces = [font.render(l, True, color) for l in lines]
        if not surfaces:
            return font.render("", True, color)
        total_h = sum(s.get_height() for s in surfaces)
        max_w   = max(s.get_width()  for s in surfaces)
        out     = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        y       = 0
        for s in surfaces:
            out.blit(s, (0, y))
            y += s.get_height()
        return out


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Interpolazione lineare tra due colori RGB.

    In pygame-ce usa ``pygame.Color.lerp()`` per accuratezza.
    In pygame vanilla usa interpolazione lineare per canale.

    Args:
        c1: Colore di partenza (R, G, B).
        c2: Colore di arrivo (R, G, B).
        t:  Parametro di interpolazione in [0.0, 1.0] (0 = c1, 1 = c2).

    Returns:
        Colore interpolato (R, G, B).
    """
    if getattr(pygame, "IS_CE", False):
        a = pygame.Color(*c1)
        b = pygame.Color(*c2)
        return tuple(a.lerp(b, t))[:3]
    else:
        return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def darken(color: tuple, factor: float = 0.6) -> tuple:
    """Scurisce un colore moltiplicando ogni canale per ``factor``.

    Args:
        color:  Colore RGB da scurire.
        factor: Fattore di scurimento (0.0 = nero, 1.0 = invariato).

    Returns:
        Colore scurito (R, G, B).
    """
    return tuple(int(c * factor) for c in color[:3])


def brighten(color: tuple, factor: float = 1.4) -> tuple:
    """Schiarisce un colore moltiplicando ogni canale per ``factor`` (clampato a 255).

    Args:
        color:  Colore RGB da schiarire.
        factor: Fattore di schiarimento (>1.0 = più luminoso).

    Returns:
        Colore schiarito (R, G, B), clampato a 255 per canale.
    """
    return tuple(min(255, int(c * factor)) for c in color[:3])
