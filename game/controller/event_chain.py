"""
event_chain.py — Catena di responsabilità (Chain of Responsibility GoF) per gli eventi pygame.

Struttura
---------
- ``EventHandler``       : Handler astratto con metodi ``set_next()`` e ``handle()``.
- ``QuitHandler``        : Intercetta ``pygame.QUIT`` e termina l'app.
- ``VideoResizeHandler`` : Aggiorna surf e scala al ridimensionamento finestra.
- ``MouseScaleHandler``  : Corregge le coordinate mouse per la scala canvas/finestra.
- ``SaveMenuHandler``    : Blocca la propagazione mentre il menu di salvataggio è aperto.
- ``ScreenHandler``      : Handler terminale che delega alla Screen corrente.
- ``build_event_chain``  : Factory function che assembla la catena completa.

Priorità (dal più al meno urgente)
-----------------------------------
    QuitHandler → VideoResizeHandler → MouseScaleHandler
        → SaveMenuHandler → ScreenHandler
"""

from __future__ import annotations
import sys
from abc import ABC, abstractmethod
import pygame


# ---------------------------------------------------------------------------
# Handler astratto
# ---------------------------------------------------------------------------

class EventHandler(ABC):
    """Handler astratto — Chain of Responsibility GoF.

    Ogni handler concreto:
    1. Verifica se può gestire l'evento.
    2. Se sì, lo gestisce e restituisce ``True`` (evento consumato).
    3. Se no, chiama ``_pass(event)`` per delegare al successivo della catena.

    ``set_next()`` restituisce il successivo per permettere chaining fluente::

        h1.set_next(h2).set_next(h3)
    """

    def __init__(self) -> None:
        self._next: EventHandler | None = None

    def set_next(self, handler: "EventHandler") -> "EventHandler":
        """Imposta il prossimo handler nella catena.

        Args:
            handler: Il prossimo handler da collegare.

        Returns:
            ``handler`` stesso (per chaining fluente).
        """
        self._next = handler
        return handler

    @abstractmethod
    def handle(self, event: pygame.event.Event) -> bool:
        """Gestisce l'evento.

        Args:
            event: Evento pygame da processare.

        Returns:
            ``True`` se l'evento è stato consumato, ``False`` altrimenti.
        """
        ...

    def _pass(self, event: pygame.event.Event) -> bool:
        """Delega l'evento al successivo nella catena.

        Args:
            event: Evento da propagare.

        Returns:
            Il valore restituito dal successivo, o ``False`` se è l'ultimo.
        """
        if self._next:
            return self._next.handle(event)
        return False


# ---------------------------------------------------------------------------
# ConcreteHandler — in ordine di priorità
# ---------------------------------------------------------------------------

class QuitHandler(EventHandler):
    """Intercetta ``pygame.QUIT`` e termina l'applicazione in modo pulito.

    Priorità: massima — il quit deve sempre essere gestito per primo.
    Consuma: sempre (non ha senso propagare un evento di chiusura).

    Args:
        gs: Il ``GameManager`` singleton (per chiamare ``audio.shutdown()``).
    """

    def __init__(self, gs) -> None:
        super().__init__()
        self._gs = gs

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            self._gs.audio.shutdown()
            pygame.quit()
            sys.exit()
        return self._pass(event)


class VideoResizeHandler(EventHandler):
    """Intercetta ``VIDEORESIZE`` e aggiorna surf e scala nella ``state_ref`` condivisa.

    ``state_ref`` è un dizionario mutabile condiviso con ``game_manager``::

        {"surf": Surface, "scale_x": float, "scale_y": float, "W": int, "H": int}

    Usare un dict mutabile permette all'handler di aggiornare i valori
    senza dover passare riferimenti a oggetti non serializzabili.

    Consuma: sì — il resize è gestito qui, non ha senso propagarlo alla Screen.

    Args:
        state_ref: Dict mutabile con le informazioni di scala della finestra.
    """

    def __init__(self, state_ref: dict) -> None:
        super().__init__()
        self._state = state_ref

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.VIDEORESIZE:
            self._state["surf"] = pygame.display.set_mode(
                event.size, pygame.RESIZABLE
            )
            win_w, win_h = self._state["surf"].get_size()
            self._state["scale_x"] = self._state["W"] / win_w
            self._state["scale_y"] = self._state["H"] / win_h
            return True
        return self._pass(event)


