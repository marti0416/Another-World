"""
enemy.py — Modello dei nemici e Factory Method GoF per la loro creazione.

Struttura
---------
- ``Enemy``            : entità nemica con logica decisionale delegata a IBattleAI.
- ``EnemyCreator``     : Creator astratto GoF (Factory Method).
- ``*Creator``         : ConcreteCreator per ogni tipo di nemico.
- ``EnemyFactory``     : Facade di retrocompatibilità che delega ai ConcreteCreator.

Pattern utilizzati
------------------
- **Strategy GoF** — la logica di battaglia è delegata a ``IBattleAI`` (``ai_behaviours.py``).
- **Factory Method GoF** — ogni ``EnemyCreator`` espone ``create_enemy()`` e ``spawn()``.
- **Abstract Factory** — ``create_npc_fazione()`` delega a ``FactionAssembler``
  (in ``faction_factory.py``) che usa la ConcreteFactory corretta.
"""

from __future__ import annotations

import random
from game.model.stats import Stats

from game.model.ai_behaviours import (
    CorazzatoAI,
    IBattleAI,
    InfettoAI,
    MeatGiantAI,
    OrdaAI,
    DannatiAI,
    ErrantiAI,
    RazziatoriAI,
    SolidaliAI,
)


# ---------------------------------------------------------------------------
# Prodotto — Enemy
# ---------------------------------------------------------------------------

class Enemy:
    """Entità nemica del gioco.

    Usa il pattern Strategy: la logica decisionale in battaglia è completamente
    delegata all'oggetto ``IBattleAI`` passato al costruttore (o impostato
    successivamente). In assenza di strategy, viene usata una logica legacy
    basata su ``ai_type``.

    Args:
        name:        Nome del nemico visualizzato in battaglia.
        stats:       Statistiche di combattimento (HP, ATK, difesa).
        faction_name: Nome della fazione di appartenenza (es. "zombie", "Dannati").
        ai_type:     Tipo di AI legacy usato se nessuna strategy è impostata.
        ai_strategy: Oggetto ``IBattleAI`` con la logica decisionale concreta.
        sprite_key:  Chiave per il caricamento dello sprite nell'AssetLoader.
    """

    def __init__(self, name: str, stats: Stats,
                 faction_name: str = "infetti",
                 ai_type: str = "basic",
                 ai_strategy: IBattleAI | None = None,
                 sprite_key: str | None = None) -> None:
        self.name         = name
        self.stats        = stats
        self.faction_name = faction_name
        self.ai_type      = ai_type
        self.sprite_key   = sprite_key

        self._ai_strategy: IBattleAI | None = ai_strategy

        # Flag e contatori usati dalle AI (impostati dinamicamente durante la battaglia)
        self._noise_source:   object | None = None
        self._viral_stacks:   int           = 0
        self._commander:      "Enemy | None"= None
        self._last_killed:    object | None = None
        self._triggered:      bool          = False
        self._turn_counter:   int           = 0
        self.can_reanimate:   bool          = False

    def is_alive(self) -> bool:
        """Restituisce ``True`` se il nemico ha HP > 0."""
        return self.stats.hp > 0

    def decide_battle_move(self, targets: list) -> dict:
        """Determina la mossa da eseguire questo turno.

        Se è impostata una ``IBattleAI`` strategy, la delega interamente ad essa.
        Altrimenti usa la logica legacy basata su ``ai_type`` per retrocompatibilità.

        Args:
            targets: Lista di tutti i possibili bersagli (vivi o meno).

        Returns:
            Dizionario che descrive l'azione scelta (vedi ``ai_behaviours.py``).
        """
        alive = [t for t in targets if t.is_alive()]

        # Delega alla Strategy se disponibile
        if self._ai_strategy is not None:
            return self._ai_strategy.decide_move(self, targets)

        # Logica legacy per retrocompatibilità
        if not alive:
            return {"action": "idle"}

        if self.ai_type == "basic":
            return {"action": "attack",
                    "target": random.choice(alive),
                    "power":  self.stats.atk}

        elif self.ai_type == "hunter":
            # Caccia il bersaglio con meno HP
            target = min(alive, key=lambda t: t.stats.hp)
            return {"action": "attack", "target": target,
                    "power": int(self.stats.atk * 1.2)}

        elif self.ai_type == "tank":
            target = random.choice(alive)
            return {"action": "attack", "target": target,
                    "power": int(self.stats.atk * 0.8)}

        elif self.ai_type == "boss":
            # 30% di probabilità di attacco speciale sul bersaglio più debole
            if random.random() < 0.3:
                target = min(alive, key=lambda t: t.stats.hp)
                return {"action": "special", "target": target,
                        "power": int(self.stats.atk * 1.5)}
            return {"action": "attack",
                    "target": random.choice(alive),
                    "power": self.stats.atk}

        # Fallback generico
        return {"action": "attack",
                "target": random.choice(alive),
                "power":  self.stats.atk}

    def __repr__(self) -> str:
        return f"Enemy({self.name}, HP={self.stats.hp}/{self.stats.max_hp})"


