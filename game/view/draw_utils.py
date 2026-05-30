"""
draw_utils.py — Primitive di disegno riutilizzabili e helper per la mappa.

Funzioni esposte
----------------
- ``txt``         : renderizza testo su una surface con allineamento opzionale.
- ``hp_bar``      : barra HP colorata con etichetta.
- ``panel``       : riquadro con bordo arrotondato.
- ``sep``         : linea separatrice orizzontale.
- ``dist_map``    : distanza di Manhattan tra due coordinate tile.
- ``near_obj``    : trova il primo oggetto entro un raggio su una lista.
- ``cur_district``: restituisce il distretto corrente in base alla posizione.
- ``draw_map``    : disegna la mappa di esplorazione centrata sul giocatore.
"""

from __future__ import annotations
import pygame
from pygame import Surface

from game.world.world_data import (
    TILE, MAP_COLS, MAP_ROWS,
    BG2, CYAN, GREEN, YELLOW, GREY, WHITE, DARKGREY, RED,
    DISTRICTS, LOOT_SPOTS, TERMINALS, NPCS,
)


def txt(surf: Surface, text: str, x: int, y: int,
        color=WHITE, font=None, center: bool = False) -> pygame.Rect:
    """Renderizza testo sulla surface e restituisce il Rect occupato.

    Args:
        surf:   Surface di destinazione.
        text:   Stringa da renderizzare.
        x, y:   Coordinate di posizionamento (topleft o center).
        color:  Colore RGB del testo (default: WHITE).
        font:   Font pygame da usare (obbligatorio).
        center: Se ``True``, (x, y) è il centro del testo; altrimenti è il topleft.

    Returns:
        ``pygame.Rect`` occupato dal testo disegnato.
    """
    s = font.render(text, True, color)
    r = s.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    surf.blit(s, r)
    return r


def hp_bar(surf: Surface, x: int, y: int, val: int, mx: int,
           w: int = 160, h: int = 12, font=None) -> None:
    """Disegna una barra HP con colore adattivo e sfondo scuro.

    Il colore della barra cambia in base alla percentuale di HP:
    - Verde (> 50%), Giallo (25–50%), Rosso (< 25%).

    Args:
        surf:    Surface di destinazione.
        x, y:   Posizione topleft della barra.
        val:     HP attuali.
        mx:      HP massimi.
        w:       Larghezza totale della barra in pixel (default 160).
        h:       Altezza della barra in pixel (default 12).
        font:    Font per l'etichetta (non usato in questa versione).
    """
    ratio = val / max(1, mx)
    color = GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
    pygame.draw.rect(surf, DARKGREY, (x, y, w, h))
    pygame.draw.rect(surf, color,    (x, y, int(w * ratio), h))
    pygame.draw.rect(surf, GREY,     (x, y, w, h), 1)


def panel(surf: Surface, x: int, y: int, w: int, h: int,
          color=BG2, border=GREY, radius: int = 6) -> None:
    """Disegna un riquadro con sfondo e bordo arrotondato.

    Args:
        surf:   Surface di destinazione.
        x, y:   Posizione topleft del pannello.
        w, h:   Larghezza e altezza in pixel.
        color:  Colore di riempimento (default: BG2).
        border: Colore del bordo (default: GREY).
        radius: Raggio degli angoli arrotondati in pixel (default 6).
    """
    pygame.draw.rect(surf, color,  (x, y, w, h), border_radius=radius)
    pygame.draw.rect(surf, border, (x, y, w, h), 1, border_radius=radius)


def sep(surf: Surface, x: int, y: int, w: int, color=GREY) -> None:
    """Disegna una linea separatrice orizzontale.

    Args:
        surf:   Surface di destinazione.
        x, y:   Punto di partenza della linea.
        w:      Lunghezza della linea in pixel.
        color:  Colore della linea (default: GREY).
    """
    pygame.draw.line(surf, color, (x, y), (x + w, y))


