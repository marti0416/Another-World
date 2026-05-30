"""
skill_wheel.py — Ruota delle skill del personaggio (pattern Iterator GoF).

Struttura
---------
- ``SkillNode``          : nodo singolo con nome, cooldown, tech cost e success rate.
- ``SkillWheelIterator`` : ConcreteIterator GoF con supporto a filtri opzionali.
- ``SkillWheel``         : ConcreteAggregate GoF che espone tre modalità di iterazione.

Pattern utilizzati
------------------
- **Iterator GoF** — ``SkillWheel.__iter__()`` restituisce un ``SkillWheelIterator``;
  i metodi ``iter_available()`` e ``iter_combat()`` restituiscono Iterator filtrati.
  I metodi ``get_available_skills()`` e ``get_combat_skills()`` sono mantenuti
  per retrocompatibilità e materializzano l'iterazione in una lista.
"""

from __future__ import annotations
import random
from typing import Callable, Iterator


# ---------------------------------------------------------------------------
# Nodo skill
# ---------------------------------------------------------------------------

class SkillNode:
    """Nodo singolo nella ruota delle skill del personaggio.

    Ogni nodo rappresenta un'abilità con la propria probabilità di successo,
    cooldown massimo, costo in tech points per sbloccarsi e flag di tipo
    (combattimento vs esplorazione).

    Args:
        name:         Nome visualizzato dell'abilità.
        success_rate: Probabilità di successo all'uso (0.0 – 1.0, default 0.85).
        cooldown:     Turni di ricarica dopo l'uso (0 = nessun cooldown).
        unlock_tech:  Tech points necessari per sbloccare l'abilità.
        is_combat:    Se ``True``, l'abilità è usabile in battaglia;
                      se ``False``, è un'abilità di esplorazione/crafting.
    """

    def __init__(self, name: str, success_rate: float = 0.85,
                 cooldown: int = 0, unlock_tech: int = 0,
                 is_combat: bool = True) -> None:
        self.name             = name
        self.success_rate     = success_rate
        self.max_cooldown     = cooldown
        self.current_cooldown = 0         # Turni rimanenti prima che possa essere riusata
        self.unlock_tech      = unlock_tech
        self.is_combat        = is_combat

    def is_available(self, tech_points: int) -> bool:
        """Verifica se l'abilità è sbloccata e non in cooldown.

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            ``True`` se il personaggio ha abbastanza tech points e il cooldown è 0.
        """
        return tech_points >= self.unlock_tech and self.current_cooldown <= 0

    def is_unlocked(self, tech_points: int) -> bool:
        """Verifica solo se l'abilità è sbloccata, ignorando il cooldown.

        Utile per mostrare le abilità nell'UI della ruota (sbloccate ma in ricarica).

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            ``True`` se il personaggio ha abbastanza tech points.
        """
        return tech_points >= self.unlock_tech

    def attempt_use(self) -> bool:
        """Tenta di usare l'abilità: controlla il cooldown, applica la probabilità di successo.

        Se il cooldown è > 0, l'abilità non può essere usata.
        In caso di uso riuscito, imposta il cooldown al valore massimo.

        Returns:
            ``True`` se l'abilità ha avuto successo, ``False`` se era in cooldown
            o se il tiro di dado è fallito.
        """
        if self.current_cooldown > 0:
            return False
        self.current_cooldown = self.max_cooldown
        return random.random() <= self.success_rate

    def __repr__(self) -> str:
        return f"SkillNode({self.name!r}, combat={self.is_combat}, cd={self.current_cooldown}/{self.max_cooldown})"


# ---------------------------------------------------------------------------
# ConcreteIterator GoF
# ---------------------------------------------------------------------------

class SkillWheelIterator:
    """ConcreteIterator GoF per ``SkillWheel``.

    Attraversa la collezione di ``SkillNode`` applicando un filtro opzionale.
    Il client non conosce né accede alla struttura interna (``_skills: list``).

    Uso diretto::

        it = SkillWheelIterator(wheel)
        for skill in it: ...

    Uso con filtro::

        it = SkillWheelIterator(wheel, filter_fn=lambda s: s.is_combat)
        for skill in it: ...

    I shortcut ``wheel.iter_available(tp)`` e ``wheel.iter_combat(tp)`` costruiscono
    automaticamente il ``filter_fn`` corretto.

    Args:
        wheel:     La ``SkillWheel`` da attraversare.
        filter_fn: Funzione di filtro opzionale; se ``None``, include tutti i nodi.
    """

    def __init__(
        self,
        wheel: "SkillWheel",
        filter_fn: Callable[[SkillNode], bool] | None = None,
    ) -> None:
        # Materializza subito la lista filtrata per efficienza e stabilità
        self._skills = [
            s for s in wheel._skills
            if filter_fn is None or filter_fn(s)
        ]
        self._index = 0

    def __iter__(self) -> "SkillWheelIterator":
        """Restituisce se stesso come Iterator (protocollo Python)."""
        return self

    def __next__(self) -> SkillNode:
        """Restituisce il prossimo nodo, o solleva ``StopIteration`` se esaurito."""
        if self._index >= len(self._skills):
            raise StopIteration
        node = self._skills[self._index]
        self._index += 1
        return node

    def __len__(self) -> int:
        """Numero di skill nel traversal filtrato."""
        return len(self._skills)

    def to_list(self) -> list[SkillNode]:
        """Materializza l'iterazione in una lista (retrocompatibilità).

        Returns:
            Lista di tutti i ``SkillNode`` che superano il filtro.
        """
        return list(self._skills)


