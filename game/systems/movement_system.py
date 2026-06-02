"""
movement_system.py — Sistema di movimento dei giocatori con collisione pixel-perfect.

Struttura
---------
- ``KeyBinding``           : dataclass con i tasti di controllo per un giocatore.
- ``PlayerMovementState``  : dataclass con posizione tile e pixel, direzione e delay.
- ``MovementSystem``       : ISystem che aggiorna la posizione di tutti i giocatori
                             ogni frame, con collision detection tramite MapData.

Il sistema supporta due modalità:
- **Con MapData** (``set_maps`` chiamato): movimento pixel-perfect con collisione
  circolare a 8 punti attorno al personaggio.
- **Senza MapData** (fallback): movimento tile-per-tile senza collisione.
"""

from __future__ import annotations
from dataclasses import dataclass, field

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.events.isystem import ISystem


@dataclass
class KeyBinding:
    """Associazione tasti per il controllo di un giocatore.

    Attributes:
        up, down, left, right: Codici tasto pygame (``pygame.K_*``).
    """
    up:    int
    down:  int
    left:  int
    right: int

    @classmethod
    def default_p1(cls) -> "KeyBinding":
        """Binding default per P1: WASD (o codici numerici se pygame non disponibile)."""
        if not _PYGAME_AVAILABLE:
            return cls(up=119, down=115, left=97, right=100)
        return cls(up=pygame.K_w, down=pygame.K_s, left=pygame.K_a, right=pygame.K_d)

    @classmethod
    def default_p2(cls) -> "KeyBinding":
        """Binding default per P2: frecce direzionali."""
        if not _PYGAME_AVAILABLE:
            return cls(up=273, down=274, left=276, right=275)
        return cls(up=pygame.K_UP, down=pygame.K_DOWN,
                   left=pygame.K_LEFT, right=pygame.K_RIGHT)


@dataclass
class PlayerMovementState:
    """Stato di movimento di un singolo giocatore.

    Mantiene sia la posizione in tile (``col``, ``row``) che la posizione
    in pixel (``pixel_x``, ``pixel_y``) per il rendering fluido.

    Attributes:
        player_id:     Identificatore del giocatore ("Rivet", "Echo", "p1", "p2").
        character:     Oggetto ``Character`` associato.
        binding:       Tasti di controllo.
        col, row:      Posizione attuale in tile.
        move_delay:    Frame tra uno spostamento e il successivo (modalità tile).
        pixel_x/y:     Posizione in pixel (centro del personaggio).
        last_dir:      Ultima direzione di movimento ("up", "down", "left", "right").
    """
    player_id:      str
    character:      object
    binding:        KeyBinding
    col:            int   = 0
    row:            int   = 0
    move_delay:     int   = 6
    _frame_counter: int   = field(default=6, init=False, repr=False)

    pixel_x:  float = field(default=0.0, init=False, repr=False)
    pixel_y:  float = field(default=0.0, init=False, repr=False)
    last_dir: str   = field(default="down", init=False, repr=False)

    def __post_init__(self):
        """Inizializza la posizione pixel dal centro della tile iniziale."""
        try:
            from game.world.city_engine import MAP_TILE_PX
            self.pixel_x = float(self.col * MAP_TILE_PX + MAP_TILE_PX / 2)
            self.pixel_y = float(self.row * MAP_TILE_PX + MAP_TILE_PX / 2)
        except ImportError:
            self.pixel_x = float(self.col * 32 + 16)
            self.pixel_y = float(self.row * 32 + 16)


