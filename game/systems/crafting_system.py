"""
crafting_system.py — Sistema di crafting con ricette e loot procedurale per zona.

Struttura
---------
- ``RECIPES``          : dizionario globale di ricette (ingredienti → risultato).
- ``LootEntry``        : dataclass che descrive una voce in una tabella loot pesata.
- ``CraftCommand``     : Command GoF per craftare un oggetto da una ricetta.
- ``DisassembleCommand``: Command GoF per smontare un oggetto in materiali.
- ``CraftingSystem``   : ISystem che gestisce lo sblocco di ricette avanzate.
- ``generate_zone_loot``: funzione helper che genera loot da una tabella per zona.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from encodings.punycode import T
import random
from dataclasses import dataclass, field
from typing import Callable

from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.model.item import Item, ItemType, Inventory



RECIPES: dict[str, dict] = {


    "medkit": {
        "ingredients": {"chem_01": 1, "scrap_metal": 1},
        "result": Item("medkit_01", "Kit medico", ItemType.CONSUMABLE,
                       quantity=1, hp_restore=30, value=40),
        "who": "all",
        "advanced": False,
        "section": "consumabili_curativi",
        "description": "Reagente×1 + Rottame×1 → Kit medico base.",
    },
    "medkit_advanced": {
        "ingredients": {"chem_01": 2, "scrap_metal": 3},
        "result": Item("medkit_advanced", "Kit med. avanzato", ItemType.CONSUMABLE,
                       quantity=1, hp_restore=60, value=80),
        "who": "all",
        "advanced": True,
        "section": "consumabili_curativi",
        "description": "Reagente×2 + Rottame×3 → Kit medico avanzato. Richiede Sintesi Tossicologica.",
    },

    "Antibiotics": {
        "ingredients": {"chem_01": 2, "alcol_01": 1},
        "result": Item("antibiotics_01", "Antibiotici", ItemType.CONSUMABLE,
                       quantity=1, hp_restore=20, value=50),
        "who": "all",
        "advanced": False,
        "section": "consumabili_curativi",
        "description": "Reagente×2 + Alcol×1 → Antibiotici. Cura infezioni e ripristina HP.",
    },

    "Bandage": {
        "ingredients": {"stracci_01": 2, "alcol_01": 1},
        "result": Item("bandage_01", "Bende Mediche", ItemType.CONSUMABLE,
                       quantity=1, hp_restore=15, value=12),
        "who": "all",
        "advanced": False,
        "section": "consumabili_curativi",
        "description": "Stracci×2 + Alcol×1 → Bende Mediche. Cura rapida di ferite superficiali.",
    },


    "gunpowder": {
        "ingredients": {"carbone_01": 1, "zolfo_01": 1, "nitrato_01": 1},
        "result": Item("gunpowder_01", "Polvere da Sparo", ItemType.MATERIAL,
                       quantity=2, value=25),
        "who": "Rivet",
        "advanced": False,
        "section": "consumabili_offensivi",
        "description": "Carbone + Zolfo + Nitrato → Polvere da Sparo ×2.",
    },

    "molotov_cocktail": {
        "ingredients": {"alcol_01": 1, "stracci_01": 1},
        "result": Item("molotov_cocktail", "Cocktail Molotov", ItemType.CONSUMABLE,
                       quantity=1, damage=40, value=35),
        "who": "all",
        "advanced": False,
        "section": "consumabili_offensivi",
        "description": "Alcol + Stracci → Molotov. Usabile in battaglia.",
    },
    "molotov_fuel": {
        "ingredients": {"carburante_01": 1, "stracci_01": 1},
        "result": Item("molotov_cocktail", "Cocktail Molotov", ItemType.CONSUMABLE,
                       quantity=1, damage=40, value=35),
        "who": "all",
        "advanced": False,
        "section": "consumabili_offensivi",
        "description": "Carburante + Stracci → Molotov. Usabile in battaglia.",
    },

    "thermite": {
        "ingredients": {"polvere_ruggine_01": 2, "alluminio_01": 2},
        "result": Item("thermite_01", "Termite", ItemType.CONSUMABLE,
                       quantity=1, damage=80, value=60),
        "who": "Rivet",
        "advanced": False,
        "high_explosives": True,
        "section": "consumabili_offensivi",
        "description": "Polvere di Ruggine×2 + Alluminio×2 → Termite. Richiede Esperto di Esplosivi.",
    },

    "battle_explosive": {
        "ingredients": {"gunpowder_01": 2, "chem_01": 1},
        "result": Item("battle_explosive", "Esplosivo da Combattimento",
                       ItemType.CONSUMABLE, quantity=1, damage=60, value=50),
        "who": "Rivet",
        "advanced": False,
        "high_explosives": True,
        "section": "consumabili_offensivi",
        "description": "Polvere da Sparo×2 + Reagente → Esplosivo. Richiede Esperto di Esplosivi.",
    },

    "c4": {
        "ingredients": {"gunpowder_01": 3, "chem_01": 2, "alluminio_01": 1},
        "result": Item("c4_01", "Carica C4", ItemType.CONSUMABLE,
                       quantity=1, damage=150, value=120),
        "who": "Rivet",
        "advanced": True,
        "high_explosives": True,
        "section": "consumabili_offensivi",
        "description": "Polvere×3 + Reagente×2 + Alluminio → C4. Richiede Sintesi Tossicologica + Esperto di Esplosivi.",
    },

    "piranha_solution": {
        "ingredients": {"chem_01": 2, "zolfo_01": 1},
        "result": Item("piranha_solution", "Piranha Solution", ItemType.CONSUMABLE,
                       quantity=1, damage=10, value=40),
        "who": "Rivet",
        "advanced": True,
        "unstable_synthesis": True,
        "section": "consumabili_offensivi",
        "description": "Reagente×2 + Zolfo → Soluzione corrosiva. Richiede Sintesi Tossicologica + Sintesi Instabile.",
    },

    "grenade": {
        "ingredients": {"chem_01": 2, "zolfo_01": 1, "gunpowder_01": 3, "alluminio_01": 1},
        "result": Item("grenade_01", "Granata Flash", ItemType.CONSUMABLE,
                       quantity=1, damage=50, value=90),
        "who": "Rivet",
        "advanced": False,
        "high_explosives": True,
        "section": "consumabili_offensivi",
        "description": "Reagente×2 + Zolfo + Polvere×3 + Alluminio → Granata Flash. Richiede Esperto di Esplosivi.",
    },


    "improvised_club": {
        "ingredients": {"junk_01": 2, "stracci_01": 1},
        "weapon_id": "improvised_club",
        "weapon_recipe": True,
        "who": "all",
        "advanced": False,
        "section": "armi",
        "description": "Junk×2 + Stracci → Mazza. Aggiunta all'arsenale.",
    },
    "improvised_knife": {
        "ingredients": {"junk_01": 1, "scrap_metal": 1},
        "weapon_id": "improvised_knife",
        "weapon_recipe": True,
        "who": "all",
        "advanced": False,
        "section": "armi",
        "description": "Junk×1 + Rottame → Coltello. Aggiunto all'arsenale.",
    },

    "craft_rusty_weapon": {
        "ingredients": {"junk_01": 2, "scrap_metal": 1},
        "weapon_id": "rusty_pistol",
        "weapon_recipe": True,
        "who": "all",
        "advanced": False,
        "section": "armi",
        "description": "Junk×2 + Rottame×1 → Pistola Arrugginita. Arma da fuoco improvvisata.",
    },

    "craft_light_weapon": {
        "ingredients": {"junk_01": 1, "scrap_metal": 1},
        "weapon_id": "light_pistol",
        "weapon_recipe": True,
        "who": "all",
        "advanced": False,
        "section": "armi",
        "description": "Junk×1 + Rottame×1 → Pistola Leggera. Arma da fuoco base.",
    },

    "craft_heavy_rifle": {
        "ingredients": {"scrap_metal": 4, "gunpowder_01": 2, "electronics_01": 1},
        "weapon_id": "heavy_rifle",
        "weapon_recipe": True,
        "who": "Rivet",
        "advanced": False,
        "weapon_tech": True,
        "section": "armi",
        "description": "Rottame×4 + Polvere×2 + Comp.Bio-Tech×1 → Fucile Pesante. Richiede Ingegneria Bellica.",
    },

    "craft_acid_gun": {
        "ingredients": {"chem_01": 3, "scrap_metal": 3, "alluminio_01": 2},
        "weapon_id": "acid_gun",
        "weapon_recipe": True,
        "who": "Rivet",
        "advanced": True,
        "section": "armi",
        "description": "Reagente×3 + Rottame×3 + Alluminio×2 → Acid Gun. Richiede Sintesi Tossicologica.",
    },

    "craft_antimatter_grenade": {
        "ingredients": {"chem_01": 5, "gunpowder_01": 5, "alluminio_01": 3},
        "weapon_id": "antimatter_grenade",
        "weapon_recipe": True,
        "who": "Rivet",
        "advanced": True,
        "high_explosives": True,
        "unstable_synthesis": True,
        "section": "armi",
        "description": "Reagente×5 + Polvere×5 + Alluminio×3 → Granata Antimateria. Richiede Sintesi Tossicologica + Esperto di Esplosivi + Sintesi Instabile.",
    },

    "craft_artillery": {
        "ingredients": {"electronics_01": 3, "kevlar_scrap": 2, "gunpowder_01": 4, "scrap_metal": 5},
        "weapon_id": "artillery",
        "weapon_recipe": True,
        "who": "Rivet",
        "advanced": False,
        "weapon_tech": True,
        "section": "armi",
        "description": "Comp.Bio-Tech×3 + Kevlar×2 + Polvere×4 + Rottame×5 → Desig. Artiglieria. Richiede Ingegneria Bellica.",
    },
}



@dataclass
class LootEntry:
    """Voce in una tabella loot pesata.

        Attributes:
            item_id:    ID dell'oggetto nel registry.
            name:       Nome visualizzato.
            item_type:  Categoria (``ItemType``).
            qty_min:    Quantità minima generata.
            qty_max:    Quantità massima generata.
            weight:     Peso relativo per la selezione casuale pesata.
            value:      Valore in crediti.
            hp_restore: HP ripristinati se consumabile curativo.
            damage:     Danno se consumabile offensivo.
    """
    item_id:   str
    name:      str
    item_type: ItemType
    qty_min:   int
    qty_max:   int
    weight:    float
    hp_restore: int = 0
    damage:    int = 0
    value:     int = 0


COMMON_HOUSE_LOOT: list[LootEntry] = [
    LootEntry("junk_can",     "Lattina Vuota",    ItemType.MATERIAL,   1, 4, 0.35, value=1),
    LootEntry("junk_cloth",   "Straccio Sporco",  ItemType.MATERIAL,   1, 3, 0.30, value=2),
    LootEntry("junk_01",      "Junk Vario",       ItemType.MATERIAL,   1, 2, 0.20, value=1),
    LootEntry("food_01",      "Razioni",          ItemType.CONSUMABLE, 1, 2, 0.10, hp_restore=10, value=15),
    LootEntry("medkit_01",    "Kit medico",       ItemType.CONSUMABLE, 1, 1, 0.05, hp_restore=30, value=40),
]

CITY_HIGH_LOOT: list[LootEntry] = [
    LootEntry("electronics_01", "Componenti Bio-Tech", ItemType.MATERIAL, 1, 2, 0.30, value=45),
    LootEntry("food_02",       "Cibo in Scatola",     ItemType.CONSUMABLE, 1, 3, 0.25, hp_restore=15, value=20),
    LootEntry("medkit_01",     "Kit Medico",          ItemType.CONSUMABLE, 1, 1, 0.20, hp_restore=30, value=40),
    LootEntry("alcol_01",      "Alcol",               ItemType.MATERIAL,   1, 2, 0.15, value=12),
    LootEntry("key_card_01",   "Badge Accesso",       ItemType.KEY_ITEM,   1, 1, 0.10, value=0),
]

MILITARY_DISTRICT_LOOT: list[LootEntry] = [
    LootEntry("ammo_01",       "Munizioni",           ItemType.MATERIAL,   10, 20, 0.35, value=5),
    LootEntry("kevlar_scrap",  "Fibre Kevlar",        ItemType.MATERIAL,   2, 4,   0.25, value=18),
    LootEntry("pistol_01",     "Pistola d'Ordinanza", ItemType.WEAPON,     1, 1,   0.12, damage=15, value=60),
    LootEntry("pistol_02",     "Pistola leggera",     ItemType.WEAPON,     1, 1,   0.08, damage=25, value=60),
    LootEntry("recovered",     "Arma Recuperata",     ItemType.WEAPON,     1, 1,   0.05, damage=20, value=200),
    LootEntry("grenade_01",    "Granata Flash",       ItemType.CONSUMABLE, 1, 1,   0.10, damage=50, value=90),
    LootEntry("incendiary_missile", "Missile Incendiario", ItemType.WEAPON, 1, 2, 0.03, value=400),
    LootEntry("antimatter_grenade", "Granata Antimateria", ItemType.WEAPON, 1, 1, 0.02, value=500),
    LootEntry("thermobaric_rocket", "Razzo Termobarico",   ItemType.WEAPON, 1, 1, 0.02, value=600),
    LootEntry("artillery",          "Desig. Artiglieria",  ItemType.WEAPON, 1, 1, 0.01, value=800),
]

RURAL_LOOT: list[LootEntry] = [
    LootEntry("food_01",       "Razioni",             ItemType.CONSUMABLE, 2, 4, 0.40, hp_restore=10, value=15),
    LootEntry("stracci_01",    "Stracci",             ItemType.MATERIAL,   2, 5, 0.30, value=2),
    LootEntry("junk_01",       "Junk Vario",          ItemType.MATERIAL,   1, 3, 0.15, value=1),
    LootEntry("improvised_club","Mazza di Fortuna",   ItemType.WEAPON,     1, 1, 0.10, damage=18, value=10),
    LootEntry("carbone_01",    "Carbone",             ItemType.MATERIAL,   1, 3, 0.05, value=8),
]

INDUSTRIAL_LOOT: list[LootEntry] = [
    LootEntry("scrap_metal",   "Rottame",             ItemType.MATERIAL,   3, 6, 0.35, value=10),
    LootEntry("alluminio_01",  "Alluminio",           ItemType.MATERIAL,   1, 3, 0.25, value=10),
    LootEntry("junk_electronics","Elettronica Rotta", ItemType.MATERIAL,   1, 2, 0.20, value=2),
    LootEntry("polvere_ruggine_01","Polv. Ruggine",   ItemType.MATERIAL,   1, 3, 0.15, value=8),
    LootEntry("gunpowder_01",  "Polvere da Sparo",    ItemType.MATERIAL,   1, 2, 0.05, value=25),
]

PHARMACY_LOOT: list[LootEntry] = [
    LootEntry("antibiotics_01","Antibiotici",         ItemType.CONSUMABLE, 1, 3, 0.40, hp_restore=20, value=50),
    LootEntry("medkit_01",     "Kit medico",          ItemType.CONSUMABLE, 1, 2, 0.35, hp_restore=30, value=40),
    LootEntry("medkit_advanced","Kit med. avanz.",    ItemType.CONSUMABLE, 1, 1, 0.15, hp_restore=60, value=80),
    LootEntry("chem_01",       "Reagente",            ItemType.MATERIAL,   1, 2, 0.10, value=20),
    LootEntry("bandage_01",    "Bende Mediche",       ItemType.CONSUMABLE, 1, 3, 0.25, hp_restore=15, value=12),
]

SHELF_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",     "Kit medico",          ItemType.CONSUMABLE, 1, 1, 0.25, hp_restore=30, value=40),
    LootEntry("antibiotics_01","Antibiotici",         ItemType.CONSUMABLE, 1, 2, 0.10, hp_restore=20, value=50),
    LootEntry("food_01",       "Razioni",             ItemType.CONSUMABLE, 1, 2, 0.20, hp_restore=10, value=15),
    LootEntry("junk_can",      "Lattina Vuota",       ItemType.MATERIAL,   1, 3, 0.15, value=1),
    LootEntry("junk_cloth",    "Straccio Sporco",     ItemType.MATERIAL,   1, 2, 0.10, value=2),
    LootEntry("alcol_01",      "Alcol",               ItemType.MATERIAL,   1, 1, 0.10, value=12),
    LootEntry("chem_01",       "Reagente",            ItemType.MATERIAL,   1, 1, 0.10, value=20),
]

SUPERMARKET_LOOT: list[LootEntry] = [
    LootEntry("food_01",       "Razioni",             ItemType.CONSUMABLE, 2, 5, 0.35, hp_restore=10, value=15),
    LootEntry("food_02",       "Cibo in Scatola",     ItemType.CONSUMABLE, 1, 3, 0.25, hp_restore=15, value=20),
    LootEntry("junk_can",      "Lattina Vuota",       ItemType.MATERIAL,   1, 4, 0.20, value=1),
    LootEntry("medkit_01",     "Kit medico",          ItemType.CONSUMABLE, 1, 1, 0.10, hp_restore=30, value=40),
    LootEntry("carburante_01", "Carburante",          ItemType.MATERIAL,   1, 1, 0.10, value=20),
]


def _weighted_choice(table: list[LootEntry], rng=random) -> LootEntry | None:
    if not table:
        return None
    total = sum(e.weight for e in table)
    r = rng.uniform(0, total)
    cumulative = 0.0
    for entry in table:
        cumulative += entry.weight
        if r <= cumulative:
            return entry
    return table[-1]


def generate_zone_loot(zone_type: str, num_rolls: int = 3) -> list[Item]:
    table = {
        "common_house": COMMON_HOUSE_LOOT,
        "pharmacy":     PHARMACY_LOOT,
        "supermarket":  SUPERMARKET_LOOT,
        "military":     MILITARY_DISTRICT_LOOT,
        "rural":        RURAL_LOOT,
        "industrial":   INDUSTRIAL_LOOT,
        "shelf":        SHELF_LOOT,
        "city_high":    CITY_HIGH_LOOT,
    }.get(zone_type, COMMON_HOUSE_LOOT)

    items: list[Item] = []
    for _ in range(num_rolls):
        entry = _weighted_choice(table)
        if entry:
            qty = random.randint(entry.qty_min, entry.qty_max)
            items.append(Item(entry.item_id, entry.name, entry.item_type,
                              quantity=qty, value=entry.value,
                              hp_restore=entry.hp_restore, damage=entry.damage))
    return items


def randomize_supermarket_occupants() -> str:
    """Randomizza gli occupanti del Supermercato al caricamento del livello."""
    SUPERMARKET_OCCUPANTS = [
        {"type": "zombie_horde",   "weight": 0.40},
        {"type": "razziatori",     "weight": 0.25},
        {"type": "erranti",        "weight": 0.20},
        {"type": "empty",          "weight": 0.15},
    ]
    total = sum(o["weight"] for o in SUPERMARKET_OCCUPANTS)
    r = random.uniform(0, total)
    cumulative = 0.0
    for occ in SUPERMARKET_OCCUPANTS:
        cumulative += occ["weight"]
        if r <= cumulative:
            return occ["type"]
    return "empty"



class ICraftCommand(ABC):
    """Command astratto — produce il risultato di una ricetta.

    Precondizione: gli ingredienti sono già stati consumati dall'Invoker.
    """

    @abstractmethod
    def execute(
        self,
        recipe:    dict,
        inventory: Inventory,
        character: str,
        bus,
    ) -> dict:
        """Produce il risultato e restituisce il dict di esito craft.

        Returns:
            {"success": True/False, "message": str, ...prodotto...}
        """
        ...


class WeaponCraftCommand(ICraftCommand):
    """Produce un'arma via WeaponRegistry e pubblica ITEM_CRAFTED.

    Usata per ricette con weapon_recipe=True.
    Il weapon_id nella ricetta deve corrispondere a un metodo factory
    in WeaponRegistry (es. WeaponRegistry.assault_rifle_behaviour()).
    """

    def execute(self, recipe: dict, inventory: Inventory,
                character: str, bus) -> dict:
        from game.model.weapon_system import WeaponRegistry
        weapon_id = recipe.get("weapon_id", "")
        factory   = getattr(WeaponRegistry, weapon_id, None)
        if factory is None:
            return {"success": False,
                    "message": f"WeaponRegistry.{weapon_id} non trovato."}
        weapon = factory()
        if bus:
            bus.publish(EventType.ITEM_CRAFTED,
                        {"weapon": weapon, "character": character})
        return {"success": True,
                "message": f"Crafting: {weapon.display_name}!",
                "weapon": weapon}


class ItemCraftCommand(ICraftCommand):
    """Produce un Item, lo aggiunge all'inventario e pubblica ITEM_CRAFTED.

    Usata per tutte le ricette normali (consumabili, granate, kit, ecc.).
    """

    def execute(self, recipe: dict, inventory: Inventory,
                character: str, bus) -> dict:
        r = recipe["result"]
        result_item = Item(r.item_id, r.name, r.item_type,
                           r.quantity, r.value, r.hp_restore, r.damage, r.defense)
        inventory.add_item(result_item)
        if bus:
            bus.publish(EventType.ITEM_CRAFTED,
                        {"item": result_item, "character": character})
        return {"success": True,
                "message": f"Crafting: {result_item.name}!",
                "item": result_item}



class CraftingSystem(ISystem):
    """Sistema di crafting.

    PATTERN 1 — Strategy (Table-Driven) per i prerequisiti skill:
      Le 4 catene if/elif su (recipe_flag, unlock_dict, messaggio) sono
      sostituite da due strutture dati centrali:
        _skill_locks: dict[skill_key, dict[character, bool]]
        _SKILL_MESSAGES: dict[skill_key, str]
      craft() e get_available_recipes() iterano la stessa tabella —
      aggiungere una quinta skill richiede 2 righe, zero modifiche ai metodi.
      I metodi unlock_*() esistenti restano come wrapper di retrocompatibilità.

    PATTERN 2 — Command per i rami di produzione:
      Il doppio branch if/else "weapon_recipe vs item" in craft() è sostituito
      da due ConcreteCommand (ICraftCommand):
        WeaponCraftCommand — produce un Weapon via WeaponRegistry
        ItemCraftCommand   — produce un Item e lo aggiunge all'inventario
      _CRAFT_COMMANDS mappa recipe_flag → comando; craft() fa dispatch in
      una riga senza if. Aggiungere un nuovo tipo di ricetta: 1 classe + 1 voce.
    """

    _SKILL_MESSAGES: dict[str, str] = {
        "advanced":           "⚠ Sblocca prima la skill Sintesi Tossicologica.",
        "weapon_tech":        "⚠ Sblocca prima la skill Ingegneria Bellica.",
        "high_explosives":    "⚠ Sblocca prima la skill Esperto di Esplosivi.",
        "unstable_synthesis": "⚠ Sblocca prima la skill Sintesi Instabile.",
    }

    def __init__(self) -> None:
        self._bus: EventBus | None = None

        self._skill_locks: dict[str, dict[str, bool]] = {
            key: {"Rivet": False, "Echo": False}
            for key in self._SKILL_MESSAGES
        }

        self._in_turn_combat: bool = False

        self._craft_commands: dict[str, "ICraftCommand"] = {
            "weapon_recipe": WeaponCraftCommand(),
            "default":       ItemCraftCommand(),
        }

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus
        bus.subscribe(EventType.START_ENCOUNTER, self._on_combat_start)
        bus.subscribe(EventType.BATTLE_ENDED,    self._on_combat_end)

    def cleanup(self) -> None:
        if self._bus:
            self._bus.unsubscribe(EventType.START_ENCOUNTER, self._on_combat_start)
            self._bus.unsubscribe(EventType.BATTLE_ENDED,    self._on_combat_end)

    def _on_combat_start(self, data: dict) -> None:
        self._in_turn_combat = True

    def _on_combat_end(self, data: dict) -> None:
        self._in_turn_combat = False


    def unlock_skill(self, skill_key: str, character: str) -> None:
        """Sblocca una skill prerequisito per il personaggio dato.

        Metodo unificato che sostituisce i 4 unlock_*() separati.
        Accetta qualsiasi skill_key presente in _SKILL_MESSAGES.
        """
        if skill_key in self._skill_locks:
            self._skill_locks[skill_key][character] = True

    def unlock_advanced_chemistry(self, character: str) -> None:
        self.unlock_skill("advanced", character)

    def unlock_weapon_tech(self, character: str) -> None:
        self.unlock_skill("weapon_tech", character)

    def unlock_high_explosives(self, character: str) -> None:
        self.unlock_skill("high_explosives", character)

    def unlock_unstable_synthesis(self, character: str) -> None:
        self.unlock_skill("unstable_synthesis", character)


    def _check_skill_prereqs(self, recipe: dict, character: str) -> dict | None:
        """Verifica i prerequisiti skill tramite la Strategy Table.

        Itera _SKILL_MESSAGES: se la ricetta richiede la skill E il
        personaggio non la possiede, restituisce il dict di errore.
        Restituisce None se tutti i prerequisiti sono soddisfatti.
        """
        for skill_key, msg in self._SKILL_MESSAGES.items():
            if recipe.get(skill_key) and \
               not self._skill_locks[skill_key].get(character, False):
                return {"success": False, "message": msg}
        return None


    def get_available_recipes(self, character: str) -> dict[str, dict]:
        """Restituisce le ricette sbloccate per il personaggio dato."""
        result = {}
        for rid, recipe in RECIPES.items():
            who = recipe.get("who", "all")
            if who not in ("all", character):
                continue
            if self._check_skill_prereqs(recipe, character) is not None:
                continue
            result[rid] = recipe
        return result

    def get_available_recipes_by_section(self, character: str) -> dict[str, dict[str, dict]]:
        """Restituisce le ricette sbloccate raggruppate per sezione."""
        available = self.get_available_recipes(character)
        sections: dict[str, dict] = {"consumabili_offensivi": {}, "armi": {}}
        for rid, recipe in available.items():
            sec = recipe.get("section", "consumabili_offensivi")
            sections.setdefault(sec, {})[rid] = recipe
        return sections


    def craft(self, recipe_id: str, inventory: Inventory, character: str) -> dict:
        """Esegue il crafting di una ricetta.

        Struttura fissa (invariante):
          1. Lookup ricetta
          2. Controllo chi può craftare
          3. Controllo prerequisiti skill (Strategy Table-Driven)
          4. Verifica e consumo ingredienti
          5. Dispatch al Command corretto (Command Pattern)

        Per aggiungere un nuovo tipo di ricetta: implementare ICraftCommand
        e aggiungere la voce in _craft_commands. Questo metodo non va modificato.
        """
        recipe = RECIPES.get(recipe_id)
        if not recipe:
            return {"success": False, "message": "Ricetta sconosciuta."}

        who = recipe.get("who", "all")
        if who == "Rivet" and character != "Rivet":
            return {"success": False, "message": "Solo Lui può craftare questo."}
        if who == "Echo" and character != "Echo":
            return {"success": False, "message": "Solo Lei può craftare questo."}

        prereq_error = self._check_skill_prereqs(recipe, character)
        if prereq_error:
            return prereq_error

        for item_id, qty in recipe["ingredients"].items():
            it = inventory.get_item(item_id)
            if not it or it.quantity < qty:
                from game.model.item_registry import get_item_proto
                proto = get_item_proto(item_id)
                nome = proto.name if proto else item_id
                return {"success": False,
                        "message": f"Ingredienti insufficienti: {nome} ×{qty}"}

        for item_id, qty in recipe["ingredients"].items():
            inventory.remove_item(item_id, qty)

        cmd_key = "weapon_recipe" if recipe.get("weapon_recipe") else "default"
        return self._craft_commands[cmd_key].execute(recipe, inventory, character, self._bus)


    def use_thermite_on_door(self, inventory: Inventory, character: str,
                              door_id: str) -> dict:
        """Applica Termite su una Porta Blindata Sigillata."""
        if character != "Rivet":
            return {"success": False, "message": "Solo Lui può usare la Termite."}

        item = inventory.get_item("thermite_01")
        if not item:
            return {"success": False, "message": "Termite non trovata nell'inventario."}

        inventory.remove_item("thermite_01", 1)
        if self._bus:
            self._bus.publish(EventType.DOOR_BREACHED,
                              {"door_id": door_id, "method": "thermite"})

        return {"success": True,
                "message": f"Termite applicata alla porta '{door_id}'. Accesso garantito!"}

    def use_c4_on_door(self, inventory: Inventory, character: str,
                        door_id: str) -> dict:
        """Piazza il C4 su porte barricatesi di un Grattacielo."""
        if character != "Rivet":
            return {"success": False, "message": "Solo Lui può piazzare il C4."}

        item = inventory.get_item("c4_01")
        if not item:
            return {"success": False, "message": "Carica C4 non trovata."}

        inventory.remove_item("c4_01", 1)
        if self._bus:
            self._bus.publish(EventType.DOOR_BREACHED,
                              {"door_id": door_id, "method": "c4", "explosive": True})

        return {"success": True,
                "message": f"C4 piazzato sulla porta '{door_id}'. BOOM!"}

    def use_piranha_solution(self, inventory: Inventory, character: str,
                              obstacle_id: str) -> dict:
        """Usa Piranha Solution su serrature arrugginite o detriti."""
        if character != "Rivet":
            return {"success": False, "message": "Solo Lui può usare la Piranha Solution."}

        item = inventory.get_item("piranha_solution")
        if not item:
            return {"success": False, "message": "Piranha Solution non trovata."}

        inventory.remove_item("piranha_solution", 1)
        if self._bus:
            self._bus.publish(EventType.OBSTACLE_CLEARED,
                              {"obstacle_id": obstacle_id, "method": "piranha"})

        return {"success": True,
                "message": f"Piranha Solution scioglie '{obstacle_id}'. Percorso aperto!"}


    def eat_food(self, item_id: str, inventory: Inventory, character) -> dict:
        """Mangiare Cibo in esplorazione ripristina salute (solo fuori dal combattimento)."""
        if self._in_turn_combat:
            return {"success": False,
                    "message": "Non puoi mangiare durante un combattimento a turni."}

        item = inventory.get_item(item_id)
        if not item:
            return {"success": False, "message": f"'{item_id}' non trovato."}
        if item.item_type != ItemType.CONSUMABLE or item.hp_restore <= 0:
            return {"success": False, "message": f"'{item.name}' non è cibo."}

        healed = character.stats.heal(item.hp_restore)
        inventory.remove_item(item_id, 1)
        return {"success": True,
                "message": f"{character.name} mangia {item.name}: +{healed} HP"}


    def craft_and_use_in_battle(self, recipe_id: str, inventory: Inventory,
                                 character: str, battle_targets: list) -> dict:
        """
        Lui accede al menu Crafting durante la battaglia,
        crea un consumabile offensivo e lo usa immediatamente contro i bersagli.
        Non applicabile a ricette arma (weapon_recipe).
        """
        recipe = RECIPES.get(recipe_id)
        if not recipe:
            return {"success": False, "message": "Ricetta sconosciuta."}
        if recipe.get("weapon_recipe"):
            return {"success": False,
                    "message": "Le armi non si usano istantaneamente in battaglia dopo il craft."}

        craft_result = self.craft(recipe_id, inventory, character)
        if not craft_result["success"]:
            return craft_result

        item = craft_result["item"]
        if item.damage <= 0:
            return {"success": False,
                    "message": f"'{item.name}' non ha danno. Usarlo fuori dal combattimento."}

        alive = [t for t in battle_targets if t.is_alive()]
        if not alive:
            return {"success": True, "message": "Nessun bersaglio vivo.", "hits": []}

        hits = []
        for target in alive:
            dmg = target.stats.take_damage(item.damage)
            hits.append((target.name, dmg))

        inventory.remove_item(item.item_id, 1)

        log = (f"{character.upper()} crafta e usa '{item.name}' in battaglia! "
               + ", ".join(f"{n}: -{d} HP" for n, d in hits))
        return {"success": True, "message": log, "hits": hits,
                "total_damage": sum(d for _, d in hits)}