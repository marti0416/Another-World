"""
character_builder.py — Creazione dei personaggi giocabili tramite pattern Builder GoF.

Struttura
---------
- ``Character``          : il prodotto finale (personaggio con stats, inventario, skill).
- ``ICharacterBuilder``  : interfaccia astratta del Builder GoF.
- ``RivetBuilder``       : ConcreteBuilder per il personaggio Rivet.
- ``EchoBuilder``        : ConcreteBuilder per il personaggio Echo.
- ``CharacterDirector``  : Director GoF che orchestra i passi di costruzione.

Flusso tipico
-------------
    director = CharacterDirector(RivetBuilder())
    rivet    = director.construct()
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from game.model.skill_wheel import SkillNode, SkillWheel
from game.model.stats import Stats
from game.model.item import Inventory


# ---------------------------------------------------------------------------
# Prodotto
# ---------------------------------------------------------------------------

class Character:
    """Personaggio giocabile: prodotto del pattern Builder GoF.

    Aggrega stats, inventario e ruota delle skill. Espone metodi di alto livello
    per la gestione delle armi e lo stato di vita.

    Args:
        name:        Nome del personaggio ("Rivet" o "Echo").
        stats:       Oggetto ``Stats`` con HP, ATK, difesa, ecc.
        inventory:   Inventario iniziale con peso massimo configurato.
        skill_wheel: Ruota delle skill con tutte le abilità pre-caricate.
    """

    def __init__(self, name: str, stats: Stats,
                 inventory: Inventory, skill_wheel: SkillWheel) -> None:
        self.name            = name
        self.stats           = stats
        self.inventory       = inventory
        self.skill_wheel     = skill_wheel
        self.can_hack        = False         # Abilitato solo per Echo
        self.equipped_weapon = None          # Arma attualmente in uso
        self.weapons: list   = []            # Lista di tutte le armi possedute

    def is_alive(self) -> bool:
        """Restituisce ``True`` se il personaggio ha HP > 0."""
        return self.stats.hp > 0

    def equip_weapon(self, weapon) -> tuple:
        """Equipaggia un'arma dopo validazione tramite ``WeaponValidator``.

        Args:
            weapon: Oggetto arma da equipaggiare.

        Returns:
            Tupla ``(ok: bool, messaggio: str)``.
            ``ok`` è ``False`` se l'arma non è compatibile con questo personaggio.
        """
        from game.model.weapon_system import WeaponValidator
        ok, reason = WeaponValidator.can_use(self.name, weapon)
        if not ok:
            return False, reason
        self.equipped_weapon = weapon
        return True, f"{self.name} equipaggia {weapon.display_name}."

    def unequip_weapon(self) -> None:
        """Rimuove l'arma equipaggiata (slot vuoto)."""
        self.equipped_weapon = None

    def __repr__(self) -> str:
        return f"Character({self.name}, HP={self.stats.hp}/{self.stats.max_hp})"


# ---------------------------------------------------------------------------
# Builder astratto
# ---------------------------------------------------------------------------

class ICharacterBuilder(ABC):
    """Interfaccia Builder GoF per la costruzione dei personaggi.

    Ogni metodo corrisponde a un passo di costruzione distinto.
    Il Director chiama i passi nell'ordine corretto tramite ``construct()``.
    """

    @abstractmethod
    def reset(self) -> None:
        """Reinizializza il builder per la costruzione di un nuovo personaggio."""
        ...

    @abstractmethod
    def set_stats(self) -> None:
        """Configura le statistiche base (HP, ATK, difesa)."""
        ...

    @abstractmethod
    def set_skills(self) -> None:
        """Popola la ruota delle skill con le abilità del personaggio."""
        ...

    @abstractmethod
    def set_inventory(self) -> None:
        """Aggiunge gli oggetti iniziali all'inventario."""
        ...

    @abstractmethod
    def get_result(self) -> Character:
        """Assembla e restituisce il ``Character`` completamente costruito."""
        ...


# ---------------------------------------------------------------------------
# ConcreteBuilder — Rivet
# ---------------------------------------------------------------------------

