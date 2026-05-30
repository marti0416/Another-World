"""
hacking_system_fixed.py — Mini-giochi di hacking con puzzle procedurali.

Struttura
---------
- ``IPuzzle``        : interfaccia astratta per i puzzle di hacking.
- ``PipePuzzle``     : puzzle a tubi con percorso procedurale (ruota i tubi per connettere).
- ``RadarPuzzle``    : puzzle a frequenze radar (indovina la frequenza giusta).
- ``NodePuzzle``     : puzzle a nodi di rete (connetti i nodi nel giusto ordine).
- ``HackingSystem``  : ISystem che gestisce i terminali hackabili sulla mappa.
"""

from __future__ import annotations
import random
from game.events.isystem import ISystem
from game.events.event_bus import EventBus


from abc import ABC, abstractmethod as _abstractmethod

class IPuzzle(ABC):
    """Interfaccia astratta per i puzzle di hacking.

        Ogni ConcreteIPuzzle implementa ``is_solved()``, ``submit(inp)``
        e ``__str__()`` per la rappresentazione testuale del puzzle.
    """
    @_abstractmethod
    def is_solved(self) -> bool: ...
    @_abstractmethod
    def submit(self, inp: str) -> str: ...
    @_abstractmethod
    def __str__(self) -> str: ...


