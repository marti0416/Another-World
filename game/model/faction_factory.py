from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.model.enemy import EnemyCreator

from game.model.enemy import (
    Enemy,
    DannatiCreator,
    RazziatoriCreator,
    ErrantiCreator,
    SolidaliCreator,
    InfettoCreator,
    CorazzatoCreator,
    OrdaCreator,
    MeatGiantCreator,
)
from game.model.faction_system import (
    Faction,
    FactionFactory,
)
from game.model.loot_protocols import (
    ILootStrategy,
    FactionDropStrategy,
    EnvironmentalLootStrategy,
)



class IFactionFactory(ABC):
    """Abstract Factory GoF — crea la famiglia di oggetti correlati a una fazione.

    Ogni ConcreteFactory garantisce la coerenza interna della famiglia:
    l'Enemy, la Faction e la ILootStrategy prodotti appartengono alla stessa
    fazione e sono configurati in modo mutuamente compatibile.

    I client (FactionAssembler, explore_screen, battle_screen) dipendono
    solo da questa interfaccia, non dalle implementazioni concrete.
    """

    @abstractmethod
    def create_enemy(self, nome: str) -> Enemy:
        """Crea il nemico della fazione con nome dato.

        Args:
            nome: nome visualizzato del NPC (es. "Dante il Dannato")
        """
        ...

    @abstractmethod
    def create_faction(self) -> Faction:
        """Crea l'entità Faction con reputazione e allineamento predefiniti."""
        ...

    @abstractmethod
    def create_loot_strategy(self) -> ILootStrategy:
        """Restituisce la ILootStrategy appropriata per questa fazione."""
        ...

    def faction_id(self) -> str:
        """Restituisce l'identificatore stringa della fazione (es. 'Dannati').

        Utile per lookup nei dizionari esistenti senza isinstance().
        Sovrascrivibile nelle ConcreteFactory; di default usa il nome della classe.
        """
        return type(self).__name__.replace("Factory", "")



class DannatiFactory(IFactionFactory):
    """Famiglia Dannati: Enemy aggressivo, Faction ostile, loot generico."""

    def create_enemy(self, nome: str = "Dannato") -> Enemy:
        return DannatiCreator().spawn(nome=nome)

    def create_faction(self) -> Faction:
        return FactionFactory.create_dannati()

    def create_loot_strategy(self) -> ILootStrategy:
        return FactionDropStrategy()

    def faction_id(self) -> str:
        return "Dannati"


class RazziatoriFactory(IFactionFactory):
    """Famiglia Razziatori: Enemy difensivo, Faction molto ostile, loot armi."""

    def create_enemy(self, nome: str = "Razziatore") -> Enemy:
        return RazziatoriCreator().spawn(nome=nome)

    def create_faction(self) -> Faction:
        return FactionFactory.create_razziatori()

    def create_loot_strategy(self) -> ILootStrategy:
        return FactionDropStrategy()

    def faction_id(self) -> str:
        return "Razziatori"


class ErrantiFactory(IFactionFactory):
    """Famiglia Erranti: Enemy neutro, Faction neutralissima, loot ambientale."""

    def create_enemy(self, nome: str = "Errante") -> Enemy:
        return ErrantiCreator().spawn(nome=nome)

    def create_faction(self) -> Faction:
        return FactionFactory.create_erranti()

    def create_loot_strategy(self) -> ILootStrategy:
        return EnvironmentalLootStrategy()

    def faction_id(self) -> str:
        return "Erranti"


class SolidaliFactory(IFactionFactory):
    """Famiglia Solidali: Enemy debole, Faction friendly, loot medicinali."""

    def create_enemy(self, nome: str = "Solidale") -> Enemy:
        return SolidaliCreator().spawn(nome=nome)

    def create_faction(self) -> Faction:
        return FactionFactory.create_solidali()

    def create_loot_strategy(self) -> ILootStrategy:
        return FactionDropStrategy()

    def faction_id(self) -> str:
        return "Solidali"