class RivetBuilder(ICharacterBuilder):
    """ConcreteBuilder GoF per il personaggio Rivet.

    Rivet è il combattente pesante: ATK elevato, difesa media.
    Ha accesso alle skill di distruzione (esplosivi, plasma, fusione)
    e parte equipaggiato con un fucile d'assalto.
    Non può eseguire hacking.
    """

    def reset(self) -> None:
        """Reinizializza inventario (peso max 100), ruota skill e nome."""
        self._inventory = Inventory(max_weight=100)
        self._wheel     = SkillWheel()
        self._name      = "Rivet"

    def set_stats(self) -> None:
        """Rivet: 100 HP, ATK 12, difesa 9."""
        self._stats     = Stats(hp=100, atk=12, defense=9)

    def set_skills(self) -> None:
        """Aggiunge le 8 skill di Rivet alla ruota, con cooldown e tech cost."""
        self._wheel.add_skill(SkillNode("Schianto Brutale",       success_rate=0.50, cooldown=1,  unlock_tech=0))
        self._wheel.add_skill(SkillNode("Sintesi Tossicologica",                                  unlock_tech=0,  is_combat=False))
        self._wheel.add_skill(SkillNode("Rattoppo d'Emergenza",   success_rate=0.35, cooldown=0,  unlock_tech=10))
        self._wheel.add_skill(SkillNode("Esperto di Esplosivi",                                   unlock_tech=15, is_combat=False))
        self._wheel.add_skill(SkillNode("Onda al Plasma",         success_rate=0.75, cooldown=2,  unlock_tech=25, is_combat=True))
        self._wheel.add_skill(SkillNode("Ingegneria Bellica",                                     unlock_tech=30, is_combat=False))
        self._wheel.add_skill(SkillNode("Punto di Fusione",       success_rate=0.85, cooldown=0,  unlock_tech=40, is_combat=True))
        self._wheel.add_skill(SkillNode("Sintesi Instabile",                                      unlock_tech=45, is_combat=False))

    def set_inventory(self) -> None:
        """Equipaggia Rivet con esplosivo da combattimento e cocktail Molotov."""
        from game.model.item import Item, ItemType
        self._inventory.add_item(Item("battle_explosive", "Esplosivo Combatt.", ItemType.CONSUMABLE, quantity=1, damage=60, value=50))
        self._inventory.add_item(Item("molotov_cocktail", "Cocktail Molotov",   ItemType.CONSUMABLE, quantity=1, damage=40, value=35))

    def get_result(self) -> Character:
        """Assembla il personaggio Rivet con fucile d'assalto pre-equipaggiato.

        Returns:
            Oggetto ``Character`` completamente configurato per Rivet.
        """
        c = Character(self._name, self._stats, self._inventory, self._wheel)
        c.can_hack = False

        from game.model.weapon_system import WeaponRegistry
        arma = WeaponRegistry.heavy_rifle(ammo=100)
        c.weapons.append(arma)
        c.equip_weapon(arma)
        return c


# ---------------------------------------------------------------------------
# ConcreteBuilder — Echo
# ---------------------------------------------------------------------------

class EchoBuilder(ICharacterBuilder):
    """ConcreteBuilder GoF per il personaggio Echo.

    Echo è la specialista tattica: ATK più basso, difesa alta.
    Ha accesso alle skill di hacking e interferenza cognitiva,
    e parte equipaggiata con una pistola leggera.
    È l'unico personaggio in grado di eseguire hacking (``can_hack = True``).
    """

    def reset(self) -> None:
        """Reinizializza inventario (peso max 80), ruota skill e nome."""
        self._inventory = Inventory(max_weight=80)
        self._wheel     = SkillWheel()
        self._name      = "Echo"

    def set_stats(self):
        """Echo: 100 HP, ATK 8, difesa 12."""
        self._stats = Stats(hp=100, atk=8, defense=12)

    def set_skills(self) -> None:
        """Aggiunge le 8 skill di Echo alla ruota, con cooldown e tech cost.

        Note: "Hacking Veloce" richiede 999 tech points ed è sbloccabile
        solo tramite progressione avanzata.
        """
        self._wheel.add_skill(SkillNode("Manovra Evasiva",       success_rate=0.50, cooldown=1,  unlock_tech=0))
        self._wheel.add_skill(SkillNode("Hacking Veloce",                                         unlock_tech=999, is_combat=False))
        self._wheel.add_skill(SkillNode("Interferenza Cognitiva", success_rate=0.75, cooldown=2,  unlock_tech=10))
        self._wheel.add_skill(SkillNode("Espansione di Banda",                                    unlock_tech=15, is_combat=False))
        self._wheel.add_skill(SkillNode("Miraggio Tattico",       success_rate=0.75, cooldown=0,  unlock_tech=25, is_combat=True))
        self._wheel.add_skill(SkillNode("Override Radar",                                         unlock_tech=30, is_combat=False))
        self._wheel.add_skill(SkillNode("Cortocircuito Sinaptico",success_rate=0.85, cooldown=3,  unlock_tech=40, is_combat=True))
        self._wheel.add_skill(SkillNode("Decrittazione Automatica",                               unlock_tech=45, is_combat=False))

    def set_inventory(self) -> None:
        """Equipaggia Echo con razioni di cibo e kit medici."""
        from game.model.item import Item, ItemType
        self._inventory.add_item(Item("food_01", "Razioni", ItemType.CONSUMABLE, quantity=4, hp_restore=10, value=15))
        self._inventory.add_item(Item("medkit_01", "Kit Medico", ItemType.CONSUMABLE, quantity=2, hp_restore=30))

    def get_result(self) -> Character:
        """Assembla il personaggio Echo con pistola leggera pre-equipaggiata.

        Returns:
            Oggetto ``Character`` completamente configurato per Echo,
            con ``can_hack = True``.
        """
        c = Character(self._name, self._stats, self._inventory, self._wheel)
        c.can_hack = True

        from game.model.weapon_system import WeaponRegistry
        arma = WeaponRegistry.light_pistol(ammo=75)
        c.weapons.append(arma)
        c.equip_weapon(arma)
        return c


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------

class CharacterDirector:
    """Director GoF: orchestra i passi del Builder nell'ordine corretto.

    Il Director non conosce i dettagli di costruzione di nessun personaggio;
    si limita a invocare i passi nella sequenza standard:
    ``reset → set_stats → set_skills → set_inventory → get_result``.

    Args:
        builder: Il ConcreteBuilder da usare (``RivetBuilder`` o ``EchoBuilder``).
    """

    def __init__(self, builder: ICharacterBuilder) -> None:
        self._builder = builder

    def construct(self) -> Character:
        """Esegue tutti i passi di costruzione e restituisce il personaggio.

        Returns:
            Oggetto ``Character`` completamente inizializzato.
        """
        self._builder.reset()
        self._builder.set_stats()
        self._builder.set_skills()
        self._builder.set_inventory()
        return self._builder.get_result()
