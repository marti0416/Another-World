"""
character_decorator.py — Implementazione del pattern Decorator GoF per il calcolo
di danno e difesa.

Struttura
---------
- ``ICharacterComponent`` (Component astratto): interfaccia comune.
- ``StatsComponent``       (ConcreteComponent): adatta ``Stats`` all'interfaccia.
- ``CharacterDecorator``   (Decorator astratto): mantiene il riferimento al wrapped.
- ``*Decorator``           (ConcreteDecorator): uno per ogni StatusEffect supportato.
- ``build_decorator_chain``: factory function che costruisce la catena completa.

La catena viene ricostruita da ``Stats._build_chain()`` ogni volta che
``Stats._effects`` cambia.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.model.stats import Stats


# ---------------------------------------------------------------------------
# Component astratto
# ---------------------------------------------------------------------------

class ICharacterComponent(ABC):
    """Interfaccia comune a ConcreteComponent e Decorator (pattern Decorator GoF).

    Definisce le due operazioni che la catena può modificare:
    il calcolo del danno e il calcolo della difesa effettiva.
    """

    @abstractmethod
    def take_damage(self, raw: int) -> int:
        """Calcola e applica il danno. Restituisce il danno effettivo subito."""
        ...

    @abstractmethod
    def effective_defense(self) -> int:
        """Restituisce la difesa effettiva dopo tutti i modificatori attivi."""
        ...


# ---------------------------------------------------------------------------
# ConcreteComponent
# ---------------------------------------------------------------------------

class StatsComponent(ICharacterComponent):
    """ConcreteComponent GoF: adatta ``Stats`` all'interfaccia ``ICharacterComponent``.

    Incapsula la logica base di danno e difesa senza alcun effetto attivo.
    È il nodo più interno della catena Decorator: tutti i Decorator wrappano
    (direttamente o indirettamente) questo oggetto.

    Args:
        stats: L'oggetto ``Stats`` del personaggio da adattare.
    """

    def __init__(self, stats: "Stats") -> None:
        self._stats = stats

    def take_damage(self, raw: int) -> int:
        """Applica il danno base sottraendo la difesa e aggiornando gli HP.

        Args:
            raw: Danno grezzo (già modificato dai Decorator più esterni).

        Returns:
            Danno effettivo subito (minimo 1).
        """
        dmg = max(1, raw - self._stats.defense)
        self._stats.hp = max(0, self._stats.hp - dmg)
        return dmg

    def effective_defense(self) -> int:
        """Restituisce il valore di difesa base del personaggio."""
        return self._stats.defense


# ---------------------------------------------------------------------------
# Decorator astratto
# ---------------------------------------------------------------------------

class CharacterDecorator(ICharacterComponent, ABC):
    """Decorator astratto GoF: mantiene un riferimento al component wrappato.

    Le sottoclassi concrete sovrascrivono solo il metodo che intendono
    modificare (``take_damage`` o ``effective_defense``), delegando
    l'altro al wrapped tramite ``super()``.

    Args:
        wrapped: Il component (o Decorator) da avvolgere.
    """

    def __init__(self, wrapped: ICharacterComponent) -> None:
        self._wrapped = wrapped

    def take_damage(self, raw: int) -> int:
        """Delega al wrapped senza modifiche (override nei ConcreteDecorator)."""
        return self._wrapped.take_damage(raw)

    def effective_defense(self) -> int:
        """Delega al wrapped senza modifiche (override nei ConcreteDecorator)."""
        return self._wrapped.effective_defense()


# ---------------------------------------------------------------------------
# ConcreteDecorator — uno per ogni StatusEffect
# ---------------------------------------------------------------------------

class CorrosioneDecorator(CharacterDecorator):
    """Effetto Corrosione: riduce la difesa del bersaglio di 5 punti.

    Il danno nel tempo (DOT) è già gestito da ``Stats._effects``;
    questo Decorator aggiunge esclusivamente il malus alla difesa.
    """

    DEFENSE_PENALTY: int = 5

    def effective_defense(self) -> int:
        """Riduce la difesa di ``DEFENSE_PENALTY`` (minimo 0)."""
        return max(0, self._wrapped.effective_defense() - self.DEFENSE_PENALTY)


class FuocoDecorator(CharacterDecorator):
    """Effetto Fuoco: amplifica ogni colpo ricevuto di 3 danni grezzi aggiuntivi.

    Il DOT è gestito da ``Stats._effects``; questo Decorator amplifica
    ogni singolo hit in ingresso.
    """

    DAMAGE_AMPLIFY: int = 3

    def take_damage(self, raw: int) -> int:
        """Aggiunge ``DAMAGE_AMPLIFY`` al danno grezzo prima di delegare al wrapped."""
        return self._wrapped.take_damage(raw + self.DAMAGE_AMPLIFY)


class MucillagineDecorator(CharacterDecorator):
    """Effetto Mucillagine aliena: rallenta i movimenti, riducendo la difesa di 3.

    Modella il rallentamento tattico causato dalla sostanza vischiosa.
    """

    DEFENSE_PENALTY: int = 3

    def effective_defense(self) -> int:
        """Riduce la difesa di ``DEFENSE_PENALTY`` (minimo 0)."""
        return max(0, self._wrapped.effective_defense() - self.DEFENSE_PENALTY)


class SoluzionePiranhaDec(CharacterDecorator):
    """Effetto Soluzione Piranha: vulnerabilità crescente in base ai turni attivi.

    Più turni è attivo l'effetto, maggiore è il bonus al danno ricevuto
    (+10 per ogni turno trascorso dall'applicazione).

    Args:
        wrapped:      Il component da avvolgere.
        turns_active: Turni già trascorsi dall'applicazione dell'effetto.
    """

    def __init__(self, wrapped: ICharacterComponent, turns_active: int = 0) -> None:
        super().__init__(wrapped)
        self.turns_active = turns_active

    def take_damage(self, raw: int) -> int:
        """Aggiunge un bonus crescente al danno grezzo (``turns_active * 10``)."""
        bonus = self.turns_active * 10
        return self._wrapped.take_damage(raw + bonus)


class ShockDecorator(CharacterDecorator):
    """Effetto Shock: il personaggio è stordito, la difesa scende a 0.

    Lo skip del turno è gestito da ``Stats.has_skip_effect()``;
    questo Decorator modella l'impatto difensivo dello stordimento.
    """

    def effective_defense(self) -> int:
        """Azzera completamente la difesa del personaggio stordito."""
        return 0


class ConfusioneDecorator(CharacterDecorator):
    """Effetto Confusione: disorientamento tattico, riduce la difesa di 2 punti."""

    DEFENSE_PENALTY: int = 2

    def effective_defense(self) -> int:
        """Riduce la difesa di ``DEFENSE_PENALTY`` (minimo 0)."""
        return max(0, self._wrapped.effective_defense() - self.DEFENSE_PENALTY)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def build_decorator_chain(
    stats: "Stats",
    effects: list,
) -> ICharacterComponent:
    """Costruisce la catena Decorator a partire dalla lista di ``StatusEffect`` attivi.

    La catena creata è: ``StatsComponent → Decorator1 → Decorator2 → … → outermost``.
    Il client (``Stats``) chiama sempre il Decorator più esterno (quello restituito).

    Ogni ``StatusEffect`` attivo nella lista genera il Decorator corrispondente;
    gli effetti non riconosciuti vengono ignorati silenziosamente.

    Chiamato da ``Stats._build_chain()`` ogni volta che ``_effects`` cambia.

    Args:
        stats:   L'oggetto ``Stats`` del personaggio (usato da ``StatsComponent``).
        effects: Lista di ``StatusEffect`` attivi al momento della chiamata.

    Returns:
        L'``ICharacterComponent`` più esterno della catena (da usare come entry point).
    """
    chain: ICharacterComponent = StatsComponent(stats)

    for eff in effects:
        name = eff.name

        if name == "Corrosione":
            chain = CorrosioneDecorator(chain)

        elif name == "Fuoco":
            chain = FuocoDecorator(chain)

        elif name == "Mucillagine":
            chain = MucillagineDecorator(chain)

        elif name == "Soluzione Piranha":
            # turns_active = turni già trascorsi = durata_max - durata_rimanente
            turns_active = max(0, 5 - eff.duration)
            chain = SoluzionePiranhaDec(chain, turns_active=turns_active)

        elif name == "Shock":
            chain = ShockDecorator(chain)

        elif name == "Confusione":
            chain = ConfusioneDecorator(chain)

    return chain