# ---------------------------------------------------------------------------
# Creator astratto — Factory Method GoF
# ---------------------------------------------------------------------------

from abc import ABC as _ABC, abstractmethod as _abstractmethod


class EnemyCreator(_ABC):
    """Creator astratto GoF (Factory Method).

    Definisce il factory method ``create_enemy()`` che ogni sottoclasse
    concreta sovrascrive per istanziare lo specifico tipo di ``Enemy``.
    Il metodo template ``spawn()`` chiama il factory method e può essere
    esteso per logica di post-creazione comune.
    """

    @_abstractmethod
    def create_enemy(self, **kwargs) -> Enemy:
        """Factory Method: istanzia e restituisce il prodotto concreto.

        Args:
            **kwargs: Parametri opzionali specifici del ConcreteCreator
                      (es. ``nome``, ``commander``).

        Returns:
            Nuovo oggetto ``Enemy`` configurato.
        """
        ...

    def spawn(self, **kwargs) -> Enemy:
        """Operazione pubblica: chiama il factory method e restituisce l'Enemy.

        Args:
            **kwargs: Inoltrati a ``create_enemy()``.

        Returns:
            Nuovo oggetto ``Enemy`` pronto per essere usato in battaglia.
        """
        return self.create_enemy(**kwargs)


# ---------------------------------------------------------------------------
# ConcreteCreator — uno per ogni tipo di nemico
# ---------------------------------------------------------------------------

class InfettoCreator(EnemyCreator):
    """Creator per l'Infetto (zombie base con possibilità di rianimazione)."""

    def create_enemy(self, **kwargs) -> Enemy:
        e = Enemy("Infetto", Stats(hp=100, atk=12, defense=2),
                  faction_name="zombie", ai_strategy=InfettoAI(), sprite_key="Infetto")
        e.respawn_chance = 0.25   # Probabilità di rianimarsi dopo la morte
        return e


class CorazzatoCreator(EnemyCreator):
    """Creator per il Corazzato (zombie con alta difesa e possibilità di evocare)."""

    def create_enemy(self, **kwargs) -> Enemy:
        return Enemy("Corazzato", Stats(hp=150, atk=15, defense=20),
                     faction_name="zombie", ai_strategy=CorazzatoAI(), sprite_key="Corazzato")


class OrdaCreator(EnemyCreator):
    """Creator per l'Orda (gruppo di zombie con attacco di massa).

    Args (via kwargs):
        commander: ``Enemy`` che comanda questa Orda (opzionale). Se presente,
                   l'Orda ottiene il flag ``is_taunting``.
    """

    def create_enemy(self, commander: Enemy = None, **kwargs) -> Enemy:
        e = Enemy("Orda", Stats(hp=100, atk=12, defense=1),
                  faction_name="zombie", ai_strategy=OrdaAI(), sprite_key="Orda")
        e._commander  = commander
        e.is_taunting = True if commander else False
        return e


class MeatGiantCreator(EnemyCreator):
    """Creator per il Gigante di Carne (boss zombie con resistenza alle armi leggere)."""

    def create_enemy(self, **kwargs) -> Enemy:
        e = Enemy("Gigante di Carne", Stats(hp=200, atk=15, defense=10),
                  faction_name="zombie", ai_strategy=MeatGiantAI(), sprite_key="Gigante")
        e.light_weapon_resist = 0.50  # Riduce del 50% il danno da armi leggere
        return e


