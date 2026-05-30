"""
base_screen.py — Classe base astratta per tutte le screen del gioco (pattern State GoF).

``Screen`` rappresenta uno State nel pattern State GoF: il ``GameManager``
mantiene un riferimento alla screen corrente e delega le operazioni di
input, update e draw ad essa. Il cambio di stato avviene impostando
``gs.screen`` su un diverso nome di screen registrata.

Ogni sottoclasse concreta deve implementare i tre metodi astratti.
"""

from abc import ABC, abstractmethod
from pygame import Surface


class Screen(ABC):
    """State astratto GoF — interfaccia comune per tutte le screen del gioco.

    Tutte le sottoclassi DEVONO implementare i tre metodi astratti.
    Python solleva ``TypeError`` a tempo di istanziazione se uno è mancante.
    """

    @abstractmethod
    def handle_event(self, event) -> None:
        """Gestisce un singolo evento pygame per il frame corrente.

        Args:
            event: Oggetto ``pygame.event.Event`` da processare.
        """
        ...

    @abstractmethod
    def update(self) -> None:
        """Aggiorna la logica interna dello stato per il frame corrente.

        Chiamato una volta per frame prima di ``draw()``.
        Deve essere O(1) o comunque veloce per rispettare il frame budget.
        """
        ...

    @abstractmethod
    def draw(self, surf: Surface) -> None:
        """Disegna lo stato corrente sulla surface fornita.

        Args:
            surf: La surface pygame su cui disegnare (canvas logico W×H).
        """
        ...

    def on_enter(self) -> None:
        """Chiamato quando si entra nello state. Override nelle sottoclassi se necessario."""
        pass

    def on_exit(self) -> None:
        """Chiamato quando si esce dallo state. Override nelle sottoclassi se necessario."""
        pass