class ZombieFactory(IFactionFactory):
    """Famiglia Zombie — gestisce tutti e 4 i tipi: Infetto, Corazzato, Orda, Gigante di Carne.

    Il tipo concreto viene dedotto dal nome NPC tramite _resolve_creator(),
    centralizzando la logica che prima era sparsa in tre punti di explore_screen.

    Regole di risoluzione (per sottostringa, case-insensitive):
      "orda"     → OrdaCreator    (spawn × 3 istanze)
      "gigante"  → MeatGiantCreator
      "corazzato"→ CorazzatoCreator
      altrimenti → InfettoCreator  (default)
    """

    _VARIANT_MAP: list[tuple[str, type]] = [
        ("orda",      OrdaCreator),
        ("gigante",   MeatGiantCreator),
        ("corazzato", CorazzatoCreator),
    ]

    @classmethod
    def _resolve_creator(cls, nome: str) -> "EnemyCreator":
        """Restituisce il Creator corretto in base al nome NPC."""
        nome_lower = nome.lower()
        for keyword, creator_cls in cls._VARIANT_MAP:
            if keyword in nome_lower:
                return creator_cls()
        return InfettoCreator()

    @classmethod
    def sprite_folder(cls, nome: str) -> str:
        """Restituisce il nome della cartella sprite per il tipo zombie.

        Usato da explore_screen per il rendering NPC sulla mappa, evitando
        la catena if/elif ripetuta. Esempio: "Orda", "Corazzato", "Gigante di Carne", "Infetto".
        """
        nome_lower = nome.lower()
        if "orda"      in nome_lower: return "Orda"
        if "gigante"   in nome_lower: return "Gigante di Carne"
        if "corazzato" in nome_lower: return "Corazzato"
        return "Infetto"

    def create_enemy(self, nome: str = "Infetto") -> Enemy:
        """Crea il nemico zombie del tipo corretto in base al nome.

        Per l'Orda restituisce una sola istanza; la moltiplicazione ×3
        avviene in FactionAssembler.build_zombie_group() che conosce
        la semantica di battaglia.
        """
        return self._resolve_creator(nome).spawn()

    def create_faction(self) -> Faction:
        return FactionFactory.create_zombie()

    def create_loot_strategy(self) -> ILootStrategy:
        return EnvironmentalLootStrategy()

    def faction_id(self) -> str:
        return "zombie"



_FACTION_MAP: dict[str, IFactionFactory] = {
    "Dannati":    DannatiFactory(),
    "Razziatori": RazziatoriFactory(),
    "Erranti":    ErrantiFactory(),
    "Solidali":   SolidaliFactory(),
    "zombie":     ZombieFactory(),
}


def get_factory(nome_fazione: str) -> IFactionFactory:
    """Restituisce la ConcreteFactory per nome_fazione.

    Args:
        nome_fazione: stringa della fazione (es. "Dannati", "zombie")

    Raises:
        ValueError: se la fazione non è registrata
    """
    factory = _FACTION_MAP.get(nome_fazione)
    if factory is None:
        raise ValueError(
            f"Fazione sconosciuta: {nome_fazione!r}. "
            f"Fazioni disponibili: {list(_FACTION_MAP)}"
        )
    return factory


def register_factory(nome_fazione: str, factory: IFactionFactory) -> None:
    """Registra una nuova ConcreteFactory a runtime.

    Permette di aggiungere nuove fazioni senza modificare questo modulo
    (Open/Closed Principle). Utile per mod, DLC o test.

    Esempio:
        register_factory("Mercanti", MerchantsFactory())
    """
    _FACTION_MAP[nome_fazione] = factory



