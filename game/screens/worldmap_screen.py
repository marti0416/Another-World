"""
worldmap_screen.py — Screen della mappa del mondo (State GoF).

Visualizza la mappa completa con i distretti, le fazioni e gli obiettivi attivi.
Permette la navigazione a livello macro prima di entrare in un distretto.
"""

from __future__ import annotations
import math
import pygame

from game.screens.base_screen import Screen
from game.controller.game_manager import GameManager
from game.world.world_data import W, H, BG, BG2, BG3, CYAN, GREY, WHITE, GREEN, RED, YELLOW, MAGENTA, ORANGE
from game.view.draw_utils import txt
from game.systems.movement_system import MovementSystem

_CARD_X   = 24
_HDR_H    = 72
_FOOTER_H = 60
_MAP_PAD  = 12

_COL_RIVET  = (80, 255, 120)
_COL_ECHO   = (0,  220, 255)
_COL_GIANT  = (220, 40,  40)
_COL_RADAR  = (255, 200, 50)

_DISTRICT_TINT = (0, 180, 220, 18)


class WorldMapScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        self._map_surface  = None
        self._anim         = 0.0
        self.scale_x       = 1.0
        self.scale_y       = 1.0

        self.start_x   = _CARD_X + _MAP_PAD
        self.start_y   = _HDR_H  + _MAP_PAD
        self.map_view_w = W - (_CARD_X + _MAP_PAD) * 2
        self.map_view_h = H - _HDR_H - _FOOTER_H - _MAP_PAD * 2

    def on_enter(self):
        gs  = GameManager.get_instance()
        mov = gs.get_system(MovementSystem)
        if not mov or not getattr(mov, '_maps', None):
            return

        maps   = mov._maps
        city_w = mov._city_w
        city_h = mov._city_h

        if self._map_surface is not None:
            return

        self.scale_x = self.map_view_w / city_w
        self.scale_y = self.map_view_h / city_h

        self._map_surface = pygame.Surface((self.map_view_w, self.map_view_h))
        self._map_surface.fill((8, 10, 14))

        for m in maps:
            rx = int(m.offset_x * self.scale_x)
            ry = int(m.offset_y * self.scale_y)
            rw = max(1, int(m.width_px  * self.scale_x))
            rh = max(1, int(m.height_px * self.scale_y))

            if hasattr(m, 'bg_surface') and m.bg_surface:
                scaled = pygame.transform.smoothscale(m.bg_surface, (rw, rh))
                tint = pygame.Surface((rw, rh), pygame.SRCALPHA)
                tint.fill(_DISTRICT_TINT)
                scaled.blit(tint, (0, 0))
                self._map_surface.blit(scaled, (rx, ry))
            else:
                pygame.draw.rect(self._map_surface, (30, 45, 35), (rx, ry, rw, rh))

            pygame.draw.rect(self._map_surface, (40, 55, 65), (rx, ry, rw, rh), 1)

        for sy in range(0, self.map_view_h, 6):
            pygame.draw.line(self._map_surface, (0, 0, 0, 30), (0, sy), (self.map_view_w, sy))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            gs = GameManager.get_instance()
            if event.key in (pygame.K_m, pygame.K_ESCAPE):
                gs.screen = "explore"

    def update(self):
        self._anim += 0.05

    def draw(self, surf):
        gs = GameManager.get_instance()
        fn = self.fonts
        cx = W // 2

        surf.fill(BG)
        for sy in range(0, H, 4):
            v = int(3 + 2 * math.sin(self._anim + sy * 0.15))
            pygame.draw.line(surf, (0, v, v + 2), (0, sy), (W, sy))

        hdr = pygame.Surface((W, _HDR_H), pygame.SRCALPHA)
        hdr.fill((12, 14, 20, 220))
        surf.blit(hdr, (0, 0))
        pygame.draw.line(surf, CYAN, (0, _HDR_H), (W, _HDR_H), 2)

        pygame.draw.rect(surf, CYAN, (_CARD_X, 18, 4, 28), border_radius=2)
        txt(surf, "MAPPA GLOBALE", _CARD_X + 16, 20, CYAN, fn["bold"])

        radar_on = gs.flags.get("giants_visible_on_map", False)
        badge_lbl = "RADAR ATTIVO" if radar_on else "RADAR OFFLINE"
        badge_col = _COL_RADAR  if radar_on else GREY
        bw = fn["sm"].size(badge_lbl)[0] + 14
        pygame.draw.rect(surf, (badge_col[0]//5, badge_col[1]//5, badge_col[2]//5),
                         (_CARD_X + 220, 20, bw, 20), border_radius=4)
        pygame.draw.rect(surf, badge_col, (_CARD_X + 220, 20, bw, 20), 1, border_radius=4)
        txt(surf, badge_lbl, _CARD_X + 220 + bw // 2, 30, badge_col, fn["sm"], center=True)

        _draw_legend_dot(surf, fn, W - _CARD_X - 220, 26, _COL_RIVET, "Rivet")
        _draw_legend_dot(surf, fn, W - _CARD_X - 120, 26, _COL_ECHO,  "Echo")
        if radar_on:
            _draw_legend_dot(surf, fn, W - _CARD_X - 20, 26, _COL_GIANT, "Gigante", right=True)

        card_x = _CARD_X
        card_y = _HDR_H + 6
        card_w = W - _CARD_X * 2
        card_h = H - _HDR_H - _FOOTER_H - 12

        pygame.draw.rect(surf, (10, 14, 20),   (card_x, card_y, card_w, card_h), border_radius=6)
        pygame.draw.rect(surf, (35, 45, 55),   (card_x, card_y, card_w, card_h), 1, border_radius=6)
        pygame.draw.rect(surf, CYAN,           (card_x, card_y, 4, card_h), border_radius=2)

        mx = self.start_x
        my = self.start_y

        if self._map_surface:
            surf.blit(self._map_surface, (mx, my))

            pygame.draw.rect(surf, (0, 80, 100),
                             (mx - 1, my - 1, self.map_view_w + 2, self.map_view_h + 2), 1)
            pygame.draw.rect(surf, (0, 40, 55),
                             (mx - 2, my - 2, self.map_view_w + 4, self.map_view_h + 4), 1)

            mov = gs.get_system(MovementSystem)
            if mov:
                st1 = mov._players.get("p1") or mov._players.get("Rivet")
                if st1:
                    px1 = mx + int(st1.pixel_x * self.scale_x)
                    py1 = my + int(st1.pixel_y * self.scale_y)
                    _draw_player_marker(surf, px1, py1, _COL_RIVET, "R", self._anim, fn)

                st2 = mov._players.get("p2") or mov._players.get("Echo")
                if st2:
                    px2 = mx + int(st2.pixel_x * self.scale_x)
                    py2 = my + int(st2.pixel_y * self.scale_y)
                    _draw_player_marker(surf, px2, py2, _COL_ECHO, "E", self._anim + 1.0, fn)

            if radar_on:
                explore_scr = getattr(gs, "_explore_screen", None)
                live_npcs   = getattr(explore_scr, "_tutti_i_mob_reali", []) if explore_scr else []
                for npc in live_npcs:
                    if npc.get("faction") != "zombie":
                        continue
                    if "gigante" not in npc["name"].lower():
                        continue
                    npc_key = (npc["name"], tuple(npc.get("_local_pos") or npc["pos"]))
                    if npc_key in gs.defeated_npcs:
                        continue
                    gx = mx + int(npc["_px"] * self.scale_x)
                    gy = my + int(npc["_py"] * self.scale_y)
                    _draw_threat_marker(surf, gx, gy, self._anim, fn)
            else:
                ov = pygame.Surface((self.map_view_w, 24), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 100))
                surf.blit(ov, (mx, my + self.map_view_h - 28))
                txt(surf, "I Giganti non sono tracciati",
                    mx + self.map_view_w // 2,
                    my + self.map_view_h - 20,
                    YELLOW, fn["sm"], center=True)
        else:
            txt(surf, "Caricamento mappa...", card_x + card_w // 2,
                card_y + card_h // 2, GREY, fn["md"], center=True)

        bar_y = H - _FOOTER_H
        foot  = pygame.Surface((W, _FOOTER_H), pygame.SRCALPHA)
        foot.fill((10, 12, 18, 235))
        surf.blit(foot, (0, bar_y))
        pygame.draw.line(surf, CYAN, (0, bar_y), (W, bar_y), 2)

        buttons = [("M / ESC", "Chiudi mappa", CYAN)]
        btn_w   = W - _CARD_X * 2
        btn_top = bar_y + 6
        btn_hi  = 44
        btn_mid = btn_top + btn_hi // 2
        bx      = _CARD_X

        pygame.draw.rect(surf, (CYAN[0]//4, CYAN[1]//4, CYAN[2]//4),
                         (bx, btn_top, btn_w, btn_hi), border_radius=6)
        pygame.draw.rect(surf, CYAN, (bx, btn_top, btn_w, btn_hi), 1, border_radius=6)
        pygame.draw.line(surf, CYAN, (bx + 4, btn_top), (bx + btn_w - 4, btn_top), 2)
        txt(surf, "M / ESC", bx + btn_w // 2, btn_mid - 9, WHITE,         fn["sm"], center=True)
        txt(surf, "Chiudi mappa", bx + btn_w // 2, btn_mid + 9, (200, 205, 215), fn["sm"], center=True)



def _draw_legend_dot(surf, fn, x, y, col, label, right=False):
    """Pallino + etichetta per la legenda nell'header."""
    pygame.draw.circle(surf, col, (x, y), 5)
    pygame.draw.circle(surf, (col[0]//2, col[1]//2, col[2]//2), (x, y), 5, 1)
    lx = x - fn["sm"].size(label)[0] - 10 if right else x + 10
    txt(surf, label, lx, y - 6, col, fn["sm"])


def _draw_player_marker(surf, px, py, col, initial, anim, fn):
    """Marker animato per i giocatori: cerchio pulsante + iniziale."""
    pulse = abs(math.sin(anim * 2.5))
    glow_r = int(8 + pulse * 5)
    glow_s = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_s, (*col, int(60 * pulse)), (glow_r + 1, glow_r + 1), glow_r)
    surf.blit(glow_s, (px - glow_r - 1, py - glow_r - 1))

    pygame.draw.circle(surf, (col[0]//3, col[1]//3, col[2]//3), (px, py), 8)
    pygame.draw.circle(surf, col, (px, py), 8, 2)

    pygame.draw.circle(surf, col, (px, py), 4)

    s = fn["sm"].render(initial, True, col)
    surf.blit(s, s.get_rect(center=(px, py - 16)))

    pygame.draw.line(surf, col, (px, py + 8), (px, py + 12), 1)


def _draw_threat_marker(surf, gx, gy, anim, fn):
    """Marker minaccia per i Giganti: rombo rosso lampeggiante + raggi radar."""
    pulse  = abs(math.sin(anim * 3.5))
    col    = _COL_GIANT
    bright = (255, int(80 + 60 * pulse), int(80 + 60 * pulse))

    ring_r = int(10 + pulse * 14)
    ring_s = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(ring_s, (*col, int(120 * (1 - pulse))),
                       (ring_r + 2, ring_r + 2), ring_r, 1)
    surf.blit(ring_s, (gx - ring_r - 2, gy - ring_r - 2))

    size = 7
    pts  = [(gx, gy - size), (gx + size, gy), (gx, gy + size), (gx - size, gy)]
    pygame.draw.polygon(surf, bright, pts)
    pygame.draw.polygon(surf, col,    pts, 1)

    pygame.draw.circle(surf, (255, 255, 255), (gx, gy), 2)

    s = fn["sm"].render("!", True, bright)
    surf.blit(s, s.get_rect(center=(gx, gy - 18)))