class DannatiCreator(EnemyCreator):
    """Creator per i Dannati (fazione umana aggressiva).

    Args (via kwargs):
        nome: Nome personalizzato del membro della fazione (default "Dannato").
    """

    def create_enemy(self, nome: str = "Dannato", **kwargs) -> Enemy:
        return Enemy(nome, Stats(hp=100, atk=20, defense=5),
                     faction_name="Dannati", ai_strategy=DannatiAI(), sprite_key=nome)


class RazziatoriCreator(EnemyCreator):
    """Creator per i Razziatori (fazione umana con alta difesa e armi da taglio).

    Args (via kwargs):
        nome: Nome personalizzato del membro della fazione (default "Razziatore").
    """

    def create_enemy(self, nome: str = "Razziatore", **kwargs) -> Enemy:
        return Enemy(nome, Stats(hp=100, atk=15, defense=18),
                     faction_name="Razziatori", ai_strategy=RazziatoriAI(), sprite_key=nome)


class ErrantiCreator(EnemyCreator):
    """Creator per gli Erranti (fazione umana con sostanze chimiche).

    Args (via kwargs):
        nome: Nome personalizzato del membro della fazione (default "Errante").
    """

    def create_enemy(self, nome: str = "Errante", **kwargs) -> Enemy:
        return Enemy(nome, Stats(hp=100, atk=15, defense=8),
                     faction_name="Erranti", ai_strategy=ErrantiAI(), sprite_key=nome)


class SolidaliCreator(EnemyCreator):
    """Creator per i Solidali (fazione non ostile, combatte solo per difesa).

    Args (via kwargs):
        nome: Nome personalizzato del membro della fazione (default "Solidale").
    """

    def create_enemy(self, nome: str = "Solidale", **kwargs) -> Enemy:
        return Enemy(nome, Stats(hp=100, atk=5, defense=4),
                     faction_name="Solidali", ai_strategy=SolidaliAI(), sprite_key=nome)


# ---------------------------------------------------------------------------
# Facade di retrocompatibilità
# ---------------------------------------------------------------------------

class EnemyFactory:
    """Facade di retrocompatibilità — API pubblica invariata.

    Delega internamente ai ConcreteCreator GoF; tutto il codice esistente
    che chiama ``EnemyFactory.create_*()`` continua a funzionare senza modifiche.
    """

    @staticmethod
    def create_infetto() -> Enemy:
        """Crea un Infetto con logica AI e statistiche predefinite."""
        return InfettoCreator().spawn()

    @staticmethod
    def create_corazzato() -> Enemy:
        """Crea un Corazzato con logica AI e statistiche predefinite."""
        return CorazzatoCreator().spawn()

    @staticmethod
    def create_orda(commander: Enemy = None) -> Enemy:
        """Crea un'Orda, opzionalmente comandata da un nemico specifico.

        Args:
            commander: Nemico che comanda l'Orda (aggiunge il flag ``is_taunting``).
        """
        return OrdaCreator().spawn(commander=commander)

    @staticmethod
    def create_meat_giant() -> Enemy:
        """Crea il Gigante di Carne con resistenza alle armi leggere."""
        return MeatGiantCreator().spawn()

    @staticmethod
    def create_npc_fazione(Nome: str, nome_fazione: str) -> Enemy:
        """Crea un nemico appartenente alla fazione indicata.

        Usa l'**Abstract Factory** GoF: delega a ``FactionAssembler.build_enemy()``
        che seleziona e usa la ConcreteFactory corretta dal registry di
        ``faction_factory.py``. L'API pubblica rimane invariata.

        Args:
            Nome:         Nome del membro della fazione (es. "Razziatore Alpha").
            nome_fazione: Nome della fazione (es. "Razziatori", "Erranti").

        Returns:
            Oggetto ``Enemy`` configurato per la fazione specificata.
        """
        from game.model.faction_factory import FactionAssembler
        return FactionAssembler.build_enemy(nome_fazione, Nome)
