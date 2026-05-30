"""
stats.py — Statistiche del personaggio e gestione degli effetti di stato.

Questo modulo definisce:
- ``StatusEffect``: un effetto di stato temporaneo (veleno, fuoco, stordimento, ecc.)
- ``Stats``: il contenitore principale delle statistiche di un personaggio,
  che integra il pattern Decorator GoF per il calcolo dinamico di danno e difesa.

Design note
-----------
``Stats`` non calcola mai danno/difesa direttamente: delega sempre alla catena
``_decorator_chain`` costruita da ``build_decorator_chain()`` in
``character_decorator.py``. Ogni volta che ``_effects`` cambia, la catena
viene ricostruita automaticamente.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from game.model.skill_wheel import SkillNode, SkillWheel

__all__ = [
    "StatusEffect", "Stats",
    "SkillNode", "SkillWheel",
]


@dataclass
class StatusEffect:
    """Effetto di stato temporaneo applicato a un personaggio o nemico.

    Gli effetti vengono processati ogni turno da ``Stats.process_turn_effects()``.
    Alcuni effetti (Stordito da Esca, Confusione, Shock) causano anche lo skip
    del turno: vengono gestiti separatamente da ``Stats.has_skip_effect()``.

    Attributes:
        name:     Identificatore testuale dell'effetto (es. "Corrosione", "Fuoco").
        duration: Numero di turni rimanenti prima che l'effetto scada.
        delta_hp: Variazione di HP applicata ogni turno (negativo = danno nel tempo,
                  positivo = rigenerazione).
    """
    name:     str
    duration: int
    delta_hp: int = 0


class Stats:
    """Statistiche di combattimento di un personaggio o nemico.

    Gestisce HP, ATK, difesa, livello, XP, tech points e gli effetti di stato
    attivi. Il calcolo effettivo di danno e difesa è delegato alla catena
    Decorator GoF (``_decorator_chain``), che viene ricostruita ogni volta
    che la lista ``_effects`` cambia.

    Il pattern Decorator permette di sovrapporre modificatori (Corrosione,
    Fuoco, Shock, ecc.) senza modificare questa classe.

    Args:
        hp:      Punti vita massimi iniziali.
        atk:     Valore di attacco base.
        defense: Valore di difesa base.
    """

    def __init__(self, hp: int, atk: int, defense: int) -> None:
        self.max_hp  = hp
        self.hp      = hp
        self.atk     = atk
        self.defense = defense
        self.xp      = 0
        self.level   = 1
        self._effects: list[StatusEffect] = []
        self.tech_points = 0

        # Costruisce la catena Decorator iniziale (nessun effetto attivo).
        self._decorator_chain = self._build_chain()

    def _build_chain(self):
        """Ricostruisce la catena Decorator GoF dagli effetti attivi.

        Deve essere chiamato ogni volta che ``_effects`` viene modificato
        (aggiunta, rimozione o scadenza di un effetto).

        Returns:
            L'oggetto ``ICharacterComponent`` più esterno della catena,
            pronto per ricevere chiamate a ``take_damage()`` e ``effective_defense()``.
        """
        from game.model.character_decorator import build_decorator_chain
        return build_decorator_chain(self, self._effects)

    @property
    def forza(self) -> int:
        """Forza fisica: derivata da ATK con un moltiplicatore minore.

        Rivet (ATK 12) → forza ~9; Echo (ATK 8) → forza ~6.
        Usata per sfondare porte blindate e in alcune interazioni ambientali.

        Returns:
            Valore intero di forza calcolato come ``int(atk * 0.75) + (level - 1)``.
        """
        return int(self.atk * 0.75) + (self.level - 1)

    def take_damage(self, raw: int) -> int:
        """Applica danno grezzo attraverso la catena Decorator.

        La catena applica in sequenza tutti i modificatori attivi
        (vulnerabilità, amplificazione, ecc.) prima di sottrarre la difesa.
        Il danno effettivo viene sottratto dagli HP all'interno della catena.

        Args:
            raw: Danno grezzo prima dell'applicazione dei modificatori.

        Returns:
            Danno effettivo subito dopo tutti i modificatori e la difesa.
        """
        return self._decorator_chain.take_damage(raw)

    def effective_defense(self) -> int:
        """Restituisce la difesa effettiva dopo tutti i Decorator attivi.

        Returns:
            Valore di difesa corrente, potenzialmente ridotto da effetti come
            Corrosione, Mucillagine o Shock.
        """
        return self._decorator_chain.effective_defense()

    def heal(self, amount: int) -> int:
        """Cura il personaggio, senza superare i punti vita massimi.

        Args:
            amount: Quantità di HP da ripristinare.

        Returns:
            HP effettivamente guadagnati (può essere inferiore ad ``amount``
            se il personaggio era quasi a pieno).
        """
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def gain_xp(self, amount: int, healed_in_battle: bool = False) -> list[str]:
        """Aggiunge XP e gestisce i level-up automatici.

        Al level-up: ATK+1, DEF+1. Con una probabilità crescente, il
        personaggio guadagna anche tech points (da 1 a 3).
        Se il personaggio si è curato durante la battaglia, subisce un
        lieve malus del 20% sugli XP guadagnati.

        Args:
            amount:           XP da aggiungere prima di eventuali malus.
            healed_in_battle: Se ``True``, gli XP vengono ridotti dell'20%.

        Returns:
            Lista di stringhe con i messaggi di level-up (una per livello
            guadagnato). Lista vuota se non si è avanzato di livello.
        """
        import random
        if healed_in_battle:
            amount = int(amount * 0.80)
        messages: list[str] = []
        self.xp += amount
        threshold = self.level * 100
        while self.xp >= threshold:
            self.xp -= threshold
            self.level += 1
            self.atk += 1
            self.defense += 1
            tech_chance = min(0.95, 0.50 + (self.level - 1) * 0.10)
            tech_gained = 0
            if random.random() < tech_chance:
                tech_gained = random.randint(1, 3)
                self.tech_points += tech_gained
            threshold = self.level * 100
            tech_str = f"  TECH+{tech_gained}" if tech_gained > 0 else ""
            messages.append(f"LEVEL UP! Livello {self.level}  ATK+1  DEF+1{tech_str}")
        return messages

    def gain_tech_points(self, amount: int) -> None:
        """Aggiunge tech points direttamente, senza passare per il sistema XP.

        Usato da crafting, hacking e uso di alcune abilità in battaglia.

        Args:
            amount: Numero di tech points da aggiungere.
        """
        self.tech_points += amount

    def add_effect(self, effect: StatusEffect) -> None:
        """Aggiunge un effetto di stato e ricostruisce la catena Decorator.

        Args:
            effect: L'effetto da applicare al personaggio.
        """
        self._effects.append(effect)
        self._decorator_chain = self._build_chain()

    def process_turn_effects(self) -> None:
        """Processa tutti gli effetti attivi a fine turno.

        Applica il ``delta_hp`` di ogni effetto, decrementa la loro durata
        e rimuove gli effetti scaduti (``duration <= 0``).
        Ricostruisce la catena Decorator dopo ogni chiamata.
        """
        remaining = []
        for eff in self._effects:
            self.hp = max(0, self.hp + eff.delta_hp)
            eff.duration -= 1
            if eff.duration > 0:
                remaining.append(eff)
        self._effects = remaining
        self._decorator_chain = self._build_chain()

    def has_skip_effect(self) -> bool:
        """Controlla e consuma gli effetti che causano lo skip del turno.

        Effetti riconosciuti: "Stordito da Esca", "Confusione", "Shock".
        Se uno di questi è presente, la sua durata viene decrementata e,
        se scade, viene rimosso da ``_effects``.

        Returns:
            ``True`` se il personaggio deve saltare il turno, ``False`` altrimenti.
        """
        SKIP_NAMES = ("Stordito da Esca", "Confusione", "Shock")
        triggered = False
        remaining = []
        for eff in self._effects:
            if eff.name in SKIP_NAMES:
                triggered = True
                eff.duration -= 1
                if eff.duration > 0:
                    remaining.append(eff)
            else:
                remaining.append(eff)
        self._effects = remaining
        self._decorator_chain = self._build_chain()
        return triggered

    def to_dict(self) -> dict:
        """Serializza tutte le stats in un dict JSON-friendly per il salvataggio.

        Returns:
            Dizionario con hp, max_hp, atk, defense, xp, level, tech_points
            e la lista degli effetti attivi.
        """
        return {
            "hp":          self.hp,
            "max_hp":      self.max_hp,
            "atk":         self.atk,
            "defense":     self.defense,
            "xp":          self.xp,
            "level":       self.level,
            "tech_points": self.tech_points,
            "effects":  [
                {"name": e.name, "duration": e.duration, "delta_hp": e.delta_hp}
                for e in self._effects
            ],
        }

    def restore_from_dict(self, d: dict) -> None:
        """Ripristina le stats da un dict serializzato (caricamento salvataggio).

        Ricostruisce anche gli effetti di stato attivi e la catena Decorator.

        Args:
            d: Dizionario prodotto da ``to_dict()``.
        """
        self.hp          = d.get("hp",          self.max_hp)
        self.max_hp      = d.get("max_hp",       self.max_hp)
        self.atk         = d.get("atk",          self.atk)
        self.defense     = d.get("defense",       self.defense)
        self.xp          = d.get("xp",            0)
        self.level       = d.get("level",         1)
        self.tech_points = d.get("tech_points",   0)
        self._effects = [
            StatusEffect(e["name"], e["duration"], e.get("delta_hp", 0))
            for e in d.get("effects", [])
        ]
        self._decorator_chain = self._build_chain()
