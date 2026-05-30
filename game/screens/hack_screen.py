"""
hack_screen.py — Screen del mini-gioco di hacking (State GoF).

Presenta il puzzle di hacking (Pipe/Radar/Node) al giocatore Echo
e gestisce l'input, la validazione della soluzione e la transizione.
"""

from __future__ import annotations
import math
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import W, H, BG, BG2, BG3, CYAN, GREEN, RED, YELLOW, MAGENTA, GREY, WHITE, DARKGREY, PANEL, ORANGE, FPS, TILE, MAP_COLS, MAP_ROWS, TILE
from game.view.draw_utils import txt, hp_bar, panel, sep, near_obj, cur_district
from game.controller.game_manager import GameManager
from game.dialogue.dialogue_barks import get_bark, HACK_BARKS


class HackScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        self._anim = 0.0

    def handle_event(self, event):
        gs = GameManager.get_instance()
        if event.type != pygame.KEYDOWN: return
        k   = event.key
        ch  = event.unicode
        hack = gs.hack_sys

        if hack.is_locked_out:
            gs.flash("SISTEMA BLOCCATO!", 80)
            return

        if k == pygame.K_ESCAPE:
            msg = hack.force_lockout()
            gs.log(gs.hlog, msg)
            gs.log(gs.wlog, get_bark(HACK_BARKS, "system_locked"))
            gs.flash("LOCKOUT — DISCONNESSIONE FORZATA", 100)
            gs.screen = "explore"
            return

        if gs.puzzle_type in ("slot", "pipe"):
            if k == pygame.K_UP: gs.log(gs.hlog, hack.submit_input("UP"))
            elif k == pygame.K_DOWN: gs.log(gs.hlog, hack.submit_input("DOWN"))
            elif k == pygame.K_LEFT: gs.log(gs.hlog, hack.submit_input("LEFT"))
            elif k == pygame.K_RIGHT: gs.log(gs.hlog, hack.submit_input("RIGHT"))
            elif k == pygame.K_r: gs.log(gs.hlog, hack.submit_input("ROTATE"))
        elif gs.puzzle_type == "radar":
            if k == pygame.K_LEFT: gs.log(gs.hlog, hack.submit_input("LEFT"))
            elif k == pygame.K_RIGHT: gs.log(gs.hlog, hack.submit_input("RIGHT"))
            elif k == pygame.K_SPACE: gs.log(gs.hlog, hack.submit_input("PING"))
        elif gs.puzzle_type == "node":
            if ch.isdigit(): gs.log(gs.hlog, hack.submit_input(ch))

        p = hack._current_puzzle
        if p and p.is_solved():
            gs.log(gs.wlog, get_bark(HACK_BARKS, "success"))
            gs.flash(f"TERMINALE VIOLATO!  Etica {gs.ethics:+d}", 100)
            gs.flash("ACCESSO GARANTITO  +10 TECH", 100)

            feedback = gs.complete_hacking()

            if feedback.get("bark_key"):
                gs.log(gs.wlog, get_bark(HACK_BARKS, feedback["bark_key"]))
            if feedback.get("flash_msg"):
                gs.flash(feedback["flash_msg"], feedback.get("flash_duration", 100))

        elif hack.is_locked_out:
            gs.log(gs.wlog, get_bark(HACK_BARKS, "system_locked"))
            gs.flash("LOCKOUT — SISTEMA BLOCCATO", 100)
            gs.screen = "explore"

    def update(self):
        self._anim += 0.06

    _CARD_X  = 24
    _CARD_W  = W - 48

    def draw(self, surf: Surface):
        gs   = GameManager.get_instance()
        fn   = self.fonts
        cx   = W // 2
        hack = gs.hack_sys
        p    = hack._current_puzzle

        surf.fill(BG)
        for sy in range(0, H, 4):
            v = int(3 + 2 * math.sin(self._anim + sy * 0.15))
            pygame.draw.line(surf, (0, v, v + 2), (0, sy), (W, sy))

        hdr_surf = pygame.Surface((W, 88), pygame.SRCALPHA)
        hdr_surf.fill((12, 14, 20, 220))
        surf.blit(hdr_surf, (0, 0))
        pygame.draw.line(surf, CYAN, (0, 88), (W, 88), 2)

        pygame.draw.rect(surf, CYAN, (self._CARD_X, 22, 4, 28), border_radius=2)
        txt(surf, "SISTEMA DI HACKING", self._CARD_X + 16, 24, CYAN, fn["bold"])

        badge_lbl = "solo Echo"
        bw = fn["sm"].size(badge_lbl)[0] + 14
        pygame.draw.rect(surf, (0, 50, 40), (self._CARD_X + 260, 26, bw, 20), border_radius=4)
        pygame.draw.rect(surf, CYAN,        (self._CARD_X + 260, 26, bw, 20), 1, border_radius=4)
        txt(surf, badge_lbl, self._CARD_X + 260 + bw // 2, 36, CYAN, fn["sm"], center=True)

        pt_str = gs.puzzle_type.upper()
        tw = fn["bold"].size(pt_str)[0]
        txt(surf, pt_str, W - self._CARD_X - tw, 28, YELLOW, fn["bold"])

        att_surf = pygame.Surface((W, 48), pygame.SRCALPHA)
        att_surf.fill((16, 20, 26, 200))
        surf.blit(att_surf, (0, 90))
        pygame.draw.line(surf, (40, 50, 60), (0, 138), (W, 138), 1)

        att   = hack.failed_attempts
        total = hack.MAX_ATTEMPTS
        is_locked = hack.is_locked_out

        txt(surf, "Tentativi:", self._CARD_X, 104, GREY, fn["sm"])
        spacing = 28 if total <= 6 else 20
        radius  = 8  if total <= 6 else 6
        dot_x0  = self._CARD_X + 110
        for i in range(total):
            col = RED if i < att else (40, 55, 65)
            brd = RED if i < att else (80, 100, 110)
            pygame.draw.circle(surf, col, (dot_x0 + i * spacing, 112), radius)
            pygame.draw.circle(surf, brd, (dot_x0 + i * spacing, 112), radius, 1)
        dot_end_x = dot_x0 + (total - 1) * spacing + radius + 8

        if is_locked:
            pygame.draw.rect(surf, (60, 0, 0),   (dot_end_x + 8, 100, 100, 22), border_radius=4)
            pygame.draw.rect(surf, RED,           (dot_end_x + 8, 100, 100, 22), 1, border_radius=4)
            txt(surf, "BLOCCATO", dot_end_x + 58, 111, RED, fn["sm"], center=True)
        else:
            txt(surf, f"{att}/{total}", dot_end_x + 8, 104, (150, 60, 60) if att > 0 else GREY, fn["sm"])

        state_str = str(p) if p else "—"
        sw = fn["md"].size(state_str)[0]
        txt(surf, state_str, W - self._CARD_X - sw, 104, WHITE, fn["md"])

        _LIST_TOP = 158
        iy = _LIST_TOP

        card_h   = H - _LIST_TOP - 80
        card_bg  = (14, 18, 24)
        card_brd = CYAN
        pygame.draw.rect(surf, card_bg,  (self._CARD_X, iy, self._CARD_W, card_h), border_radius=6)
        pygame.draw.rect(surf, (35, 45, 55), (self._CARD_X, iy, self._CARD_W, card_h), 1, border_radius=6)
        pygame.draw.rect(surf, CYAN, (self._CARD_X, iy, 4, card_h), border_radius=2)

        iy += 18

        if gs.puzzle_type in ("slot", "pipe"):
            txt(surf, "Instrada l'energia: SX  →  DX", cx, iy + fn["md"].get_height() // 2, GREY, fn["sm"], center=True)
            iy += 26
            if p and hasattr(p, "_reels"):
                tile    = 80
                grid_size = tile * 3
                gx = cx - grid_size // 2
                avail_h = card_h - 60
                gy = _LIST_TOP + 18 + (avail_h - grid_size) // 2
                pygame.draw.rect(surf, BG3, (gx, gy, grid_size, grid_size))
                pygame.draw.rect(surf, GREY, (gx, gy, grid_size, grid_size), 2)
                solved_color = GREEN if p.is_solved() else CYAN
                txt(surf, "IN ▶",  gx - 52, gy + grid_size // 2, CYAN,         fn["bold"], center=True)
                txt(surf, "▶ OUT", gx + grid_size + 52, gy + grid_size // 2, solved_color, fn["bold"], center=True)
                half = tile // 2
                arm  = tile // 2 - 2
                thick = 10
                for c in range(3):
                    for r in range(3):
                        if c == p._cursor_c and r == p._cursor_r:
                            pygame.draw.rect(surf, YELLOW, (gx + c * tile, gy + r * tile, tile, tile), 3)
                        pipe_char = p._reels[c][r]
                        conn = p.PIPES[pipe_char]
                        center_x = gx + c * tile + half
                        center_y = gy + r * tile + half
                        col = GREEN if p.is_solved() else CYAN
                        pygame.draw.rect(surf, col, (center_x - thick//2, center_y - thick//2, thick, thick))
                        if conn[0]: pygame.draw.rect(surf, col, (center_x - thick//2, center_y - arm, thick, arm))
                        if conn[1]: pygame.draw.rect(surf, col, (center_x, center_y - thick//2, arm, thick))
                        if conn[2]: pygame.draw.rect(surf, col, (center_x - thick//2, center_y, thick, arm))
                        if conn[3]: pygame.draw.rect(surf, col, (center_x - arm, center_y - thick//2, arm, thick))
                iy += grid_size + 16

        elif gs.puzzle_type == "radar":
            txt(surf, "Trova la cella con segnale al 100%.  Hai ping limitati.", cx, iy + fn["sm"].get_height() // 2, GREY, fn["sm"], center=True)
            iy += 28
            if p and hasattr(p, "_pos"):
                bar_w = min(520, self._CARD_W - 60)
                cell  = bar_w // p.SIZE
                bx2   = cx - bar_w // 2

                cell_h    = 48
                ping_h    = 40
                wave_h    = 60
                total_h   = cell_h + ping_h + wave_h
                avail_h   = card_h - (iy - _LIST_TOP) - 20
                iy        = iy + max(0, (avail_h - total_h) // 2)

                if p._last_ping is not None:
                    signal   = p._last_ping / 100.0
                    wave_cx  = bx2 + p._pos * cell + cell // 2
                    wave_cy  = iy + cell_h // 2
                    for ring in range(3):
                        phase    = (self._anim * 1.8 - ring * 1.2) % (2 * math.pi)
                        progress = (math.sin(phase) + 1) / 2
                        max_r    = int(20 + signal * 55)
                        r        = int(progress * max_r)
                        alpha    = int(220 * (1 - progress) * signal)
                        if r > 0 and alpha > 10:
                            ring_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                            ring_col  = (int(255 * signal), int(200 * signal), 0, alpha)
                            pygame.draw.circle(ring_surf, ring_col, (r + 2, r + 2), r, 2)
                            surf.blit(ring_surf, (wave_cx - r - 2, wave_cy - r - 2))

                for i in range(p.SIZE):
                    cx_cell = bx2 + i * cell + cell // 2
                    cy_cell = iy + cell_h // 2

                    if i == p._pos:
                        pulse = abs(math.sin(self._anim * 3.0))
                        glow_r = int(4 + pulse * 6)
                        glow_surf = pygame.Surface((cell - 2 + glow_r * 2, cell_h + glow_r * 2), pygame.SRCALPHA)
                        pygame.draw.rect(glow_surf, (0, 255, 80, int(60 * pulse)),
                                         (0, 0, cell - 2 + glow_r * 2, cell_h + glow_r * 2), border_radius=6)
                        surf.blit(glow_surf, (bx2 + i * cell - glow_r, iy - glow_r))

                    col = BG3
                    if i == p._pos:
                        col = GREEN
                    if p.is_solved() and i == p._target:
                        col = CYAN

                    pygame.draw.rect(surf, col,  (bx2 + i * cell, iy, cell - 2, cell_h), border_radius=4)
                    pygame.draw.rect(surf, GREY, (bx2 + i * cell, iy, cell - 2, cell_h), 1, border_radius=4)

                    label = "▲" if i == p._pos else ("T" if p.is_solved() and i == p._target else "")
                    if label:
                        s = fn["sm"].render(label, True, BG if col != BG3 else WHITE)
                        surf.blit(s, s.get_rect(center=(cx_cell, cy_cell)))

                iy += cell_h + 14

                if p._last_ping is not None:
                    sig = p._last_ping
                    sig_col = (
                        GREEN  if sig >= 70 else
                        YELLOW if sig >= 35 else
                        RED
                    )
                    txt(surf, f"Ultimo Ping: {sig}%", cx, iy + 8, sig_col, fn["md"], center=True)
                    iy += 26
                    bar_full = 260
                    bar_fill = int(bar_full * sig / 100)
                    bar_bx   = cx - bar_full // 2
                    bar_by   = iy
                    pygame.draw.rect(surf, BG3,    (bar_bx, bar_by, bar_full, 10), border_radius=5)
                    pygame.draw.rect(surf, sig_col,(bar_bx, bar_by, bar_fill, 10), border_radius=5)
                    pygame.draw.rect(surf, GREY,   (bar_bx, bar_by, bar_full, 10), 1, border_radius=5)
                    iy += 20
                else:
                    txt(surf, "[ nessun ping effettuato ]", cx, iy + 8, GREY, fn["sm"], center=True)
                    iy += 22

        elif gs.puzzle_type == "node":
            txt(surf, "Mastermind — Digita 4 cifre da 1 a 6.", cx, iy + fn["sm"].get_height() // 2, GREY, fn["sm"], center=True)
            iy += 24

            _leg_items = [("■", GREEN, " Posizione OK"), ("■", YELLOW, " Presente"), ("■", GREY, " Assente")]
            _leg_total_w = 310
            _lx = cx - _leg_total_w // 2
            for _sym, _sc, _label in _leg_items:
                txt(surf, _sym,   _lx,      iy, _sc,  fn["sm"])
                txt(surf, _label, _lx + 14, iy, GREY, fn["sm"])
                _lx += _leg_total_w // 3
            iy += 28

            CELL   = 52
            GAP    = 10
            COLS   = 4
            ROW_H  = CELL + GAP
            row_w  = COLS * CELL + (COLS - 1) * GAP
            row_x0 = cx - row_w // 2

            def _draw_node_row(y, digits, colors, is_current=False):
                _color_map = {"green": GREEN, "yellow": YELLOW, "grey": GREY}
                if is_current:
                    pygame.draw.rect(surf, (20, 28, 36),
                                     (row_x0 - 10, y - 6, row_w + 20, CELL + 12), border_radius=6)
                    pygame.draw.rect(surf, (40, 55, 70),
                                     (row_x0 - 10, y - 6, row_w + 20, CELL + 12), 1, border_radius=6)
                for i in range(COLS):
                    sx  = row_x0 + i * (CELL + GAP)
                    col = _color_map.get(colors[i], GREY)
                    if colors[i] == "green":
                        bg_col = (0, 50, 15)
                    elif colors[i] == "yellow":
                        bg_col = (50, 42, 0)
                    else:
                        bg_col = BG3
                    pygame.draw.rect(surf, bg_col, (sx, y, CELL, CELL), border_radius=6)
                    pygame.draw.rect(surf, col,    (sx, y, CELL, CELL), 2, border_radius=6)
                    if is_current and i == len(digits) and i < COLS:
                        cursor_on = int(self._anim * 4) % 2 == 0
                        if cursor_on:
                            pygame.draw.rect(surf, CYAN,
                                             (sx + CELL // 2 - 2, y + CELL - 10, 4, 8), border_radius=2)
                    ch2 = str(digits[i]) if i < len(digits) else ""
                    if ch2:
                        txt(surf, ch2, sx + CELL // 2, y + CELL // 2, col, fn["xl"], center=True)

            if p and hasattr(p, "_history"):
                history_shown = min(len(p._history), 4)
                total_rows    = history_shown + 1
                block_h       = total_rows * ROW_H + 30
                avail_h       = card_h - (iy - _LIST_TOP) - 20
                iy            = iy + max(0, (avail_h - block_h) // 2)

                for (digits, colors) in p._history[-4:]:
                    _draw_node_row(iy, digits, colors, is_current=False)
                    iy += ROW_H

                pygame.draw.line(surf, (50, 65, 80),
                                 (row_x0, iy - 2), (row_x0 + row_w, iy - 2), 1)

                entered    = p._entered if hasattr(p, "_entered") else []
                cur_colors = ["grey"] * COLS
                _draw_node_row(iy, entered, cur_colors, is_current=True)
                iy += ROW_H + 14

        log_y = _LIST_TOP + card_h - 82
        pygame.draw.line(surf, (40, 50, 60), (self._CARD_X + 8, log_y), (self._CARD_X + self._CARD_W - 8, log_y), 1)
        ly2 = log_y + 10
        if gs.puzzle_type == "node" and p and hasattr(p, "_history"):
            for digits, colors in p._history[-3:]:
                combo   = "".join(str(d) for d in digits)
                verdi   = sum(1 for c in colors if c == "green")
                gialli  = sum(1 for c in colors if c == "yellow")
                disp    = f"{combo}  →  {verdi}V  {gialli}G"
                ec      = GREEN if verdi == 4 else YELLOW
                txt(surf, disp, cx, ly2 + fn["sm"].get_height() // 2, ec, fn["sm"], center=True)
                ly2 += 20
        else:
            for entry in gs.hlog[-3:]:
                ec = (GREEN if any(x in entry for x in ["Jackpot", "agganciata", "corretto", "Accesso", "completato"])
                      else RED if ("errato" in entry or "fallit" in entry or "LOCK" in entry.upper())
                      else YELLOW)
                txt(surf, entry[:72], cx, ly2 + fn["sm"].get_height() // 2, ec, fn["sm"], center=True)
                ly2 += 20

        bar_h   = 60
        bar_y   = H - bar_h
        footer_surf = pygame.Surface((W, bar_h), pygame.SRCALPHA)
        footer_surf.fill((10, 12, 18, 235))
        surf.blit(footer_surf, (0, bar_y))
        pygame.draw.line(surf, CYAN, (0, bar_y), (W, bar_y), 2)

        ctrl_map = {
            "slot":  [("← ↑ ↓ →", "Muovi",  CYAN),  ("R",       "Ruota",   YELLOW), ("ESC", "Annulla", RED)],
            "pipe":  [("← ↑ ↓ →", "Muovi",  CYAN),  ("R",       "Ruota",   YELLOW), ("ESC", "Annulla", RED)],
            "radar": [("← →",     "Muovi",  CYAN),  ("SPAZIO",  "Ping",    YELLOW), ("ESC", "Annulla", RED)],
            "node":  [("1 – 6",   "Cifra",  CYAN),  ("INVIO",   "Conferma",YELLOW)],
        }
        buttons  = ctrl_map.get(gs.puzzle_type, [("ESC", "Annulla", RED)])
        margin   = 16
        gap      = 10
        n        = len(buttons)
        btn_w    = (W - margin * 2 - gap * (n - 1)) // n
        bx       = margin
        btn_top  = bar_y + 6
        btn_hi   = 44
        btn_mid  = btn_top + btn_hi // 2
        row1_y   = btn_mid - 9
        row2_y   = btn_mid + 9

        for key_str, label, col in buttons:
            btn_cx = bx + btn_w // 2
            pygame.draw.rect(surf, (col[0]//4, col[1]//4, col[2]//4),
                             (bx, btn_top, btn_w, btn_hi), border_radius=6)
            pygame.draw.rect(surf, col, (bx, btn_top, btn_w, btn_hi), 1, border_radius=6)
            pygame.draw.line(surf, col, (bx + 4, btn_top), (bx + btn_w - 4, btn_top), 2)
            txt(surf, key_str, btn_cx, row1_y, WHITE,           fn["sm"], center=True)
            txt(surf, label,   btn_cx, row2_y, (200, 205, 215), fn["sm"], center=True)
            bx += btn_w + gap