class MouseScaleHandler(EventHandler):
    """Corregge le coordinate mouse per la scala finestra→canvas interno.

    Quando la finestra è ridimensionata, le coordinate mouse riportate da
    pygame si riferiscono alla finestra fisica. Questo handler le converte
    alle coordinate del canvas logico (W×H) prima che la Screen le riceva.

    Non consuma l'evento: lo trasforma in-place e lo propaga.

    Args:
        state_ref: Dict mutabile con ``scale_x`` e ``scale_y``.
    """

    def __init__(self, state_ref: dict) -> None:
        super().__init__()
        self._state = state_ref

    def handle(self, event: pygame.event.Event) -> bool:
        if event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            mx, my = event.pos
            event.dict["pos"] = (
                int(mx * self._state["scale_x"]),
                int(my * self._state["scale_y"]),
            )
        return self._pass(event)


class SaveMenuHandler(EventHandler):
    """Blocca la propagazione agli handler successivi se il menu di salvataggio è aperto.

    Il ``SaveMenuSystem`` gestisce il proprio input tramite ``handle_input(events)``
    nel loop principale; questo handler impedisce che gli stessi eventi raggiungano
    anche la Screen corrente, evitando doppio processing.

    Consuma: sì se save_menu aperto, no altrimenti.

    Args:
        gs: Il ``GameManager`` singleton per accedere ai sistemi registrati.
    """

    def __init__(self, gs) -> None:
        super().__init__()
        self._gs = gs

    def handle(self, event: pygame.event.Event) -> bool:
        from game.systems.save_ui import SaveMenuSystem
        save_sys = self._gs.get_system(SaveMenuSystem)
        if save_sys and save_sys.is_open:
            return True   # Consumato: la Screen non vede questo evento
        return self._pass(event)


class ScreenHandler(EventHandler):
    """Handler terminale che delega l'evento alla Screen corrente.

    È sempre l'ultimo della catena; non ha un successivo.
    Consuma: dipende dalla Screen (restituisce il valore di ``handle_event``).

    Args:
        screens_ref: Dict ``{screen_name: Screen}`` con tutte le screen registrate.
        gs:          Il ``GameManager`` singleton per leggere ``gs.screen``.
    """

    def __init__(self, screens_ref: dict, gs) -> None:
        super().__init__()
        self._screens = screens_ref
        self._gs      = gs

    def handle(self, event: pygame.event.Event) -> bool:
        current = self._screens.get(self._gs.screen)
        if current and hasattr(current, "handle_event"):
            current.handle_event(event)
        return False


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def build_event_chain(gs, state_ref: dict, screens_ref: dict) -> EventHandler:
    """Costruisce e restituisce la catena CoR completa.

    Ordine di priorità (dal più al meno urgente):
        ``QuitHandler → VideoResizeHandler → MouseScaleHandler
        → SaveMenuHandler → ScreenHandler``

    Args:
        gs:          ``GameManager`` singleton.
        state_ref:   Dict mutabile con keys: ``surf``, ``scale_x``, ``scale_y``, ``W``, ``H``.
        screens_ref: Dict ``{screen_name: Screen}`` usato da ``ScreenHandler``.

    Returns:
        Il primo handler della catena (``QuitHandler``).
    """
    quit_h   = QuitHandler(gs)
    resize_h = VideoResizeHandler(state_ref)
    mouse_h  = MouseScaleHandler(state_ref)
    save_h   = SaveMenuHandler(gs)
    screen_h = ScreenHandler(screens_ref, gs)

    quit_h.set_next(resize_h).set_next(mouse_h).set_next(save_h).set_next(screen_h)

    return quit_h
