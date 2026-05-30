"""
quest_screen.py — Screen del diario delle quest (State GoF).

Visualizza le quest attive, completate e fallite con i rispettivi obiettivi
e premi. Permette di tracciare la quest selezionata sulla mappa.
"""

from __future__ import annotations
import math
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import (
    W, H, BG, BG2, BG3,
    CYAN, YELLOW, GREEN, RED, GREY, WHITE, DARKGREY, ORANGE
)
from game.view.draw_utils import txt, sep
from game.controller.game_manager import GameManager


_CARD_X   = 24
_CARD_W   = W - 48
_HDR_H    = 88
_ATT_H    = 48
_FOOTER_H = 60
_LIST_TOP = _HDR_H + _ATT_H + 10
_LIST_X   = _CARD_X + 8
_LIST_W   = 280
_DETAIL_X = _CARD_X + _LIST_W + 32
_DETAIL_W = _CARD_W - _LIST_W - 40

_MAIN_QUESTS = {"Q01_grattacielo", "Q02_centrale", "Q03_fabbrica"}


def _wrap(text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = cur + w + " "
        if font.size(test)[0] > max_w and cur:
            lines.append(cur.rstrip())
            cur = w + " "
        else:
            cur = test
    if cur:
        lines.append(cur.rstrip())
    return lines


class QuestScreen(Screen):
    def __init__(self, fonts):
        self.fonts  = fonts
        self.cursor = 0
        self.tab    = "active"
        self._anim  = 0.0
        self._scroll_offset = 0
        self._MAX_VISIBLE   = 12

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k  = event.key
        gs = GameManager.get_instance()
        quests = self._get_quests(gs)

        if k in (pygame.K_ESCAPE, pygame.K_q, pygame.K_m, pygame.K_p):
            gs.screen = "explore"

        elif k in (pygame.K_UP, pygame.K_w):
            if quests:
                self.cursor = (self.cursor - 1) % len(quests)
                self._clamp_scroll()

        elif k in (pygame.K_DOWN, pygame.K_s):
            if quests:
                self.cursor = (self.cursor + 1) % len(quests)
                self._clamp_scroll()

        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            self.tab    = "completed" if self.tab == "active" else "active"
            self.cursor = 0
            self._scroll_offset = 0

    def _clamp_scroll(self):
        if self.cursor < self._scroll_offset:
            self._scroll_offset = self.cursor
        elif self.cursor >= self._scroll_offset + self._MAX_VISIBLE:
            self._scroll_offset = self.cursor - self._MAX_VISIBLE + 1

    def _get_quests(self, gs):
        if not gs.quest_sys:
            return []
        if self.tab == "active":
            return gs.quest_sys.get_active_quests()
        return [q for q in gs.quest_sys._states.values() if q.status.value == "completed"]

    def update(self):
        self._anim += 0.05

    def draw(self, surf: Surface):
        gs     = GameManager.get_instance()
        fn     = self.fonts
        cx     = W // 2
        quests = self._get_quests(gs)

        surf.fill(BG)
        for sy in range(0, H, 4):
            v = int(3 + 2 * math.sin(self._anim + sy * 0.15))
            pygame.draw.line(surf, (0, v, v + 2), (0, sy), (W, sy))

        hdr = pygame.Surface((W, _HDR_H), pygame.SRCALPHA)
        hdr.fill((12, 14, 20, 220))
        surf.blit(hdr, (0, 0))
        pygame.draw.line(surf, CYAN, (0, _HDR_H), (W, _HDR_H), 2)

        pygame.draw.rect(surf, CYAN, (_CARD_X, 22, 4, 28), border_radius=2)
        txt(surf, "DIARIO MISSIONI", _CARD_X + 16, 24, CYAN, fn["bold"])

        active_n = len(gs.quest_sys.get_active_quests()) if gs.quest_sys else 0
        badge    = f"{active_n} attive"
        bw       = fn["sm"].size(badge)[0] + 14
        pygame.draw.rect(surf, (0, 50, 40), (_CARD_X + 240, 26, bw, 20), border_radius=4)
        pygame.draw.rect(surf, CYAN,        (_CARD_X + 240, 26, bw, 20), 1, border_radius=4)
        txt(surf, badge, _CARD_X + 240 + bw // 2, 36, CYAN, fn["sm"], center=True)

        tab_str = "ATTIVE" if self.tab == "active" else "COMPLETATE"
        tw = fn["bold"].size(tab_str)[0]
        txt(surf, tab_str, W - _CARD_X - tw, 28, YELLOW, fn["bold"])

        tab_surf = pygame.Surface((W, _ATT_H), pygame.SRCALPHA)
        tab_surf.fill((16, 20, 26, 200))
        surf.blit(tab_surf, (0, _HDR_H))
        pygame.draw.line(surf, (40, 50, 60), (0, _HDR_H + _ATT_H), (W, _HDR_H + _ATT_H), 1)

        tab_items = [("MISSIONI ATTIVE", "active"), ("COMPLETATE", "completed")]
        tbx = _CARD_X
        for label, key in tab_items:
            is_sel = self.tab == key
            col    = YELLOW if is_sel else GREY
            tw2    = fn["sm"].size(label)[0] + 24
            if is_sel:
                pygame.draw.rect(surf, (30, 40, 20),
                                 (tbx, _HDR_H + 6, tw2, _ATT_H - 12), border_radius=4)
                pygame.draw.rect(surf, YELLOW,
                                 (tbx, _HDR_H + 6, tw2, _ATT_H - 12), 1, border_radius=4)
                pygame.draw.line(surf, YELLOW,
                                 (tbx + 4, _HDR_H + 6),
                                 (tbx + tw2 - 4, _HDR_H + 6), 2)
            txt(surf, label, tbx + tw2 // 2, _HDR_H + _ATT_H // 2, col, fn["sm"], center=True)
            tbx += tw2 + 10

        card_h = H - _LIST_TOP - _FOOTER_H - 8
        card_bg = (14, 18, 24)
        pygame.draw.rect(surf, card_bg,      (_CARD_X, _LIST_TOP, _CARD_W, card_h), border_radius=6)
        pygame.draw.rect(surf, (35, 45, 55), (_CARD_X, _LIST_TOP, _CARD_W, card_h), 1, border_radius=6)
        pygame.draw.rect(surf, CYAN,         (_CARD_X, _LIST_TOP, 4, card_h), border_radius=2)

        if not quests:
            txt(surf, "Nessuna missione in questa categoria.", cx, _LIST_TOP + card_h // 2,
                GREY, fn["md"], center=True)
        else:
            self._draw_list(surf, fn, quests, card_h)
            sep_x = _CARD_X + _LIST_W + 16
            pygame.draw.line(surf, (40, 55, 65),
                             (sep_x, _LIST_TOP + 10), (sep_x, _LIST_TOP + card_h - 10))
            self._draw_detail(surf, fn, quests, card_h)

        bar_y = H - _FOOTER_H
        foot  = pygame.Surface((W, _FOOTER_H), pygame.SRCALPHA)
        foot.fill((10, 12, 18, 235))
        surf.blit(foot, (0, bar_y))
        pygame.draw.line(surf, CYAN, (0, bar_y), (W, bar_y), 2)

        buttons = [
            ("← →", "Cambia scheda", CYAN),
            ("↑ ↓",        "Scorri",        CYAN),
            ("Q / ESC",    "Chiudi",         RED),
        ]
        margin  = 16
        gap     = 10
        btn_w   = (W - margin * 2 - gap * (len(buttons) - 1)) // len(buttons)
        bx      = margin
        btn_top = bar_y + 6
        btn_hi  = 44
        btn_mid = btn_top + btn_hi // 2
        row1_y  = btn_mid - 9
        row2_y  = btn_mid + 9

        for key_str, label, col in buttons:
            btn_cx = bx + btn_w // 2
            pygame.draw.rect(surf, (col[0]//4, col[1]//4, col[2]//4),
                             (bx, btn_top, btn_w, btn_hi), border_radius=6)
            pygame.draw.rect(surf, col, (bx, btn_top, btn_w, btn_hi), 1, border_radius=6)
            pygame.draw.line(surf, col, (bx + 4, btn_top), (bx + btn_w - 4, btn_top), 2)
            txt(surf, key_str, btn_cx, row1_y, WHITE,           fn["sm"], center=True)
            txt(surf, label,   btn_cx, row2_y, (200, 205, 215), fn["sm"], center=True)
            bx += btn_w + gap

    def _draw_list(self, surf, fn, quests, card_h):
        row_h     = 30
        pad_top   = 12
        visible   = min(self._MAX_VISIBLE, card_h // row_h)

        for slot in range(visible):
            idx = self._scroll_offset + slot
            if idx >= len(quests):
                break
            q       = quests[idx]
            y       = _LIST_TOP + pad_top + slot * row_h
            is_sel  = idx == self.cursor
            is_main = q.quest_id in _MAIN_QUESTS

            if is_sel:
                pulse = abs(math.sin(self._anim * 3.0))
                bg_col = (int(0 + 20 * pulse), int(35 + 20 * pulse), int(20 + 15 * pulse))
                pygame.draw.rect(surf, bg_col,
                                 (_LIST_X, y - 3, _LIST_W - 4, row_h - 2), border_radius=4)
                pygame.draw.rect(surf, GREEN,
                                 (_LIST_X, y - 3, _LIST_W - 4, row_h - 2), 1, border_radius=4)

            dot_col = YELLOW if is_main else GREY
            pygame.draw.circle(surf, dot_col, (_LIST_X + 10, y + row_h // 2 - 2), 4)

            col   = GREEN if is_sel else (WHITE if is_main else GREY)
            title = q.title[:28]
            txt(surf, title, _LIST_X + 22, y + 4, col, fn["sm"])

        if self._scroll_offset > 0:
            txt(surf, "▲", _LIST_X + _LIST_W // 2, _LIST_TOP + 2, GREY, fn["sm"], center=True)
        if self._scroll_offset + visible < len(quests):
            txt(surf, "▼", _LIST_X + _LIST_W // 2, _LIST_TOP + card_h - 16, GREY, fn["sm"], center=True)

    def _draw_detail(self, surf, fn, quests, card_h):
        if self.cursor >= len(quests):
            return
        q  = quests[self.cursor]
        gs = GameManager.get_instance()
        dx = _DETAIL_X
        dy = _LIST_TOP + 14

        is_main = q.quest_id in _MAIN_QUESTS

        txt(surf, q.title, dx, dy, YELLOW, fn["bold"])
        dy += 26

        tipo    = "MISSIONE PRINCIPALE" if is_main else "MISSIONE SECONDARIA"
        tipo_col = YELLOW if is_main else ORANGE
        bw = fn["sm"].size(tipo)[0] + 12
        pygame.draw.rect(surf, (tipo_col[0]//5, tipo_col[1]//5, tipo_col[2]//5),
                         (dx, dy, bw, 18), border_radius=3)
        pygame.draw.rect(surf, tipo_col, (dx, dy, bw, 18), 1, border_radius=3)
        txt(surf, tipo, dx + bw // 2, dy + 9, tipo_col, fn["sm"], center=True)
        dy += 28

        pygame.draw.line(surf, (40, 55, 65), (dx, dy), (dx + _DETAIL_W - 8, dy))
        dy += 10

        quest_def = gs.quest_sys._defs.get(q.quest_id)
        desc      = quest_def.description if quest_def else "Nessuna descrizione."
        for line in _wrap(desc, fn["sm"], _DETAIL_W - 8):
            txt(surf, line, dx, dy, (180, 185, 195), fn["sm"])
            dy += 20
        dy += 8

        pygame.draw.line(surf, (40, 55, 65), (dx, dy), (dx + _DETAIL_W - 8, dy))
        dy += 8
        txt(surf, "OBIETTIVI", dx, dy, CYAN, fn["sm"])
        dy += 22

        for obj in q.objectives:
            if getattr(obj, "hidden", False):
                continue

            done    = obj.completed
            box_col = GREEN if done else (60, 70, 80)
            txt_col = GREEN if done else GREY

            pygame.draw.rect(surf, box_col, (dx, dy + 1, 14, 14), border_radius=2)
            if done:
                pygame.draw.lines(surf, BG2, False,
                                  [(dx + 3, dy + 8), (dx + 6, dy + 11), (dx + 11, dy + 4)], 2)
            else:
                pygame.draw.rect(surf, (80, 95, 110), (dx, dy + 1, 14, 14), 1, border_radius=2)

            progress = f"  ({obj.progress}/{obj.required})" if obj.required > 1 and not done else ""
            label    = f"{obj.description}{progress}"
            txt(surf, label, dx + 20, dy, txt_col, fn["sm"])
            dy += 22

            if dy > _LIST_TOP + card_h - 20:
                break

            if not done:
                break