class PipePuzzle(IPuzzle):
    """Pipe Puzzle Procedurale: genera un percorso univoco ogni volta."""

    PIPES = {
        "━": (0, 1, 0, 1), "┃": (1, 0, 1, 0), "┏": (0, 1, 1, 0), "┓": (0, 0, 1, 1),
        "┗": (1, 1, 0, 0), "┛": (1, 0, 0, 1), "┣": (1, 1, 1, 0), "┫": (1, 0, 1, 1),
        "┳": (0, 1, 1, 1), "┻": (1, 1, 0, 1), "╋": (1, 1, 1, 1)
    }

    ROTATIONS = {
        "━": "┃", "┃": "━",
        "┏": "┓", "┓": "┛", "┛": "┗", "┗": "┏",
        "┣": "┳", "┳": "┫", "┫": "┻", "┻": "┣",
        "╋": "╋"
    }

    def __init__(self, skills: list[str]) -> None:
        self._cursor_c = 1
        self._cursor_r = 1

        self._moves = 30 if "Espansione di Banda" in skills else 20

        def get_dir(r1, c1, r2, c2):
            if r2 < r1: return 0
            if c2 > c1: return 1
            if r2 > r1: return 2
            if c2 < c1: return 3

        def _is_solved_grid(reels) -> bool:
            grid = [[reels[c][r] for c in range(3)] for r in range(3)]
            start_pipe = grid[1][0]
            if self.PIPES[start_pipe][3] == 0: return False
            queue = [(1, 0)]
            visited = set()
            while queue:
                r, c = queue.pop(0)
                if (r, c) in visited: continue
                visited.add((r, c))
                pipe = grid[r][c]
                conn = self.PIPES[pipe]
                if c == 2 and conn[1] == 1: return True
                if conn[0] == 1 and r > 0 and (r-1,c) not in visited:
                    if self.PIPES[grid[r-1][c]][2] == 1: queue.append((r-1, c))
                if conn[1] == 1 and c < 2 and (r,c+1) not in visited:
                    if self.PIPES[grid[r][c+1]][3] == 1: queue.append((r, c+1))
                if conn[2] == 1 and r < 2 and (r+1,c) not in visited:
                    if self.PIPES[grid[r+1][c]][0] == 1: queue.append((r+1, c))
                if conn[3] == 1 and c > 0 and (r,c-1) not in visited:
                    if self.PIPES[grid[r][c-1]][1] == 1: queue.append((r, c-1))
            return False

        def _can_be_solved_in_few_moves(reels_to_check, max_moves=2) -> bool:
            if _is_solved_grid(reels_to_check): return True
            queue = [(reels_to_check, 0)]
            visited = set()
            def serialize(g): return tuple(tuple(col) for col in g)
            visited.add(serialize(reels_to_check))

            while queue:
                current_grid, depth = queue.pop(0)
                if depth > 0 and _is_solved_grid(current_grid): return True
                if depth < max_moves:
                    for c in range(3):
                        for r in range(3):
                            new_grid = [col[:] for col in current_grid]
                            new_grid[c][r] = self.ROTATIONS[new_grid[c][r]]
                            ser = serialize(new_grid)
                            if ser not in visited:
                                visited.add(ser)
                                queue.append((new_grid, depth + 1))
            return False

        def _apply_rotations(reels_ref, rot_map):
            result = [col[:] for col in reels_ref]
            for c in range(3):
                for r in range(3):
                    for _ in range(rot_map[c][r]):
                        result[c][r] = self.ROTATIONS[result[c][r]]
            return result

        def _rotations_needed_on_path(solution, scrambled, path):
            total = 0
            for (r, c) in path:
                cur = scrambled[c][r]
                for n in range(4):
                    if cur == solution[c][r]:
                        total += n
                        break
                    cur = self.ROTATIONS[cur]
            return total

        puzzle_ready = False
        while not puzzle_ready:
            self._reels = [["" for _ in range(3)] for _ in range(3)]

            paths = []
            def dfs(r, c, current_path):
                if c == 2:
                    paths.append(current_path + [(r, c)])
                    return
                for dr, dc in [(-1, 0), (1, 0), (0, 1), (0, -1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 3 and 0 <= nc < 3 and (nr, nc) not in current_path:
                        dfs(nr, nc, current_path + [(r, c)])

            dfs(1, 0, [])
            chosen_path = random.choice(paths)

            path_cells = set(chosen_path)
            for i, (r, c) in enumerate(chosen_path):
                req = [0, 0, 0, 0]
                if i == 0: req[3] = 1
                else:
                    pr, pc = chosen_path[i-1]
                    req[get_dir(r, c, pr, pc)] = 1

                if i == len(chosen_path) - 1: req[1] = 1
                else:
                    nr, nc = chosen_path[i+1]
                    req[get_dir(r, c, nr, nc)] = 1

                valid_pipes = [p for p, conn in self.PIPES.items() if conn[0]>=req[0] and conn[1]>=req[1] and conn[2]>=req[2] and conn[3]>=req[3]]
                self._reels[c][r] = random.choice(valid_pipes)

            all_pipes = list(self.PIPES.keys())
            for c in range(3):
                for r in range(3):
                    if (r, c) not in path_cells:
                        self._reels[c][r] = random.choice(all_pipes)

            solution_reels = [col[:] for col in self._reels]

            for _attempt in range(50):
                rot_map = [[random.randint(0, 3) for _ in range(3)] for _ in range(3)]
                scrambled = _apply_rotations(solution_reels, rot_map)
                needed = _rotations_needed_on_path(solution_reels, scrambled, chosen_path)

                if 3 <= needed <= 5 and not _can_be_solved_in_few_moves(scrambled, 2):
                    self._reels = scrambled
                    puzzle_ready = True
                    break

        self._solved = self._check_path()

    def submit(self, inp: str) -> str:
        if inp == "UP": self._cursor_r = max(0, self._cursor_r - 1); return "Cursore: SU"
        elif inp == "DOWN": self._cursor_r = min(2, self._cursor_r + 1); return "Cursore: GIÙ"
        elif inp == "LEFT": self._cursor_c = max(0, self._cursor_c - 1); return "Cursore: SX"
        elif inp == "RIGHT": self._cursor_c = min(2, self._cursor_c + 1); return "Cursore: DX"
        elif inp == "ROTATE":
            char = self._reels[self._cursor_c][self._cursor_r]
            self._reels[self._cursor_c][self._cursor_r] = self.ROTATIONS[char]
            self._solved = self._check_path()
            if self._solved:
                return "Routing completato! Energia instradata."
            return "Nodo ruotato."
        return "Comando non riconosciuto."

    def _check_path(self) -> bool:
        grid = [[self._reels[c][r] for c in range(3)] for r in range(3)]
        start_pipe = grid[1][0]
        if self.PIPES[start_pipe][3] == 0: return False

        queue = [(1, 0)]
        visited = set()
        while queue:
            r, c = queue.pop(0)
            if (r, c) in visited: continue
            visited.add((r, c))

            pipe = grid[r][c]
            conn = self.PIPES[pipe]
            if c == 2 and conn[1] == 1: return True

            if conn[0] == 1 and r > 0 and (r-1, c) not in visited:
                if self.PIPES[grid[r-1][c]][2] == 1: queue.append((r-1, c))
            if conn[1] == 1 and c < 2 and (r, c+1) not in visited:
                if self.PIPES[grid[r][c+1]][3] == 1: queue.append((r, c+1))
            if conn[2] == 1 and r < 2 and (r+1, c) not in visited:
                if self.PIPES[grid[r+1][c]][0] == 1: queue.append((r+1, c))
            if conn[3] == 1 and c > 0 and (r, c-1) not in visited:
                if self.PIPES[grid[r][c-1]][1] == 1: queue.append((r, c-1))
        return False

    def is_solved(self) -> bool:
        return self._solved

    def __str__(self) -> str:
        return "PIPE ROUTING"


class RadarPuzzle(IPuzzle):
    """Puzzle a frequenze radar: individua la frequenza corretta entro N tentativi.

        Ad ogni tentativo fornisce feedback "troppo alta" / "troppo bassa" / "giusta".
    """
    def __init__(self, skills: list[str]) -> None:
        self._scans  = 5
        self._last_ping = None

        self.SIZE = 7 if "Override Radar" in skills else 10

        self._pos = random.randint(0, self.SIZE - 1)
        self._target = random.randint(0, self.SIZE - 1)
        while self._target == self._pos:
            self._target = random.randint(0, self.SIZE - 1)

        self._solved = False

    def submit(self, inp: str) -> str:
        if inp == "LEFT": self._pos = max(0, self._pos - 1); return f"Posizione: {self._pos}"
        elif inp == "RIGHT": self._pos = min(self.SIZE - 1, self._pos + 1); return f"Posizione: {self._pos}"
        elif inp == "PING":
            dist = abs(self._pos - self._target)
            power = max(0, 100 - (dist * 15))
            self._last_ping = power
            if dist == 0:
                self._solved = True
                return f"Frequenza 100% agganciata! Accesso."
            return f"Ping: potenza {power}%"
        return "Usa LEFT / RIGHT / PING."

    def is_solved(self) -> bool:
        return self._solved

    def __str__(self) -> str:
        bar = ["─"] * self.SIZE
        if 0 <= self._pos < self.SIZE:
            bar[self._pos] = "▲"
        return "RADAR [" + "".join(bar) + "]"


class NodePuzzle(IPuzzle):
    """Puzzle a nodi di rete: connetti i nodi nel giusto ordine crittografato.

        Ogni nodo ha un ID cifrato; il giocatore deve inserire la sequenza corretta.
    """
    def __init__(self, skills: list[str]) -> None:
        self._secret  = [str(random.randint(1, 6)) for _ in range(4)]
        self._entered: list[str] = []
        self._history: list[tuple] = []
        self._solved  = False
        self._skills  = skills

        if "Decrittazione Automatica" in skills:
            self._entered.append(self._secret[0])

    def _evaluate(self, attempt: list[str]) -> list[str]:
        """Restituisce una lista di 4 colori per l'attempt dato."""
        colors   = ["grey"] * 4
        sec_copy = self._secret[:]

        for i in range(4):
            if attempt[i] == sec_copy[i]:
                colors[i]   = "green"
                sec_copy[i] = None

        for i in range(4):
            if colors[i] == "green":
                continue
            if attempt[i] in sec_copy:
                colors[i] = "yellow"
                sec_copy[sec_copy.index(attempt[i])] = None

        return colors

    def submit(self, inp: str) -> str:
        if inp.isdigit() and 1 <= int(inp) <= 6 and len(inp) == 1:
            self._entered.append(inp)
            if len(self._entered) == 4:
                colors = self._evaluate(self._entered)
                verdi  = colors.count("green")
                gialli = colors.count("yellow")

                if verdi == 4:
                    self._solved = True
                    return "Codice corretto! Accesso nodo."
                else:
                    self._history.append((self._entered[:], colors))

                    if "Decrittazione Automatica" in self._skills:
                        self._entered = [self._secret[0]]
                    else:
                        self._entered = []
                    return f"Codice errato. Feedback: {verdi}V {gialli}G"
            return f"Inserito: {''.join(self._entered)} ({4-len(self._entered)} rimasti)"
        return "Inserisci una cifra da 1 a 6."

    def is_solved(self) -> bool:
        return self._solved

    def __str__(self) -> str:
        filled = "".join(self._entered) + "_" * (4 - len(self._entered))
        return f"NODE  [{filled}]"


class HackingSystem(ISystem):
    """ISystem che gestisce i terminali hackabili sulla mappa.

        Tiene traccia dei terminali già hackerati, genera il puzzle appropriato
        e verifica la soluzione. Solo Echo può interagire con i terminali.
    """
    def __init__(self) -> None:
        self._bus             = None
        self._current_puzzle: IPuzzle | None = None
        self._active_char: str = ""
        self.failed_attempts  = 0
        self.MAX_ATTEMPTS     = 5
        self.is_locked_out    = False
        self._lockout_time: float = 0.0
        self._lockout_terminal = None
        self._hacked_terminals: set = set()
        self.LOCKOUT_DURATION = 60.0

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus

    def cleanup(self) -> None: pass

    def start_hacking(self, puzzle_type: str, character: str) -> str:
        from game.controller.game_manager import GameManager

        if character != "Echo":
            return "Solo Echo può hackare i terminali."

        self.failed_attempts  = 0
        self.is_locked_out    = False
        self._active_char     = character
        self.LOCKOUT_DURATION = 60.0

        gs = GameManager.get_instance()
        echo = gs.Echo
        unlocked_skills = []
        if echo and hasattr(echo, 'skill_wheel'):
            unlocked_skills = [s.name for s in echo.skill_wheel.get_available_skills(echo.stats.tech_points)]

        if puzzle_type in ("slot", "pipe"):
            self._current_puzzle = PipePuzzle(unlocked_skills)
            self.MAX_ATTEMPTS = 5
        elif puzzle_type == "radar":
            self._current_puzzle = RadarPuzzle(unlocked_skills)
            self.MAX_ATTEMPTS = 3
        elif puzzle_type == "node":
            self._current_puzzle = NodePuzzle(unlocked_skills)
            self.MAX_ATTEMPTS = 10
        else:
            self._current_puzzle = PipePuzzle(unlocked_skills)
            self.MAX_ATTEMPTS = 5

        if "Hacking Veloce" in unlocked_skills:
            self.MAX_ATTEMPTS += 3
            self.LOCKOUT_DURATION = 30.0

        return "ok"

    def mark_hacked(self, terminal) -> None:
        """Segna un terminale come già violato con successo.
        Al primo terminale hackerato con successo, sblocca automaticamente
        'Hacking Veloce' per Echo abbassando il suo unlock_tech a 0.
        """
        if terminal is not None:
            self._hacked_terminals.add(tuple(terminal) if not isinstance(terminal, tuple) else terminal)
        if len(self._hacked_terminals) == 1:
            try:
                from game.controller.game_manager import GameManager
                gs = GameManager.get_instance()
                if gs.Echo and hasattr(gs.Echo, 'skill_wheel'):
                    node = gs.Echo.skill_wheel.get_skill("Hacking Veloce")
                    if node:
                        node.unlock_tech = 0
            except Exception:
                pass

    def to_dict(self) -> dict:
        """Serializza lo stato persistente dell'HackingSystem."""
        return {
            "hacked_terminals": [list(t) for t in self._hacked_terminals],
        }

    def restore_from_dict(self, d: dict) -> None:
        """Ripristina lo stato dell'HackingSystem da un dict serializzato."""
        self._hacked_terminals = set(
            tuple(t) for t in d.get("hacked_terminals", [])
        )
        self._current_puzzle  = None
        self._active_char     = ""
        self.failed_attempts  = 0
        self.is_locked_out    = False
        self._lockout_time    = 0.0
        self._lockout_terminal = None

        if self._hacked_terminals:
            try:
                from game.controller.game_manager import GameManager
                gs = GameManager.get_instance()
                if gs.Echo and hasattr(gs.Echo, 'skill_wheel'):
                    node = gs.Echo.skill_wheel.get_skill("Hacking Veloce")
                    if node:
                        node.unlock_tech = 0
            except Exception:
                pass

    def can_hack(self, terminal) -> tuple[bool, str]:
        """
        Restituisce (True, "") se il terminale è hackabile,
        oppure (False, messaggio) con il motivo per cui non lo è.
        """
        import time
        key = tuple(terminal) if not isinstance(terminal, tuple) else terminal

        if key in self._hacked_terminals:
            return False, "Terminale già violato. Sistema inaccessibile."

        if self._lockout_terminal == key and self.is_locked_out:
            elapsed = time.monotonic() - self._lockout_time
            remaining = self.LOCKOUT_DURATION - elapsed
            if remaining > 0:
                secs = int(remaining) + 1
                return False, f"SISTEMA BLOCCATO — Riprova tra {secs}s."
            else:
                self.is_locked_out = False
                self._lockout_terminal = None

        return True, ""

    def submit_input(self, inp: str) -> str:
        if self.is_locked_out or not self._current_puzzle:
            return "Sistema bloccato."

        result = self._current_puzzle.submit(inp)

        if not self._current_puzzle.is_solved():
            if any(trigger in result for trigger in ["errato", "Ping:", "Nodo ruotato"]):
                self.failed_attempts += 1
                if self.failed_attempts >= self.MAX_ATTEMPTS:
                    import time
                    self.is_locked_out = True
                    self._lockout_time = time.monotonic()
                    from game.controller.game_manager import GameManager
                    gs = GameManager.get_instance()
                    self._lockout_terminal = getattr(gs, "active_terminal", None)
                    return result + " -> LOCKOUT!"
        return result

    def force_lockout(self) -> str:
        """Forza il blocco immediato del terminale a seguito di una disconnessione (ESC)."""
        import time
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()

        self.failed_attempts = self.MAX_ATTEMPTS
        self.is_locked_out = True
        self._lockout_time = time.monotonic()
        self._lockout_terminal = getattr(gs, "active_terminal", None)

        return "Disconnessione anomala -> LOCKOUT!"