class FactionAssembly:
    """Prodotto composito restituito da FactionAssembler.build().

    Raggruppa i tre oggetti della famiglia in un unico contenitore,
    garantendo che appartengano alla stessa fazione e siano coerenti.
    """
    __slots__ = ("enemy", "enemies", "faction", "loot_strategy", "factory")

    def __init__(
        self,
        enemy: Enemy,
        faction: Faction,
        loot_strategy: ILootStrategy,
        factory: IFactionFactory,
    ) -> None:
        self.enemy         = enemy
        self.enemies       = [enemy]
        self.faction       = faction
        self.loot_strategy = loot_strategy
        self.factory       = factory

    def __repr__(self) -> str:
        return (
            f"FactionAssembly("
            f"enemy={self.enemy.name!r}, "
            f"faction={self.faction.name!r}, "
            f"loot={type(self.loot_strategy).__name__})"
        )


class FactionAssembler:
    """Client dell'Abstract Factory — costruisce la famiglia completa.

    È l'unico punto del codebase che conosce IFactionFactory.
    Il resto del codice lavora con i singoli prodotti (Enemy, Faction,
    ILootStrategy) senza sapere come sono stati creati.

    Utilizzo tipico:
        assembly = FactionAssembler.build("Dannati", "Dante")
        enemy    = assembly.enemy
        faction  = assembly.faction
        loot     = assembly.loot_strategy

    Utilizzo diretto se serve solo il nemico (retrocompatibilità):
        enemy = FactionAssembler.build_enemy("Dannati", "Dante")
    """

    @staticmethod
    def build(nome_fazione: str, nome_npc: str = "") -> FactionAssembly:
        """Costruisce la famiglia completa per nome_fazione.

        Args:
            nome_fazione: stringa della fazione (es. "Dannati")
            nome_npc:     nome visualizzato del NPC; se vuoto usa il default

        Returns:
            FactionAssembly con enemy, faction e loot_strategy coerenti
        """
        factory = get_factory(nome_fazione)
        nome = nome_npc or factory.faction_id()
        return FactionAssembly(
            enemy=factory.create_enemy(nome),
            faction=factory.create_faction(),
            loot_strategy=factory.create_loot_strategy(),
            factory=factory,
        )

    @staticmethod
    def build_enemy(nome_fazione: str, nome_npc: str = "") -> Enemy:
        """Shortcut — restituisce solo l'Enemy, senza creare Faction e LootStrategy.

        Usato da EnemyFactory.create_npc_fazione() per retrocompatibilità:
        i caller esistenti ricevono lo stesso Enemy di prima, senza modifiche.
        """
        factory = get_factory(nome_fazione)
        nome = nome_npc or factory.faction_id()
        return factory.create_enemy(nome)

    @staticmethod
    def build_zombie_group(nome_npc: str) -> "FactionAssembly":
        """Costruisce la famiglia zombie completa, gestendo l'Orda ×3.

        Centralizza tutta la logica di selezione del tipo zombie che prima
        era ripetuta in tre punti di explore_screen. Il campo `enemies` di
        FactionAssembly contiene la lista di Enemy pronti per gs.enemies.

        Args:
            nome_npc: nome visualizzato del NPC zombie (es. "Orda dei Dannati")

        Returns:
            FactionAssembly con:
              - .enemy         → Enemy principale (primo dell'orda o singolo)
              - .enemies       → lista completa [1 o 3 Enemy]
              - .faction       → Faction zombie
              - .loot_strategy → EnvironmentalLootStrategy
        """
        factory  = get_factory("zombie")
        zfactory = factory
        enemy    = zfactory.create_enemy(nome_npc)
        enemy.name       = nome_npc
        enemy.sprite_key = nome_npc

        if "orda" in nome_npc.lower():
            e2 = zfactory.create_enemy(nome_npc)
            e3 = zfactory.create_enemy(nome_npc)
            for ex in (e2, e3):
                ex.name       = nome_npc
                ex.sprite_key = nome_npc
            enemies_list = [enemy, e2, e3]
        else:
            enemies_list = [enemy]

        assembly = FactionAssembly(
            enemy=enemy,
            faction=zfactory.create_faction(),
            loot_strategy=zfactory.create_loot_strategy(),
            factory=zfactory,
        )
        assembly.enemies = enemies_list
        return assembly
