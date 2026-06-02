"""
save_ui.py — UI per il menu di salvataggio/caricamento e ISystem associato.

Struttura
---------
- ``SaveSlotInfo``  : dataclass con metadati di uno slot di salvataggio.
- ``SaveSlotUI``    : rendering pygame di un singolo slot.
- ``SaveMenuUI``    : pannello completo con navigazione tra gli slot.
- ``SaveMenuSystem``: ISystem che gestisce apertura/chiusura e input del menu.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType

if TYPE_CHECKING:
    from game.controller.game_manager import GameManager, SaveManager

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False



@dataclass
class SaveSlotInfo:
    """Metadati di uno slot di salvataggio per la visualizzazione nell'UI.

        Attributes:
            slot_id:   Numero dello slot (1-based).
            is_empty:  ``True`` se lo slot non contiene dati.
            timestamp: Data e ora dell'ultimo salvataggio.
            location:  Nome del distretto al momento del salvataggio.
    """
    slot_id:    int
    is_empty:   bool = True
    timestamp:  datetime | None = None
    location:   str = ""

    @property
    def display_title(self) -> str:
        return f"SLOT {self.slot_id}"

    @property
    def display_info(self) -> str:
        if self.is_empty:
            return "Nessun dato salvato"
        ts = self.timestamp.strftime("%d/%m/%Y - %H:%M") if self.timestamp else "—"
        return f"{self.location or 'Settore Sconosciuto'}  |  {ts}"



class SaveSlotUI:
    """Renderer di un singolo slot di salvataggio nell'UI pygame.

        Gestisce il rendering sia dello slot selezionato (bordo colorato e cursore)
        che di quello non selezionato (bordo grigio, icona floppy).
    """
    SLOT_W:  int = 420
    SLOT_H:  int = 85
    GAP:     int = 15

    def __init__(self, info: SaveSlotInfo) -> None:
        self.info = info

    def render(self, surface, font_big, font_small, simboli_font,
               x: int, y: int, selected: bool, main_col: tuple) -> pygame.Rect | None:

        if not _PYGAME_AVAILABLE:
            return None

        rect = pygame.Rect(x, y, self.SLOT_W, self.SLOT_H)

        if selected:
            bg_col = (main_col[0]//5, main_col[1]//5, main_col[2]//5, 230)
            border_col = main_col
            txt_title = (255, 255, 255)
            txt_info = main_col
        else:
            bg_col = (20, 25, 32, 200) if not self.info.is_empty else (10, 12, 18, 180)
            border_col = (80, 90, 100) if not self.info.is_empty else (40, 50, 60)
            txt_title = (180, 180, 180) if not self.info.is_empty else (100, 100, 100)
            txt_info = (120, 130, 140) if not self.info.is_empty else (80, 80, 80)

        slot_surf = pygame.Surface((self.SLOT_W, self.SLOT_H), pygame.SRCALPHA)
        slot_surf.fill(bg_col)
        surface.blit(slot_surf, (x, y))
        pygame.draw.rect(surface, border_col, rect, 2, border_radius=6)

        if selected:
            ico_cursor = simboli_font.render("➤", True, main_col)
            surface.blit(ico_cursor, (x + 15, y + 30))

        ico_str = "🖿" if self.info.is_empty else "💾"
        ico_floppy = simboli_font.render(ico_str, True, txt_info)
        surface.blit(ico_floppy, (x + 40 if selected else x + 20, y + 16))

        offset_x = 70 if selected else 50

        title_surf = font_big.render(self.info.display_title, True, txt_title)
        surface.blit(title_surf, (x + offset_x, y + 15))

        info_surf = font_small.render(self.info.display_info, True, txt_info)
        surface.blit(info_surf, (x + offset_x, y + 45))

        return rect



class SaveMenuUI:
    """Pannello completo di selezione slot con navigazione su/giù.

        Espone ``navigate(delta)`` per muoversi tra gli slot e
        ``render(surface, ...)`` per disegnare il pannello completo.
    """
    NUM_SLOTS = 3
    MENU_W:  int = 500
    MENU_H:  int = 450

    def __init__(self, slot_infos: list[SaveSlotInfo]) -> None:
        self.slot_uis  = [SaveSlotUI(info) for info in slot_infos]
        self.selected  = 0
        self._message  = ""
        self._msg_timer: int = 0

        if _PYGAME_AVAILABLE:
            pygame.font.init()
            self.simboli_font = pygame.font.SysFont("segoeuisymbol, applesymbols, dejavusans, arial", 20)

    @property
    def selected_slot_id(self) -> int:
        return self.selected + 1

    def navigate(self, direction: int) -> None:
        self.selected = (self.selected + direction) % self.NUM_SLOTS

    def set_message(self, msg: str, duration: int = 150) -> None:
        self._message   = msg
        self._msg_timer = duration

    def render(self, surface, screen_w: int, screen_h: int,
               font_title, font_big, font_small, font_hint, current_mode: str) -> None:
        if not _PYGAME_AVAILABLE: return

        main_col = (0, 200, 100) if current_mode == "save" else (0, 229, 255)
        title_str = "SALVATAGGIO DATI" if current_mode == "save" else "CARICAMENTO DATI"

        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        mx = (screen_w - self.MENU_W) // 2
        my = (screen_h - self.MENU_H) // 2
        panel_rect = pygame.Rect(mx, my, self.MENU_W, self.MENU_H)

        bg_surf = pygame.Surface((self.MENU_W, self.MENU_H), pygame.SRCALPHA)
        bg_surf.fill((15, 18, 25, 230))
        surface.blit(bg_surf, (mx, my))
        pygame.draw.rect(surface, main_col, panel_rect, 2, border_radius=8)

        ico_info = self.simboli_font.render("❖", True, main_col)
        surface.blit(ico_info, (mx + 20, my + 18))

        title_surf = font_title.render(title_str, True, main_col)
        surface.blit(title_surf, (mx + 45, my + 20))

        pygame.draw.line(surface, (40, 50, 60), (mx + 20, my + 50), (mx + self.MENU_W - 20, my + 50))

        slot_y_start = 75
        for i, slot_ui in enumerate(self.slot_uis):
            sy = my + slot_y_start + i * (SaveSlotUI.SLOT_H + SaveSlotUI.GAP)
            sx = mx + (self.MENU_W - SaveSlotUI.SLOT_W) // 2
            slot_ui.render(surface, font_big, font_small, self.simboli_font,
                           sx, sy, selected=(i == self.selected), main_col=main_col)

        pygame.draw.line(surface, (40, 50, 60), (mx + 20, my + self.MENU_H - 50), (mx + self.MENU_W - 20, my + self.MENU_H - 50))

        action = "Salva" if current_mode == "save" else "Carica"
        hint_str = f"↑↓ Naviga   INVIO {action}   CANC Elimina   ESC Chiudi"
        hint = font_hint.render(hint_str, True, (120, 130, 140))
        surface.blit(hint, (mx + (self.MENU_W - hint.get_width()) // 2, my + self.MENU_H - 35))

        if self._msg_timer > 0:
            self._msg_timer -= 1
            msg_surf = font_small.render(self._message, True, (255, 214, 0))
            surface.blit(msg_surf, (mx + (self.MENU_W - msg_surf.get_width()) // 2, my + self.MENU_H - 85))



class SaveMenuSystem(ISystem):
    """ISystem che gestisce il menu di salvataggio/caricamento.

        Si iscrive agli eventi ``SAVE_REQUESTED`` e ``LOAD_REQUESTED``.
        Espone ``is_open`` per comunicare allo ``SaveMenuHandler`` di bloccare
        la propagazione degli eventi alla Screen corrente.
    """
    NUM_SLOTS = 3

    def __init__(self, save_manager: "SaveManager", game_manager: "GameManager") -> None:
        self._save_manager  = save_manager
        self._game_manager  = game_manager
        self._bus: EventBus | None = None

        self._slot_infos: list[SaveSlotInfo] = [SaveSlotInfo(slot_id=i + 1) for i in range(self.NUM_SLOTS)]
        self._ui = SaveMenuUI(self._slot_infos)
        self.is_open: bool = False
        self.mode: str = "save"

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus
        bus.subscribe(EventType.SAVE_REQUESTED, self._on_save_requested)
        bus.subscribe(EventType.LOAD_REQUESTED, self._on_load_requested)
        self._refresh_slot_infos()

    def cleanup(self) -> None:
        if self._bus:
            self._bus.unsubscribe(EventType.SAVE_REQUESTED, self._on_save_requested)
            self._bus.unsubscribe(EventType.LOAD_REQUESTED, self._on_load_requested)

    def toggle(self, mode: str = "save") -> None:
        self.is_open = not self.is_open
        if self.is_open:
            self.mode = mode
            self._refresh_slot_infos()

    def handle_input(self, pygame_events: list) -> None:
        if not _PYGAME_AVAILABLE or not self.is_open:
            return

        for event in pygame_events:
            if event.type != pygame.KEYDOWN:
                continue

            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.is_open = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._ui.navigate(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._ui.navigate(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.mode == "load":
                    self._do_load()
                else:
                    self._do_save()
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                self._do_delete()

    def render(self, surface, screen_w: int, screen_h: int,
               font_title, font_big, font_small, font_hint, current_mode) -> None:
        if self.is_open:
            self._ui.render(surface, screen_w, screen_h, font_title, font_big, font_small, font_hint, self.mode)

    def _do_save(self) -> None:
        slot_id = self._ui.selected_slot_id
        self._save_manager.save_game(self._game_manager, slot_id)
        self._refresh_slot_infos()
        self._ui.set_message(f"✔ Partita Salvata con successo nello Slot {slot_id}!")
        if self._bus:
            self._bus.publish(EventType.GAME_SAVED, {"slot_id": slot_id})

    def _do_load(self) -> None:
        slot_id = self._ui.selected_slot_id
        success = self._save_manager.load_game(self._game_manager, slot_id)

        if success:
            self._ui.set_message(f"✔ Caricamento Slot {slot_id} completato!")
            self.is_open = False

            gs = self._game_manager
            gs.current_battle_npc = None
            gs.predialogue_npc    = None

            if gs._explore_screen is not None and hasattr(gs._explore_screen, "_tutti_i_mob_reali"):
                from game.systems.world_rules import WorldRulesSystem
                world_rules = gs.get_system(WorldRulesSystem)
                if world_rules:
                    world_rules._aggro_triggers = []
                    world_rules.build_aggro_from_npc_list(gs._explore_screen._tutti_i_mob_reali)

            gs.screen = "explore"
            if self._bus:
                self._bus.publish(EventType.GAME_LOADED, {"slot_id": slot_id})
        else:
            self._ui.set_message(f"⚠ Errore: Lo Slot {slot_id} è vuoto o corrotto.")

    def _do_delete(self) -> None:
        slot_id = self._ui.selected_slot_id
        deleted = self._save_manager.delete_save(slot_id)
        if deleted:
            self._refresh_slot_infos()
            self._ui.set_message(f"✔ Slot {slot_id} eliminato.")
            if self._bus:
                self._bus.publish(EventType.SAVE_DELETED, {"slot_id": slot_id})
        else:
            self._ui.set_message(f"Lo Slot {slot_id} è già vuoto.")

    def _on_save_requested(self, data: dict) -> None:
        target_slot = self._save_manager.get_first_empty_slot(self.NUM_SLOTS)
        self._ui.selected = target_slot - 1
        self._do_save()

    def _on_load_requested(self, data: dict) -> None:
        slot_id = data.get("slot_id", 1)
        self._ui.selected = slot_id - 1
        self._do_load()

    def _refresh_slot_infos(self) -> None:
        for i in range(self.NUM_SLOTS):
            slot_id = i + 1
            meta = self._save_manager.get_slot_metadata(slot_id)
            self._slot_infos[i].is_empty = meta["is_empty"]
            self._slot_infos[i].timestamp = meta["timestamp"]
            self._slot_infos[i].location = meta["location"]