# ---------------------------------------------------------------------------
# ConcreteAggregate GoF
# ---------------------------------------------------------------------------

class SkillWheel:
    """ConcreteAggregate GoF: contenitore delle skill di un personaggio.

    Espone tre modalità di iterazione tramite Iterator GoF:

    - ``__iter__()``         → tutte le skill (senza filtro).
    - ``iter_available(tp)`` → skill sbloccate e non in cooldown.
    - ``iter_combat(tp)``    → skill sbloccate, non in cooldown, usabili in battaglia.

    I metodi ``get_available_skills()`` e ``get_combat_skills()`` sono mantenuti
    per retrocompatibilità e delegano internamente all'Iterator.
    """

    def __init__(self) -> None:
        self._skills: list[SkillNode] = []

    def __iter__(self) -> SkillWheelIterator:
        """Iterator GoF: restituisce un Iterator su tutte le skill (senza filtri)."""
        return SkillWheelIterator(self)

    def iter_available(self, tech_points: int = 0) -> SkillWheelIterator:
        """Restituisce un Iterator filtrato sulle skill sbloccate e non in cooldown.

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            ``SkillWheelIterator`` che include solo le skill disponibili.
        """
        return SkillWheelIterator(
            self,
            filter_fn=lambda s: s.is_available(tech_points),
        )

    def iter_combat(self, tech_points: int = 0) -> SkillWheelIterator:
        """Restituisce un Iterator filtrato sulle skill da battaglia disponibili.

        Include solo skill sbloccate, non in cooldown e con ``is_combat = True``.

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            ``SkillWheelIterator`` che include solo le skill da battaglia.
        """
        return SkillWheelIterator(
            self,
            filter_fn=lambda s: s.is_available(tech_points) and s.is_combat,
        )

    def add_skill(self, skill: SkillNode) -> None:
        """Aggiunge un nodo skill alla ruota.

        Args:
            skill: Il ``SkillNode`` da aggiungere.
        """
        self._skills.append(skill)

    def get_skill(self, name: str) -> SkillNode | None:
        """Ricerca un nodo skill per nome.

        Args:
            name: Nome esatto dell'abilità da cercare.

        Returns:
            Il ``SkillNode`` trovato, oppure ``None`` se non presente.
        """
        return next((s for s in self._skills if s.name == name), None)

    def tick(self) -> None:
        """Decrementa di 1 il cooldown di tutte le abilità in ricarica.

        Da chiamare una volta per turno di battaglia dopo che tutte le mosse
        sono state risolte.
        """
        for s in self._skills:
            if s.current_cooldown > 0:
                s.current_cooldown -= 1

    def get_available_skills(self, tech_points: int = 0) -> list[SkillNode]:
        """Restituisce le skill sbloccate come lista (retrocompatibilità).

        Preferire ``iter_available()`` per il traversal diretto senza materializzazione.

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            Lista di ``SkillNode`` disponibili.
        """
        return self.iter_available(tech_points).to_list()

    def get_combat_skills(self, tech_points: int = 0) -> list[SkillNode]:
        """Restituisce le skill da battaglia come lista (retrocompatibilità).

        Preferire ``iter_combat()`` per il traversal diretto senza materializzazione.

        Args:
            tech_points: Tech points correnti del personaggio.

        Returns:
            Lista di ``SkillNode`` da battaglia disponibili.
        """
        return self.iter_combat(tech_points).to_list()

    def to_dict(self) -> list:
        """Serializza i cooldown correnti di tutte le skill per il salvataggio.

        Returns:
            Lista di dict con ``name`` e ``current_cooldown`` per ogni skill.
        """
        return [
            {"name": s.name, "current_cooldown": s.current_cooldown}
            for s in self
        ]

    def restore_from_dict(self, data: list) -> None:
        """Ripristina i cooldown delle skill da un dict serializzato.

        Ignora silenziosamente i nomi non presenti nella ruota (es. skill
        rimosse in aggiornamenti successivi al salvataggio).

        Args:
            data: Lista prodotta da ``to_dict()``.
        """
        cd_map = {entry["name"]: entry["current_cooldown"] for entry in data}
        for s in self:
            if s.name in cd_map:
                s.current_cooldown = cd_map[s.name]

    def __repr__(self) -> str:
        return f"SkillWheel({[s.name for s in self]})"