def dist_map(a: tuple, b: tuple) -> int:
    """Calcola la distanza di Manhattan tra due coordinate tile.

    Args:
        a: Prima coordinata (col, row).
        b: Seconda coordinata (col, row).

    Returns:
        Distanza di Manhattan in tile.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def near_obj(pos: tuple, items: list, r: int = 1):
    """Restituisce il primo elemento in ``items`` entro raggio ``r`` da ``pos``.

    Supporta sia liste di tuple ``(col, row)`` che liste di dict con chiave ``pos``.

    Args:
        pos:   Posizione di riferimento (col, row).
        items: Lista di tuple o dict con chiave ``pos``.
        r:     Raggio massimo in tile (default 1).

    Returns:
        Il primo elemento trovato entro il raggio, oppure ``None``.
    """
    return next(
        (x for x in items
         if abs(pos[0] - (x[0] if isinstance(x, tuple) else x["pos"][0])) <= r
         and abs(pos[1] - (x[1] if isinstance(x, tuple) else x["pos"][1])) <= r),
        None,
    )


def cur_district(pos: tuple) -> tuple:
    """Restituisce il distretto corrente in base alla posizione tile del giocatore.

    Il layout della mappa è diviso in quattro quadranti in base ai confini
    delle immagini (larghezza 195 tile, altezza 146 tile):

    - col < 130, row < 73  → Città
    - col ≥ 130, row < 73  → Aeroporto Militare
    - col < 130, row ≥ 73  → Zona Rurale
    - col ≥ 130, row ≥ 73  → Fabbrica Chimica

    Args:
        pos: Posizione corrente del giocatore (col, row) nella città.

    Returns:
        Coppia ``(key, dati_distretto)`` dove ``key`` è la chiave in ``DISTRICTS``
        e ``dati_distretto`` è la tupla ``(nome, sigla, colore)``.
    """
    wx, wy = pos[0], pos[1]
    in_right_half = wx >= 130
    in_lower_half = wy >= 73

    if not in_right_half and not in_lower_half:
        key = (90, 60)
    elif in_right_half and not in_lower_half:
        key = (160, 20)
    elif not in_right_half and in_lower_half:
        key = (30, 120)
    else:
        key = (160, 120)

    return key, DISTRICTS[key]


def draw_map(surf: Surface, gs, fx: int, fy: int, fn_sm) -> tuple[int, int]:
    """Disegna la mappa di esplorazione centrata sul giocatore P1.

    Renderizza una finestra di ``MAP_COLS × MAP_ROWS`` tile attorno alla posizione
    corrente di P1, colorando il sfondo in base al distretto e sovrapponendo:
    - Simboli ``$`` (giallo) per i loot spot non ancora saccheggiati.
    - Simboli ``T`` (ciano) per i terminali hackabili.
    - Simboli ``@`` (verde) per gli NPC.
    - Simbolo ``H`` o ``S`` (giallo) per P2.
    - Simbolo ``★`` (ciano) per P1.

    Args:
        surf:  Surface di destinazione (canvas di gioco).
        gs:    ``GameManager`` con attributi ``p1``, ``p2``, ``player``,
               ``Rivet``, ``looted``.
        fx:    Offset X della camera (non usato; la camera è centrata su P1).
        fy:    Offset Y della camera (non usato).
        fn_sm: Font di dimensione piccola per i simboli sulla mappa.

    Returns:
        Coppia ``(map_w, map_h)`` con le dimensioni in pixel della mappa disegnata.
    """
    px, py = gs.p1
    cam_x  = px - MAP_COLS // 2
    cam_y  = py - MAP_ROWS // 2
    map_w  = MAP_COLS * TILE
    map_h  = MAP_ROWS * TILE

    map_surf = pygame.Surface((map_w, map_h))
    map_surf.fill((5, 5, 16))

    # Sfondo tile colorato per distretto
    for row in range(MAP_ROWS):
        for col in range(MAP_COLS):
            wx = col + cam_x; wy = row + cam_y
            sx = col * TILE;  sy = row * TILE

            bg = (5, 5, 16)
            for (dx, dy), (_, _, dcol) in DISTRICTS.items():
                if abs(wx - dx) <= 3 and abs(wy - dy) <= 3:
                    bg = dcol
            pygame.draw.rect(map_surf, bg, (sx, sy, TILE, TILE))
            pygame.draw.rect(map_surf, (bg[0]+8, bg[1]+8, bg[2]+8),
                             (sx, sy, TILE, TILE), 1)

            cx = sx + TILE // 2; cy = sy + TILE // 2

            # Simboli punti di interesse
            for lp in LOOT_SPOTS:
                if lp not in gs.looted and lp == (wx, wy):
                    s = fn_sm.render("$", True, YELLOW)
                    map_surf.blit(s, s.get_rect(center=(cx, cy)))
            for tp in TERMINALS:
                if tp == (wx, wy):
                    s = fn_sm.render("T", True, CYAN)
                    map_surf.blit(s, s.get_rect(center=(cx, cy)))
            for npc in NPCS:
                if npc["pos"] == (wx, wy):
                    s = fn_sm.render("@", True, GREEN)
                    map_surf.blit(s, s.get_rect(center=(cx, cy)))

    # Icona P2 (gialla)
    qx, qy = gs.p2
    p2sx = (qx - cam_x) * TILE; p2sy = (qy - cam_y) * TILE
    pygame.draw.rect(map_surf, (50, 50, 0), (p2sx+1, p2sy+1, TILE-2, TILE-2))
    pygame.draw.rect(map_surf, YELLOW,      (p2sx,   p2sy,   TILE,   TILE), 1)
    p2lbl = "H" if gs.player is gs.Rivet else "S"
    s2 = fn_sm.render(p2lbl, True, YELLOW)
    map_surf.blit(s2, s2.get_rect(center=(p2sx + TILE // 2, p2sy + TILE // 2)))

    # Icona P1 (ciano, stella)
    p1sx = (px - cam_x) * TILE; p1sy = (py - cam_y) * TILE
    pygame.draw.rect(map_surf, (0, 30, 60), (p1sx+1, p1sy+1, TILE-2, TILE-2))
    pygame.draw.rect(map_surf, CYAN,        (p1sx,   p1sy,   TILE,   TILE), 2)
    s1 = fn_sm.render("★", True, CYAN)
    map_surf.blit(s1, s1.get_rect(center=(p1sx + TILE // 2, p1sy + TILE // 2)))

    # Incolla la mappa sul canvas principale con bordo ciano
    surf.blit(map_surf, (8, 8))
    pygame.draw.rect(surf, CYAN, (7, 7, map_w + 2, map_h + 2), 1)

    return map_w, map_h