class MovementSystem(ISystem):
    """Sistema che aggiorna la posizione dei giocatori ogni frame.

    Supporta due modalità di collisione:
    - **Pixel-perfect con MapData**: controlla 8 punti attorno al personaggio
      (raggio COLL_R = 0.35 tile) per gestire angoli e sliding.
    - **Fallback tile**: movimento diretto senza collision detection.

    Attributes:
        MAP_COLS, MAP_ROWS: Dimensioni della griglia (fallback senza MapData).
    """

    MAP_COLS: int = 195
    MAP_ROWS: int = 146

    def __init__(self) -> None:
        self._bus:     EventBus | None = None
        self._players: dict[str, PlayerMovementState] = {}
        self._maps:    list   = []
        self._city_w:  int    = 0
        self._city_h:  int    = 0
        self._coll_r:  float  = 0.0

    def initialize(self, bus: EventBus) -> None:
        """Registra il bus; questo sistema non si iscrive ad eventi.

        Args:
            bus: L'istanza condivisa dell'``EventBus``.
        """
        self._bus = bus

    def cleanup(self) -> None:
        """No-op: nessuna iscrizione da rimuovere."""
        pass

    def register_player(self, player_id: str, character,
                        binding: KeyBinding | None = None,
                        start_col: int = 0, start_row: int = 0,
                        move_delay: int = 6) -> None:
        """Registra un giocatore nel sistema con posizione e binding iniziali.

        Args:
            player_id:  Identificatore univoco del giocatore.
            character:  Oggetto ``Character`` associato.
            binding:    Tasti di controllo; se ``None`` usa il default per il player_id.
            start_col:  Colonna di partenza sulla griglia.
            start_row:  Riga di partenza sulla griglia.
            move_delay: Frame tra spostamenti in modalità tile.
        """
        b = binding or (KeyBinding.default_p1() if player_id in ("Rivet", "p1")
                        else KeyBinding.default_p2())
        state = PlayerMovementState(
            player_id=player_id, character=character,
            binding=b, col=start_col, row=start_row,
            move_delay=move_delay,
        )
        self._players[player_id] = state

    def set_maps(self, maps: list, city_w: int, city_h: int) -> None:
        """Configura la collision detection pixel-perfect con i MapData di city_engine.

        Il raggio di collisione è 0.35 tile, identico a ``city_engine.Player.COLL_R``.

        Args:
            maps:   Lista di ``MapData`` con metodo ``is_collision(wx, wy)``.
            city_w: Larghezza totale della città in pixel.
            city_h: Altezza totale della città in pixel.
        """
        from game.world.city_engine import MAP_TILE_PX
        self._maps   = maps
        self._city_w = city_w
        self._city_h = city_h
        self._coll_r = MAP_TILE_PX * 0.35

    def set_obstacles(self, obstacle_positions: list) -> None:
        """Retrocompatibilità — non più usato se ``set_maps`` è chiamato."""
        pass

    def _blocked(self, wx: float, wy: float) -> bool:
        """Verifica se un punto in pixel è in collisione con un MapData.

        Args:
            wx, wy: Coordinate pixel del punto da verificare.

        Returns:
            ``True`` se il punto è in collisione, ``False`` altrimenti.
        """
        for m in self._maps:
            if (m.offset_x <= wx < m.offset_x + m.width_px and
                    m.offset_y <= wy < m.offset_y + m.height_px):
                if m.is_collision(wx, wy):
                    return True
        return False

    def _can_move_to(self, nx: float, ny: float) -> bool:
        """Verifica se la posizione (nx, ny) è libera da collisioni.

        Controlla 8 punti di test attorno al centro del personaggio
        (4 cardinali + 4 diagonali a 70.71% del raggio) per gestire
        correttamente gli angoli.

        Args:
            nx, ny: Nuova posizione in pixel (centro personaggio).

        Returns:
            ``True`` se la posizione è libera, ``False`` se c'è collisione.
        """
        r    = self._coll_r
        nx   = max(r, min(self._city_w - r, nx))
        ny   = max(r, min(self._city_h - r, ny))
        diag = r * 0.7071   # cos(45°) ≈ 0.7071
        return not (
            self._blocked(nx - r,    ny      ) or
            self._blocked(nx + r,    ny      ) or
            self._blocked(nx,        ny - r  ) or
            self._blocked(nx,        ny + r  ) or
            self._blocked(nx - diag, ny - diag) or
            self._blocked(nx + diag, ny - diag) or
            self._blocked(nx - diag, ny + diag) or
            self._blocked(nx + diag, ny + diag)
        )

    def update(self, keys_pressed) -> list[dict]:
        """Aggiorna la posizione di tutti i giocatori per il frame corrente.

        In modalità pixel-perfect:
        - Movimento diagonale normalizzato (×0.7071).
        - Sliding: se il movimento combinato è bloccato, tenta X e Y separatamente.

        In modalità tile (fallback):
        - Movimento di 1 tile per pressione tasto, con clamp ai bordi della mappa.

        Args:
            keys_pressed: Dizionario ``{keycode: bool}`` di ``pygame.key.get_pressed()``.

        Returns:
            Lista di dict, uno per giocatore, con chiavi:
            player, col, row, moved, is_moving, last_dir, pixel_x, pixel_y.
        """
        results: list[dict] = []

        try:
            from game.world.city_engine import MAP_TILE_PX
        except ImportError:
            MAP_TILE_PX = 32

        MOVE_SPEED = 4.0   # Pixel per frame

        for pid, state in self._players.items():
            b = state.binding
            up    = keys_pressed[b.up]
            down  = keys_pressed[b.down]
            left  = keys_pressed[b.left]
            right = keys_pressed[b.right]
            is_moving = up or down or left or right

            # Aggiorna l'ultima direzione
            if up:    state.last_dir = "up"
            elif down:  state.last_dir = "down"
            elif left:  state.last_dir = "left"
            elif right: state.last_dir = "right"

            moved = False

            if is_moving:
                if self._maps:
                    # --- Modalità pixel-perfect ---
                    dx = dy = 0.0
                    if up:    dy = -MOVE_SPEED
                    elif down:  dy =  MOVE_SPEED
                    if left:  dx = -MOVE_SPEED
                    elif right: dx =  MOVE_SPEED

                    # Normalizza la diagonale
                    if dx != 0 and dy != 0:
                        dx *= 0.7071
                        dy *= 0.7071

                    nx = state.pixel_x + dx
                    ny = state.pixel_y + dy

                    if self._can_move_to(nx, ny):
                        state.pixel_x = nx
                        state.pixel_y = ny
                        moved = True
                    elif dx != 0 and self._can_move_to(nx, state.pixel_y):
                        # Sliding orizzontale
                        state.pixel_x = nx
                        moved = True
                    elif dy != 0 and self._can_move_to(state.pixel_x, ny):
                        # Sliding verticale
                        state.pixel_y = ny
                        moved = True

                else:
                    # --- Modalità tile (fallback) ---
                    new_col, new_row = state.col, state.row
                    if up:    new_row -= 1
                    elif down:  new_row += 1
                    if left:  new_col -= 1
                    elif right: new_col += 1
                    new_col = max(0, min(self.MAP_COLS - 1, new_col))
                    new_row = max(0, min(self.MAP_ROWS - 1, new_row))
                    if (new_col, new_row) != (state.col, state.row):
                        state.col, state.row = new_col, new_row
                        state.pixel_x = state.col * MAP_TILE_PX + MAP_TILE_PX / 2
                        state.pixel_y = state.row * MAP_TILE_PX + MAP_TILE_PX / 2
                        moved = True

            # Aggiorna le coordinate tile dal pixel
            state.col = int(state.pixel_x / MAP_TILE_PX)
            state.row = int(state.pixel_y / MAP_TILE_PX)
            if self._city_w > 0:
                max_col = int(self._city_w / MAP_TILE_PX) - 1
                max_row = int(self._city_h / MAP_TILE_PX) - 1
            else:
                max_col = self.MAP_COLS - 1
                max_row = self.MAP_ROWS - 1
            state.col = max(0, min(max_col, state.col))
            state.row = max(0, min(max_row, state.row))

            results.append({
                "player":    pid,
                "col":       state.col,
                "row":       state.row,
                "moved":     moved,
                "is_moving": is_moving,
                "last_dir":  state.last_dir,
                "pixel_x":   state.pixel_x,
                "pixel_y":   state.pixel_y,
            })

        return results

    def get_position(self, player_id: str) -> tuple[int, int] | None:
        """Restituisce la posizione in tile del giocatore, o ``None`` se non registrato.

        Args:
            player_id: Identificatore del giocatore.

        Returns:
            Coppia ``(col, row)`` oppure ``None``.
        """
        state = self._players.get(player_id)
        return (state.col, state.row) if state else None

    def set_position(self, player_id: str, col: int, row: int) -> None:
        """Imposta la posizione del giocatore direttamente (teleport).

        Aggiorna sia le coordinate tile che quelle pixel.

        Args:
            player_id: Identificatore del giocatore.
            col:       Nuova colonna.
            row:       Nuova riga.
        """
        state = self._players.get(player_id)
        if state:
            try:
                from game.world.city_engine import MAP_TILE_PX
            except ImportError:
                MAP_TILE_PX = 32
            max_c = int(self._city_w / MAP_TILE_PX) - 1 if self._city_w > 0 else self.MAP_COLS - 1
            max_r = int(self._city_h / MAP_TILE_PX) - 1 if self._city_h > 0 else self.MAP_ROWS - 1
            state.col     = max(0, min(max_c, col))
            state.row     = max(0, min(max_r, row))
            state.pixel_x = float(state.col * MAP_TILE_PX + MAP_TILE_PX / 2)
            state.pixel_y = float(state.row * MAP_TILE_PX + MAP_TILE_PX / 2)
