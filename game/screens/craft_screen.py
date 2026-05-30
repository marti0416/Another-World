"""
craft_screen.py — Screen del crafting (State GoF).

Visualizza le ricette disponibili, gli ingredienti richiesti e il risultato.
Permette di craftare o smontare oggetti tramite i Command GoF.
"""

from __future__ import annotations
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import (
    W, H, BG, BG2, BG3, CYAN, GREEN, RED, YELLOW,
    MAGENTA, GREY, WHITE, DARKGREY, PANEL, ORANGE, FPS,
)
from game.view.draw_utils import txt, panel, sep
from game.controller.game_manager import GameManager
from game.systems.crafting_system import RECIPES
from game.model.item import ItemType

_SECTION_ORDER = ["consumabili_curativi", "consumabili_offensivi", "armi"]

def _section_color(section: str) -> tuple:
    return {
        "consumabili_curativi":  GREEN,
        "consumabili_offensivi": ORANGE,
        "armi":                  CYAN,
    }.get(section, GREY)

def _section_label(section: str) -> str:
    return {
        "consumabili_curativi":  "CURA",
        "consumabili_offensivi": "OFF.",
        "armi":                  "ARMA",
    }.get(section, "???")

RECIPE_LIST = [
    ("medkit",           "Kit medico",        "Reagente×1 + Rottame×1",                 "tutti", "consumabili_curativi"),
    ("medkit_advanced",  "Kit med. avanzato", "Reagente×2 + Rottame×3",                 "tutti", "consumabili_curativi"),
    ("Antibiotics",      "Antibiotici",       "Reagente×2 + Alcol×1",                   "tutti", "consumabili_curativi"),
    ("Bandage",          "Bende Mediche",     "Stracci×2 + Alcol×1",                    "tutti", "consumabili_curativi"),

    ("gunpowder",        "Polvere da Sparo",    "Carbone×1 + Zolfo×1 + Nitrato×1",      "Rivet", "consumabili_offensivi"),
    ("molotov_cocktail", "Cocktail Molotov",    "Alcol×1 + Stracci×1",                  "tutti", "consumabili_offensivi"),
    ("molotov_fuel",     "Molotov (carburante)","Carburante×1 + Stracci×1",             "tutti", "consumabili_offensivi"),
    ("thermite",         "Termite",             "Polv. Ruggine×2 + Alluminio×2",        "Rivet", "consumabili_offensivi"),
    ("battle_explosive", "Esplosivo Combatt.",  "Polvere×2 + Reagente×1",               "tutti", "consumabili_offensivi"),
    ("c4",               "Carica C4",           "Polvere×3 + Reagente×2 + Alluminio×1", "Rivet", "consumabili_offensivi"),
    ("piranha_solution", "Piranha Solution",    "Reagente×2 + Zolfo×1",                 "Rivet", "consumabili_offensivi"),
    ("grenade",          "Granata Flash",       "Reag.×2 + Zolfo×1 + Polvere×3 + Allum.×1", "Rivet", "consumabili_offensivi"),

    ("improvised_club",          "Mazza di Fortuna",    "Junk×2 + Stracci×1",                                "tutti", "armi"),
    ("improvised_knife",         "Coltello Improvv.",   "Junk×1 + Rottame×1",                                "tutti", "armi"),
    ("craft_rusty_weapon",       "Pistola Arrugginita", "Junk×2 + Rottame×1",                                "tutti", "armi"),
    ("craft_light_weapon",       "Pistola Leggera",     "Junk×1 + Rottame×1",                                "tutti", "armi"),
    ("craft_heavy_rifle",        "Fucile d'Assalto",    "Rottame×4 + Polvere×2 + Comp.Bio-Tech×1",           "Rivet", "armi"),
    ("craft_acid_gun",           "Acid Gun",            "Reagente×3 + Rottame×3 + Alluminio×2",              "Rivet", "armi"),
    ("craft_antimatter_grenade", "Granata Antimateria", "Reagente×5 + Polvere×5 + Alluminio×3",              "Rivet", "armi"),
    ("craft_artillery",          "Desig. Artiglieria",  "Comp.Bio-Tech×3 + Kevlar×2 + Polvere×4 + Rottame×5", "Rivet", "armi"),
]

_CARD_X       = 24
_CARD_W       = W - 48
_ROW_H        = 52
_LIST_TOP     = 208
_LIST_BOTTOM  = H - 110
_MAX_VISIBLE  = (_LIST_BOTTOM - _LIST_TOP) // _ROW_H

_CI_TAG   = 14
_CI_NAME  = 100
_CI_MATS  = 420
_CI_WHO   = 780
_CI_BTN   = 880


def _can_craft(recipe_id: str, inventory) -> bool:
    recipe = RECIPES.get(recipe_id)
    if not recipe:
        return False
    for item_id, qty in recipe["ingredients"].items():
        it = inventory.get_item(item_id)
        if not it or it.quantity < qty:
            return False
    return True


class CraftScreen(Screen):
    def __init__(self, fonts):
        self.fonts = fonts
        self._scroll_offset: int = 0

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont(
            "segoeuisymbol, applesymbols, dejavusans, arial", 18)


    def update(self):
        return super().update()

    def _get_craftable_recipes(self) -> list[tuple]:
        gs = GameManager.get_instance()
        available_dict = gs.craft_sys.get_available_recipes(gs.cft_target)
        inv = gs.Rivet.inventory if gs.cft_target == "Rivet" else gs.Echo.inventory
        craftable = [
            r for r in RECIPE_LIST
            if r[0] in available_dict and _can_craft(r[0], inv)
        ]
        craftable.sort(key=lambda r: _SECTION_ORDER.index(r[4])
                       if r[4] in _SECTION_ORDER else 99)
        return craftable


    def handle_event(self, event):
        gs = GameManager.get_instance()
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        craftable = self._get_craftable_recipes()
        max_idx = max(1, len(craftable))

        if k in (pygame.K_UP, pygame.K_w):
            gs.cft_cursor = (gs.cft_cursor - 1) % max_idx
            self._ensure_cursor_visible(gs.cft_cursor, max_idx)
        elif k in (pygame.K_DOWN, pygame.K_s):
            gs.cft_cursor = (gs.cft_cursor + 1) % max_idx
            self._ensure_cursor_visible(gs.cft_cursor, max_idx)
        elif k == pygame.K_TAB:
            gs.cft_target = "Echo" if gs.cft_target == "Rivet" else "Rivet"
            gs.cft_cursor = 0
            self._scroll_offset = 0
            gs.craft_msg = ""
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self._craft(craftable)
        elif k in (pygame.K_c, pygame.K_ESCAPE):
            gs.screen = "explore"

    def _ensure_cursor_visible(self, cursor: int, total: int):
        if cursor < self._scroll_offset:
            self._scroll_offset = cursor
        elif cursor >= self._scroll_offset + _MAX_VISIBLE:
            self._scroll_offset = cursor - _MAX_VISIBLE + 1
        self._scroll_offset = max(0, min(self._scroll_offset,
                                         max(0, total - _MAX_VISIBLE)))


    def _craft(self, craftable: list[tuple]):
        gs = GameManager.get_instance()
        if not craftable:
            gs.craft_msg = "Nessun oggetto craftabile al momento."
            gs.craft_ok  = False
            return

        rid = craftable[gs.cft_cursor][0]
        inv = gs.Rivet.inventory if gs.cft_target == "Rivet" else gs.Echo.inventory
        char_obj = gs.Rivet if gs.cft_target == "Rivet" else gs.Echo
        res = gs.craft_sys.craft(rid, inv, gs.cft_target)

        gs.craft_msg = res.get("message", "Errore sconosciuto")
        gs.craft_ok  = res.get("success", False)

        if res.get("success"):
            if char_obj.name == "Rivet":
                char_obj.stats.gain_tech_points(10)
                gs.craft_msg += "  +10 TECH"

        if res.get("success") and "weapon" in res:
            weapon = res["weapon"]
            char_obj.weapons.append(weapon)
            ok, equip_msg = char_obj.equip_weapon(weapon)
            gs.craft_msg += "   Arma Equipaggiata!" if ok else f" ({equip_msg})"

        new_craftable = self._get_craftable_recipes()
        if new_craftable:
            gs.cft_cursor = min(gs.cft_cursor, len(new_craftable) - 1)
        else:
            gs.cft_cursor = 0
        self._scroll_offset = max(0, min(self._scroll_offset,
                                          max(0, len(new_craftable) - _MAX_VISIBLE)))


    def _draw_header(self, surf, gs, fn):
        """Titolo + selettore personaggio + materiali (stile card explore)."""
        cx = W // 2

        hdr_surf = pygame.Surface((W, 88), pygame.SRCALPHA)
        hdr_surf.fill((12, 14, 20, 220))
        surf.blit(hdr_surf, (0, 0))
        pygame.draw.line(surf, CYAN, (0, 88), (W, 88), 2)

        pygame.draw.rect(surf, CYAN, (24, 22, 4, 28), border_radius=2)
        txt(surf, "OFFICINA DI CRAFTING", 36, 24, CYAN, fn["bold"])

        craftable = self._get_craftable_recipes()
        count_str = f"{len(craftable)} craftabil{'e' if len(craftable)==1 else 'i'}"
        tw = fn["sm"].size(count_str)[0]
        txt(surf, count_str, W - 24 - tw, 28, GREEN, fn["sm"])

        for i, (label, char_name) in enumerate([("Rivet", "Rivet"), ("Echo", "Echo")]):
            is_active = (gs.cft_target == char_name)
            bcol = (CYAN if char_name == "Rivet" else MAGENTA) if is_active else DARKGREY
            bx = cx - 110 + i * 120
            by = 46
            bw, bh = 100, 30

            bg_col = (10, 40, 55) if (is_active and char_name == "Rivet") else \
                     (35, 10, 45) if (is_active and char_name == "Echo") else (20, 22, 28)
            pygame.draw.rect(surf, bg_col, (bx, by, bw, bh), border_radius=6)
            pygame.draw.line(surf, bcol, (bx + 4, by), (bx + bw - 4, by), 2)
            if is_active:
                pygame.draw.rect(surf, bcol, (bx, by, bw, bh), 1, border_radius=6)
            txt(surf, label, bx + bw // 2, by + bh // 2 - 1, bcol, fn["bold"], center=True)



    def _draw_materials_bar(self, surf, gs, fn):
        """Barra materiali stile card explore (sotto l'header)."""
        char_attivo = gs.Rivet if gs.cft_target == "Rivet" else gs.Echo
        mats = char_attivo.inventory.get_by_type(ItemType.MATERIAL)

        bar_surf = pygame.Surface((W, 48), pygame.SRCALPHA)
        bar_surf.fill((16, 20, 26, 200))
        surf.blit(bar_surf, (0, 90))
        pygame.draw.line(surf, (40, 50, 60), (0, 138), (W, 138), 1)

        txt(surf, "Zaino:", 28, 104, GREY, fn["sm"])

        if mats:
            x = 88
            for m in mats:
                col = YELLOW
                label = f"{m.name} x{m.quantity}"
                lw = fn["sm"].size(label)[0]
                pygame.draw.circle(surf, (50, 60, 70), (x - 6, 112), 2)
                txt(surf, label, x, 104, col, fn["sm"])
                x += lw + 20
                if x > W - 100:
                    break
        else:
            txt(surf, "(nessun materiale)", 88, 104, DARKGREY, fn["sm"])

    def _draw_column_headers(self, surf, fn):
        """Header colonne integrato nella barra materiali."""
        row_y = 146
        pygame.draw.line(surf, (40, 50, 60), (_CARD_X, row_y + 22), (_CARD_X + _CARD_W, row_y + 22), 1)

        headers = [
            ("Tipo",        _CARD_X + _CI_TAG),
            ("Ricetta",     _CARD_X + _CI_NAME),
            ("Ingredienti", _CARD_X + _CI_MATS),
            ("Chi",         _CARD_X + _CI_WHO),
        ]
        for label, x in headers:
            txt(surf, label, x, row_y, (80, 95, 110), fn["sm"])

    def _draw_recipe_rows(self, surf, gs, fn):
        """Lista ricette craftabili con card stile explore."""
        craftable = self._get_craftable_recipes()
        cx = W // 2

        if not craftable:
            ey = _LIST_TOP + 40
            card_surf = pygame.Surface((_CARD_W, 100), pygame.SRCALPHA)
            card_surf.fill((20, 25, 20, 210))
            surf.blit(card_surf, (_CARD_X, ey))
            pygame.draw.rect(surf, (50, 70, 50), (_CARD_X, ey, _CARD_W, 100), 1, border_radius=6)

            txt(surf, "Nessun oggetto craftabile al momento",
                cx, ey + 22, (160, 170, 160), fn["md"], center=True)
            txt(surf, f"Controlla l'inventario di {gs.cft_target}: mancano ingredienti",
                cx, ey + 48, GREY, fn["sm"], center=True)
            txt(surf, "oppure cambia personaggio con il tasto TAB",
                cx, ey + 68, GREY, fn["sm"], center=True)
            return

        total   = len(craftable)
        end_idx = min(self._scroll_offset + _MAX_VISIBLE, total)
        row_y   = _LIST_TOP

        for real_idx in range(self._scroll_offset, end_idx):
            rid, name, mats_str, who, section = craftable[real_idx]
            sel = (real_idx == gs.cft_cursor)
            scol = _section_color(section)

            card_bg = (18, 24, 30) if not sel else (12, 35, 48)
            card_border = scol if sel else (35, 45, 55)
            pygame.draw.rect(surf, card_bg,
                             (_CARD_X, row_y, _CARD_W, _ROW_H - 4), border_radius=6)
            pygame.draw.rect(surf, card_border,
                             (_CARD_X, row_y, _CARD_W, _ROW_H - 4), 1, border_radius=6)

            if sel:
                pygame.draw.rect(surf, scol,
                                 (_CARD_X, row_y, 4, _ROW_H - 4), border_radius=2)
            else:
                pygame.draw.rect(surf, (scol[0]//3, scol[1]//3, scol[2]//3),
                                 (_CARD_X, row_y, 4, _ROW_H - 4), border_radius=2)

            cx_card = _CARD_X + _CI_TAG
            cy_mid  = row_y + (_ROW_H - 4) // 2 - 10

            slabel = _section_label(section)
            badge_w = fn["sm"].size(slabel)[0] + 10
            badge_bg = (scol[0]//4, scol[1]//4, scol[2]//4)
            pygame.draw.rect(surf, badge_bg,
                             (cx_card, cy_mid, badge_w, 20), border_radius=4)
            pygame.draw.rect(surf, scol,
                             (cx_card, cy_mid, badge_w, 20), 1, border_radius=4)
            txt(surf, slabel, cx_card + badge_w // 2, cy_mid + 10,
                scol, fn["sm"], center=True)

            name_col = WHITE if sel else (190, 195, 205)
            txt(surf, name, _CARD_X + _CI_NAME, cy_mid, name_col, fn["md"])

            mats_max_chars = (_CI_WHO - _CI_MATS - 10) // 7
            mats_display = mats_str if len(mats_str) <= mats_max_chars else mats_str[:mats_max_chars - 1] + "…"
            txt(surf, mats_display, _CARD_X + _CI_MATS, cy_mid, (130, 170, 130), fn["sm"])

            who_col = GREEN if who == "tutti" else ORANGE
            txt(surf, who, _CARD_X + _CI_WHO, cy_mid, who_col, fn["bold"])

            btn_x = _CARD_X + _CI_BTN
            btn_w = _CARD_W - _CI_BTN - 10
            btn_y = row_y + 8
            btn_h = _ROW_H - 20
            if sel:
                pygame.draw.rect(surf, YELLOW, (btn_x, btn_y, btn_w, btn_h), border_radius=5)
                pygame.draw.line(surf, WHITE,
                                 (btn_x + 4, btn_y), (btn_x + btn_w - 4, btn_y), 1)
                txt(surf, "CRAFTA", btn_x + btn_w // 2, btn_y + btn_h // 2,
                    BG, fn["bold"], center=True)
            else:
                pygame.draw.rect(surf, (28, 32, 38), (btn_x, btn_y, btn_w, btn_h), border_radius=5)
                pygame.draw.rect(surf, (55, 65, 75), (btn_x, btn_y, btn_w, btn_h), 1, border_radius=5)
                txt(surf, "Crafta", btn_x + btn_w // 2, btn_y + btn_h // 2,
                    GREY, fn["sm"], center=True)

            row_y += _ROW_H

        if self._scroll_offset > 0:
            pygame.draw.polygon(surf, GREY, [
                (cx, _LIST_TOP - 14),
                (cx - 8, _LIST_TOP - 4),
                (cx + 8, _LIST_TOP - 4),
            ])
        if end_idx < total:
            remaining = total - end_idx
            pygame.draw.polygon(surf, GREY, [
                (cx, row_y + 14),
                (cx - 8, row_y + 4),
                (cx + 8, row_y + 4),
            ])
            txt(surf, f"altri {remaining}", cx + 16, row_y + 6, GREY, fn["sm"])

    def _draw_result_message(self, surf, gs, fn):
        """Messaggio risultato craft — card stile explore."""
        if not (hasattr(gs, "craft_msg") and gs.craft_msg):
            return
        cx = W // 2
        mc = GREEN if getattr(gs, "craft_ok", False) else RED

        msg_w = fn["bold"].size(gs.craft_msg)[0] + 32
        msg_w = min(msg_w, _CARD_W)
        msg_x = cx - msg_w // 2
        msg_y = H - 100

        msg_bg = (mc[0]//6, mc[1]//6, mc[2]//6)
        pygame.draw.rect(surf, msg_bg, (msg_x, msg_y, msg_w, 30), border_radius=6)
        pygame.draw.rect(surf, mc, (msg_x, msg_y, msg_w, 30), 1, border_radius=6)
        pygame.draw.line(surf, mc, (msg_x + 4, msg_y), (msg_x + msg_w - 4, msg_y), 2)

        ind_col = GREEN if getattr(gs, "craft_ok", False) else RED
        pygame.draw.rect(surf, ind_col, (msg_x + 8, msg_y + 7, 6, 16), border_radius=2)

        msg_display = gs.craft_msg
        max_chars = (msg_w - 30) // 7
        if len(msg_display) > max_chars:
            msg_display = msg_display[:max_chars - 1] + "…"
        txt(surf, msg_display, cx, msg_y + 15, mc, fn["bold"], center=True)

    def _draw_footer(self, surf, fn):
        """Footer barra comandi — stile action bar di explore."""
        bar_h = 60
        bar_y = H - bar_h

        footer_surf = pygame.Surface((W, bar_h), pygame.SRCALPHA)
        footer_surf.fill((10, 12, 18, 235))
        surf.blit(footer_surf, (0, bar_y))
        pygame.draw.line(surf, CYAN, (0, bar_y), (W, bar_y), 2)

        buttons = [
            ("[W/S]/[⇅]",   "Naviga",      CYAN),
            ("[INVIO]",   "Crafta",      YELLOW),
            ("[TAB]",     "Cambia PG",   MAGENTA),
            ("[C]/[ESC]", "Torna",       RED),
        ]
        margin   = 16
        gap      = 10
        n        = len(buttons)
        btn_w    = (W - margin * 2 - gap * (n - 1)) // n
        bx       = margin

        btn_top        = bar_y + 6
        btn_h_inner    = 44
        btn_mid_y      = btn_top + btn_h_inner // 2
        row1_y         = btn_mid_y - 9
        row2_y         = btn_mid_y + 9

        for key_str, label, col in buttons:
            btn_cx = bx + btn_w // 2
            pygame.draw.rect(surf, (col[0]//4, col[1]//4, col[2]//4),
                             (bx, btn_top, btn_w, btn_h_inner), border_radius=6)
            pygame.draw.rect(surf, col, (bx, btn_top, btn_w, btn_h_inner), 1, border_radius=6)
            pygame.draw.line(surf, col, (bx + 4, btn_top), (bx + btn_w - 4, btn_top), 2)
            txt(surf, key_str, btn_cx, row1_y, WHITE,           fn["sm"], center=True)
            txt(surf, label,   btn_cx, row2_y, (200, 205, 215), fn["sm"], center=True)
            bx += btn_w + gap


    def draw(self, surf: Surface):
        gs  = GameManager.get_instance()
        fn  = self.fonts

        surf.fill(BG)

        self._draw_header(surf, gs, fn)
        self._draw_materials_bar(surf, gs, fn)
        self._draw_column_headers(surf, fn)
        self._draw_recipe_rows(surf, gs, fn)
        self._draw_result_message(surf, gs, fn)
        self._draw_footer(surf, fn)