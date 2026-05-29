"""
loot_system.py — Sistema di loot procedurale con tabelle pesate per zona.

Struttura
---------
- Pool di ``LootEntry`` per zona (universale, farmacia, supermercato, ecc.).
- Strategy concrete per ogni zona: ``CommonHouseLootStrategy``,
  ``PharmacyLootStrategy``, ``CityHighLootStrategy``, ``MilitaryLootStrategy``,
  ``RuralLootStrategy``, ``IndustrialLootStrategy``, ``TrashLootStrategy``.
- ``LootSystem``: ISystem che gestisce i loot spot e coordina le strategie.
- ``_roll_table``: helper per estrarre N item da una tabella pesata.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.model.item import Item, ItemType
from game.model.loot_protocols import (
    LootContext,
    ILootStrategy,
    EnvironmentalLootStrategy,
    FactionDropStrategy,
)

from game.systems.crafting_system import (
    generate_zone_loot,
    randomize_supermarket_occupants,
    LootEntry,
    COMMON_HOUSE_LOOT,
    PHARMACY_LOOT,
    SUPERMARKET_LOOT,
    SHELF_LOOT,
)



def _roll_table(table: list[LootEntry], num_rolls: int = 3) -> list[Item]:
    """Esegue num_rolls tiri sulla tabella, restituisce la lista di Item."""
    items: list[Item] = []
    for _ in range(num_rolls):
        total = sum(e.weight for e in table)
        r = random.uniform(0, total)
        cumulative = 0.0
        for entry in table:
            cumulative += entry.weight
            if r <= cumulative:
                qty = random.randint(entry.qty_min, entry.qty_max)
                items.append(Item(
                    entry.item_id, entry.name, entry.item_type,
                    quantity=qty, value=entry.value,
                    hp_restore=entry.hp_restore, damage=entry.damage
                ))
                break
    return items



UNIVERSAL_MATERIAL_POOL: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.02, value=45),
    LootEntry("junk_electronics",   "Elettronica Rotta",    ItemType.MATERIAL, 1, 2, 0.03, value=2),
]

MEDIUM_MATERIAL_POOL: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.03, value=25),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.03, value=45),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
]

def _maybe_add_material(items: list[Item], pool: list[LootEntry] = UNIVERSAL_MATERIAL_POOL, rolls: int = 1) -> list[Item]:
    """Aggiunge 0–rolls material dal pool universale (% molto basse)."""
    items.extend(_roll_table(pool, num_rolls=rolls))
    return items



SCAFFALE_LOOT: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.03, value=25),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.03, value=45),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 1, 2, 0.08, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 2, 0.06, hp_restore=15, value=20),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.05, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 2, 0.05, hp_restore=15, value=12),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1, 0.02, damage=14, value=8),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.01, damage=15, value=60),
]

SCATOLE_LOOT: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.03, value=25),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.03, value=45),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 1, 2, 0.05, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 2, 0.06, hp_restore=15, value=20),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.04, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.03, hp_restore=15, value=12),
    LootEntry("improvised_club",    "Mazza di Fortuna",     ItemType.WEAPON,     1, 1, 0.02, damage=18, value=10),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.01, damage=15, value=60),
]

AUTO_LOOT: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.03, value=25),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.03, value=45),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 1, 1, 0.05, hp_restore=10, value=15),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.04, hp_restore=15, value=12),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1, 0.02, damage=14, value=8),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.01, damage=15, value=60),
]

FARMACIA_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 2, 0.30, hp_restore=30, value=40),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 3, 0.28, hp_restore=20, value=50),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 3, 0.22, hp_restore=15, value=12),
    LootEntry("medkit_advanced",    "Kit med. avanzato",    ItemType.CONSUMABLE, 1, 1, 0.12, hp_restore=60, value=80),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 1, 0.01, damage=40, value=35),
]

NEGOZIO_LOOT: list[LootEntry] = [
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 2, 4, 0.30, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 3, 0.28, hp_restore=15, value=20),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.03, hp_restore=15, value=12),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.02, hp_restore=30, value=40),
]

SUPERMERCATO_LOOT: list[LootEntry] = [
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 2, 5, 0.32, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 2, 4, 0.28, hp_restore=15, value=20),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.04, hp_restore=15, value=12),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.03, hp_restore=30, value=40),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.01, hp_restore=20, value=50),
]

CASA_LOOT: list[LootEntry] = [
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 1, 3, 0.28, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 2, 0.20, hp_restore=15, value=20),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 2, 0.18, hp_restore=15, value=12),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.12, hp_restore=30, value=40),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.08, hp_restore=20, value=50),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 4, 0.20, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 3, 0.18, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 4, 0.15, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 3, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 3, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 2, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 2, 0.06, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 2, 0.05, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.06, value=5),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.03, value=25),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.03, value=45),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.03, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1, 0.02, damage=14, value=8),
]

SCUOLA_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 2, 0.20, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 2, 0.18, hp_restore=15, value=12),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.12, hp_restore=20, value=50),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 1, 0.03, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.02, damage=60, value=50),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("junk_electronics",   "Elettronica Rotta",    ItemType.MATERIAL, 1, 2, 0.03, value=2),
]

STAZIONE_GAS_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 2, 0.18, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 2, 0.16, hp_restore=15, value=12),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2, 0.15, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.12, damage=60, value=50),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.08, damage=80, value=60),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.07, hp_restore=20, value=50),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
]

VIGILI_FUOCO_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 3, 0.22, hp_restore=30, value=40),
    LootEntry("medkit_advanced",    "Kit med. avanzato",    ItemType.CONSUMABLE, 1, 2, 0.14, hp_restore=60, value=80),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 3, 0.16, hp_restore=15, value=12),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 2, 0.10, hp_restore=20, value=50),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2, 0.10, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.08, damage=60, value=50),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.06, damage=80, value=60),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.02, damage=15, value=60),
    LootEntry("improvised_club",    "Mazza di Fortuna",     ItemType.WEAPON,     1, 1, 0.02, damage=18, value=10),
]

STAZIONE_BENZINA_LOOT: list[LootEntry] = [
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 2, 0.18, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 2, 0.16, hp_restore=15, value=12),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2, 0.15, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.12, damage=60, value=50),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.08, damage=80, value=60),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.07, hp_restore=20, value=50),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
]

CASERMA_LOOT: list[LootEntry] = [
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.08, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 2, 0.04, value=18),
    LootEntry("grenade_01",         "Granata Flash",        ItemType.CONSUMABLE, 1, 2, 0.14, damage=50, value=90),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.08, damage=80, value=60),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.06, damage=60, value=50),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.10, damage=15, value=60),
    LootEntry("pistol_02",          "Pistola leggera",      ItemType.WEAPON,     1, 1, 0.08, damage=25, value=60),
    LootEntry("heavy_rifle_01",     "Fucile d'Assalto Pesante", ItemType.WEAPON, 1, 1, 0.06, damage=80, value=200),
    LootEntry("recovered",          "Arma Recuperata",      ItemType.WEAPON,     1, 1, 0.04, damage=20, value=200),
    LootEntry("incendiary_missile", "Missile Incendiario",  ItemType.WEAPON,     1, 1, 0.03, value=400),
    LootEntry("antimatter_grenade", "Granata Antimateria",  ItemType.WEAPON,     1, 1, 0.02, value=500),
    LootEntry("thermobaric_rocket", "Razzo Termobarico",    ItemType.WEAPON,     1, 1, 0.02, value=600),
    LootEntry("artillery",          "Designatore Artigl.",  ItemType.WEAPON,     1, 1, 0.01, value=800),
]

STAZIONE_POLIZIA_LOOT: list[LootEntry] = [
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("grenade_01",         "Granata Flash",        ItemType.CONSUMABLE, 1, 2,  0.18, damage=50, value=90),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2,  0.14, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1,  0.12, damage=60, value=50),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1,  0.10, damage=15, value=60),
    LootEntry("pistol_02",          "Pistola leggera",      ItemType.WEAPON,     1, 1,  0.06, damage=25, value=60),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1,  0.05, damage=14, value=8),
    LootEntry("improvised_club",    "Mazza di Fortuna",     ItemType.WEAPON,     1, 1,  0.02, damage=18, value=10),
]
GRATTACIELO_LOOT: list[LootEntry] = [
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.02, value=45),
    LootEntry("junk_electronics",   "Elettronica Rotta",    ItemType.MATERIAL, 1, 2, 0.03, value=2),

    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 2, 0.14, hp_restore=15, value=20),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.13, hp_restore=30, value=40),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.10, hp_restore=15, value=12),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 1, 0.08, damage=40, value=35),
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 1, 1, 0.05, hp_restore=10, value=15),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.05, damage=60, value=50),
    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 1, 0.04, hp_restore=20, value=50),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.02, damage=15, value=60),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1, 0.01, damage=14, value=8),
]

TENDA_DORMITORIO_HANGAR_LOOT: list[LootEntry] = [
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 2, 6, 0.08, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.02, value=45),
    LootEntry("grenade_01",         "Granata Flash",        ItemType.CONSUMABLE, 1, 2,  0.12, damage=50, value=90),
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2,  0.10, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1,  0.08, damage=60, value=50),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1,  0.06, damage=80, value=60),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1,  0.05, hp_restore=15, value=12),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1,  0.03, hp_restore=30, value=40),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1,  0.05, damage=15, value=60),
    LootEntry("pistol_02",          "Pistola leggera",      ItemType.WEAPON,     1, 1,  0.04, damage=25, value=60),
    LootEntry("recovered",          "Arma Recuperata",      ItemType.WEAPON,     1, 1,  0.03, damage=20, value=200),
    LootEntry("improvised_club",    "Mazza di Fortuna",     ItemType.WEAPON,     1, 1,  0.02, damage=18, value=10),
    LootEntry("improvised_knife",   "Coltello Improvvisato",ItemType.WEAPON,     1, 1,  0.01, damage=14, value=8),
]

FATTORIA_LOOT: list[LootEntry] = [
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 3, 6, 0.35, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 2, 4, 0.28, hp_restore=15, value=20),

    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
]

MULINO_LOOT: list[LootEntry] = [
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 2, 0.20, damage=40, value=35),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 2, 0.16, damage=80, value=60),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 2, 0.14, damage=60, value=50),
    LootEntry("piranha_solution",   "Piranha Solution",     ItemType.CONSUMABLE, 1, 1, 0.10, damage=10, value=40),
    LootEntry("grenade_01",         "Granata Flash",        ItemType.CONSUMABLE, 1, 1, 0.08, damage=50, value=90),
    LootEntry("bandage_01",         "Bende Mediche",        ItemType.CONSUMABLE, 1, 1, 0.08, hp_restore=15, value=12),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.05, hp_restore=30, value=40),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL,   1, 2, 0.07, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL,   1, 2, 0.05, value=18),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL,   1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL,   1, 1, 0.03, value=25),
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 1, 0.07, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),

    LootEntry("improvised_club",    "Mazza di Fortuna",     ItemType.WEAPON,     1, 1, 0.04, damage=18, value=10),
    LootEntry("pistol_01",          "Pistola arrugginita",  ItemType.WEAPON,     1, 1, 0.02, damage=15, value=60),
]

LABORATORIO_LOOT: list[LootEntry] = [
    LootEntry("alcol_01",           "Alcol",                ItemType.MATERIAL, 1, 1, 0.08, value=12),
    LootEntry("chem_01",            "Reagente",             ItemType.MATERIAL, 1, 2, 0.10, value=20),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL, 1, 1, 0.02, value=12),
    LootEntry("nitrato_01",         "Nitrato di Potassio",  ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 2, 0.06, value=45),
    LootEntry("junk_electronics",   "Elettronica Rotta",    ItemType.MATERIAL, 1, 2, 0.03, value=2),

    LootEntry("antibiotics_01",     "Antibiotici",          ItemType.CONSUMABLE, 1, 2, 0.14, hp_restore=20, value=50),
    LootEntry("medkit_01",          "Kit medico",           ItemType.CONSUMABLE, 1, 1, 0.10, hp_restore=30, value=40),
    LootEntry("piranha_solution",   "Piranha Solution",     ItemType.CONSUMABLE, 1, 1, 0.10, damage=10, value=40),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.08, damage=80, value=60),
    LootEntry("c4_01",              "Carica C4",            ItemType.CONSUMABLE, 1, 1, 0.05, damage=150, value=120),
    LootEntry("zolfo_01",           "Zolfo",                ItemType.MATERIAL,   1, 2, 0.06, value=12),
    LootEntry("rail_gun",           "Rail Gun",             ItemType.WEAPON,     1, 1, 0.03, damage=55, value=200),
    LootEntry("acid_gun",           "Pistola Acida",        ItemType.WEAPON,     1, 1, 0.02, damage=20, value=200),
    LootEntry("data_chip",          "Chip dati",            ItemType.KEY_ITEM,   1, 1, 0.10, value=50),
]

CENTRALE_ELETTRICA_LOOT: list[LootEntry] = [
    LootEntry("molotov_cocktail",   "Cocktail Molotov",     ItemType.CONSUMABLE, 1, 1, 0.25, damage=40, value=35),
    LootEntry("battle_explosive",   "Esplosivo Combatt.",   ItemType.CONSUMABLE, 1, 1, 0.22, damage=60, value=50),
    LootEntry("thermite_01",        "Termite",              ItemType.CONSUMABLE, 1, 1, 0.18, damage=80, value=60),
    LootEntry("grenade_01",         "Granata Flash",        ItemType.CONSUMABLE, 1, 1, 0.15, damage=50, value=90),
    LootEntry("c4_01",              "Carica C4",            ItemType.CONSUMABLE, 1, 1, 0.10, damage=150, value=120),
    LootEntry("piranha_solution",   "Piranha Solution",     ItemType.CONSUMABLE, 1, 1, 0.10, damage=10, value=40),
    LootEntry("scrap_metal",        "Rottame",              ItemType.MATERIAL, 1, 2, 0.18, value=10),
    LootEntry("carburante_01",      "Carburante",           ItemType.MATERIAL, 1, 1, 0.05, value=20),
    LootEntry("polvere_ruggine_01", "Polvere di Ruggine",   ItemType.MATERIAL, 1, 1, 0.04, value=8),
    LootEntry("alluminio_01",       "Alluminio",            ItemType.MATERIAL, 1, 1, 0.03, value=10),
    LootEntry("carbone_01",         "Carbone",              ItemType.MATERIAL, 1, 1, 0.03, value=8),
    LootEntry("gunpowder_01",       "Polvere da Sparo",     ItemType.MATERIAL, 1, 1, 0.02, value=25),
    LootEntry("ammo_01",            "Munizioni",            ItemType.MATERIAL, 1, 3, 0.05, value=5),
    LootEntry("kevlar_scrap",       "Fibre Kevlar",         ItemType.MATERIAL, 1, 1, 0.02, value=18),
    LootEntry("electronics_01",     "Componenti Bio-Tech",  ItemType.MATERIAL, 1, 1, 0.02, value=45),
    LootEntry("junk_electronics",   "Elettronica Rotta",    ItemType.MATERIAL, 1, 2, 0.03, value=2),
]

CAMPI_LOOT: list[LootEntry] = [
    LootEntry("food_01",            "Razioni",              ItemType.CONSUMABLE, 2, 5, 0.38, hp_restore=10, value=15),
    LootEntry("food_02",            "Cibo in Scatola",      ItemType.CONSUMABLE, 1, 3, 0.24, hp_restore=15, value=20),
    LootEntry("junk_01",            "Junk Vario",           ItemType.MATERIAL, 1, 2, 0.16, value=1),
    LootEntry("junk_can",           "Lattina Vuota",        ItemType.MATERIAL, 1, 2, 0.14, value=1),
    LootEntry("junk_cloth",         "Straccio Sporco",      ItemType.MATERIAL, 1, 2, 0.12, value=1),
    LootEntry("stracci_01",         "Stracci",              ItemType.MATERIAL, 1, 2, 0.10, value=2),
    ]

SOLIDALI_BATTLE_LOOT: list = [
    LootEntry("medkit_01",       "Kit medico",          ItemType.CONSUMABLE, 1, 2, 0.28, hp_restore=30, value=40),
    LootEntry("bandage_01",      "Bende Mediche",       ItemType.CONSUMABLE, 1, 3, 0.22, hp_restore=15, value=12),
    LootEntry("antibiotics_01",  "Antibiotici",         ItemType.CONSUMABLE, 1, 2, 0.18, hp_restore=20, value=50),
    LootEntry("medkit_advanced", "Kit med. avanzato",   ItemType.CONSUMABLE, 1, 1, 0.10, hp_restore=60, value=80),
    LootEntry("food_01",         "Razioni",             ItemType.CONSUMABLE, 1, 2, 0.08, hp_restore=10, value=15),
    LootEntry("chem_01",         "Reagente",            ItemType.MATERIAL,   1, 2, 0.06, value=20),
    LootEntry("alcol_01",        "Alcol",               ItemType.MATERIAL,   1, 2, 0.04, value=12),
    LootEntry("stracci_01",      "Stracci",             ItemType.MATERIAL,   1, 2, 0.02, value=2),
    LootEntry("pistol_01",       "Pistola arrugginita", ItemType.WEAPON,     1, 1, 0.01, damage=15, value=60),
    LootEntry("improvised_knife","Coltello Improvvisato",ItemType.WEAPON,    1, 1, 0.01, damage=14, value=8),
]

ERRANTI_BATTLE_LOOT: list = [
    LootEntry("molotov_cocktail","Cocktail Molotov",    ItemType.CONSUMABLE, 1, 2, 0.25, damage=40, value=35),
    LootEntry("battle_explosive","Esplosivo Combatt.",  ItemType.CONSUMABLE, 1, 2, 0.20, damage=60, value=50),
    LootEntry("grenade_01",      "Granata Flash",       ItemType.CONSUMABLE, 1, 1, 0.16, damage=50, value=90),
    LootEntry("piranha_solution","Piranha Solution",    ItemType.CONSUMABLE, 1, 1, 0.12, damage=10, value=40),
    LootEntry("thermite_01",     "Termite",             ItemType.CONSUMABLE, 1, 1, 0.08, damage=80, value=60),
    LootEntry("zolfo_01",        "Zolfo",               ItemType.MATERIAL,   1, 2, 0.07, value=12),
    LootEntry("nitrato_01",      "Nitrato di Potassio", ItemType.MATERIAL,   1, 2, 0.06, value=18),
    LootEntry("carbone_01",      "Carbone",             ItemType.MATERIAL,   1, 2, 0.04, value=8),
    LootEntry("gunpowder_01",    "Polvere da Sparo",    ItemType.MATERIAL,   1, 1, 0.02, value=25),
]

DANNATI_BATTLE_LOOT: list = [
    LootEntry("improvised_club", "Mazza di Fortuna",    ItemType.WEAPON,     1, 1, 0.22, damage=18, value=10),
    LootEntry("improvised_knife","Coltello Improvvisato",ItemType.WEAPON,    1, 1, 0.20, damage=14, value=8),
    LootEntry("pistol_01",       "Pistola arrugginita", ItemType.WEAPON,     1, 1, 0.14, damage=15, value=60),
    LootEntry("pistol_02",       "Pistola leggera",     ItemType.WEAPON,     1, 1, 0.08, damage=25, value=60),
    LootEntry("recovered",       "Arma Recuperata",     ItemType.WEAPON,     1, 1, 0.06, damage=20, value=200),
    LootEntry("heavy_rifle_01",  "Fucile d'Assalto Pesante", ItemType.WEAPON,1, 1, 0.06, damage=80, value=200),
    LootEntry("thermite_01",     "Termite",             ItemType.CONSUMABLE, 1, 1, 0.12, damage=80, value=60),
    LootEntry("c4_01",           "Carica C4",           ItemType.CONSUMABLE, 1, 1, 0.08, damage=150, value=120),
    LootEntry("grenade_01",      "Granata Flash",       ItemType.CONSUMABLE, 1, 1, 0.08, damage=50, value=90),
    LootEntry("molotov_cocktail","Cocktail Molotov",    ItemType.CONSUMABLE, 1, 1, 0.06, damage=40, value=35),
    LootEntry("ammo_01",         "Munizioni",           ItemType.MATERIAL,   3, 8, 0.04, value=5),
]

RAZZIATORI_BATTLE_LOOT: list = [
    LootEntry("pistol_01",       "Pistola arrugginita", ItemType.WEAPON,     1, 1, 0.16, damage=15, value=60),
    LootEntry("pistol_02",       "Pistola leggera",     ItemType.WEAPON,     1, 1, 0.10, damage=25, value=60),
    LootEntry("improvised_club", "Mazza di Fortuna",    ItemType.WEAPON,     1, 1, 0.12, damage=18, value=10),
    LootEntry("improvised_knife","Coltello Improvvisato",ItemType.WEAPON,    1, 1, 0.10, damage=14, value=8),
    LootEntry("recovered",       "Arma Recuperata",     ItemType.WEAPON,     1, 1, 0.05, damage=20, value=200),
    LootEntry("heavy_rifle_01",  "Fucile d'Assalto Pesante", ItemType.WEAPON,1, 1, 0.04, damage=80, value=200),
    LootEntry("grenade_01",      "Granata Flash",       ItemType.CONSUMABLE, 1, 2, 0.10, damage=50, value=90),
    LootEntry("molotov_cocktail","Cocktail Molotov",    ItemType.CONSUMABLE, 1, 1, 0.08, damage=40, value=35),
    LootEntry("thermite_01",     "Termite",             ItemType.CONSUMABLE, 1, 1, 0.06, damage=80, value=60),
    LootEntry("c4_01",           "Carica C4",           ItemType.CONSUMABLE, 1, 1, 0.04, damage=150, value=120),
    LootEntry("medkit_01",       "Kit medico",          ItemType.CONSUMABLE, 1, 1, 0.06, hp_restore=30, value=40),
    LootEntry("bandage_01",      "Bende Mediche",       ItemType.CONSUMABLE, 1, 2, 0.05, hp_restore=15, value=12),
    LootEntry("ammo_01",         "Munizioni",           ItemType.MATERIAL,   3, 10, 0.06, value=5),
    LootEntry("scrap_metal",     "Rottame",             ItemType.MATERIAL,   1, 3,  0.05, value=10),
    LootEntry("chem_01",         "Reagente",            ItemType.MATERIAL,   1, 2,  0.04, value=20),
    LootEntry("kevlar_scrap",    "Fibre Kevlar",        ItemType.MATERIAL,   1, 2,  0.03, value=18),
    LootEntry("electronics_01",  "Componenti Bio-Tech", ItemType.MATERIAL,   1, 1,  0.01, value=45),
]

INFETTO_LOOT: list = [
    LootEntry("junk_01",         "Junk Vario",          ItemType.MATERIAL,   1, 1, 0.28, value=1),
    LootEntry("junk_can",        "Lattina Vuota",       ItemType.MATERIAL,   1, 1, 0.24, value=1),
    LootEntry("junk_cloth",      "Straccio Sporco",     ItemType.MATERIAL,   1, 1, 0.20, value=1),
    LootEntry("stracci_01",      "Stracci",             ItemType.MATERIAL,   1, 1, 0.14, value=2),
    LootEntry("scrap_metal",     "Rottame",             ItemType.MATERIAL,   1, 1, 0.10, value=10),
    LootEntry("alcol_01",        "Alcol",               ItemType.MATERIAL,   1, 1, 0.04, value=12),
]

ORDA_LOOT: list = [
    LootEntry("junk_01",         "Junk Vario",          ItemType.MATERIAL,   1, 2, 0.26, value=1),
    LootEntry("junk_can",        "Lattina Vuota",       ItemType.MATERIAL,   1, 2, 0.22, value=1),
    LootEntry("junk_cloth",      "Straccio Sporco",     ItemType.MATERIAL,   1, 2, 0.18, value=1),
    LootEntry("junk_electronics","Elettronica Rotta",   ItemType.MATERIAL,   1, 2, 0.12, value=2),
    LootEntry("stracci_01",      "Stracci",             ItemType.MATERIAL,   1, 2, 0.10, value=2),
    LootEntry("scrap_metal",     "Rottame",             ItemType.MATERIAL,   1, 2, 0.08, value=10),
    LootEntry("alcol_01",        "Alcol",               ItemType.MATERIAL,   1, 1, 0.04, value=12),
]

CORAZZATO_LOOT: list = [
    LootEntry("pistol_01",        "Pistola arrugginita",      ItemType.WEAPON, 1, 1, 0.30, damage=15, value=60),
    LootEntry("pistol_02",        "Pistola leggera",          ItemType.WEAPON, 1, 1, 0.16, damage=25, value=60),
    LootEntry("improvised_club",  "Mazza di Fortuna",         ItemType.WEAPON, 1, 1, 0.28, damage=18, value=10),
    LootEntry("heavy_rifle_01",   "Fucile d'Assalto Pesante", ItemType.WEAPON, 1, 1, 0.18, damage=80, value=200),
    LootEntry("improvised_knife", "Coltello Improvvisato",    ItemType.WEAPON, 1, 1, 0.14, damage=14, value=8),
    LootEntry("recovered",        "Arma Recuperata",          ItemType.WEAPON, 1, 1, 0.07, damage=20, value=200),
    LootEntry("kevlar_scrap",     "Fibre Kevlar",             ItemType.MATERIAL, 1, 2, 0.07, value=18),
    LootEntry("ammo_01",          "Munizioni",                ItemType.MATERIAL, 2, 5, 0.03, value=5),
]

GIGANTE_LOOT: list = [
    LootEntry("heavy_rifle_01",  "Fucile d'Assalto Pesante", ItemType.WEAPON,     1, 1, 0.28, damage=80, value=200),
    LootEntry("improvised_club", "Mazza di Fortuna",         ItemType.WEAPON,     1, 1, 0.20, damage=18, value=10),
    LootEntry("pistol_01",       "Pistola arrugginita",      ItemType.WEAPON,     1, 1, 0.16, damage=15, value=60),
    LootEntry("rail_gun",        "Rail Gun",                 ItemType.WEAPON,     1, 1, 0.04, damage=55, value=200),
    LootEntry("acid_gun",        "Pistola Acida",            ItemType.WEAPON,     1, 1, 0.03, damage=20, value=200),
    LootEntry("thermite_01",     "Termite",                  ItemType.CONSUMABLE, 1, 1, 0.12, damage=80, value=60),
    LootEntry("c4_01",           "Carica C4",                ItemType.CONSUMABLE, 1, 1, 0.08, damage=150, value=120),
    LootEntry("grenade_01",      "Granata Flash",            ItemType.CONSUMABLE, 1, 1, 0.07, damage=50, value=90),
    LootEntry("battle_explosive","Esplosivo Combatt.",        ItemType.CONSUMABLE, 1, 1, 0.05, damage=60, value=50),
    LootEntry("medkit_01",       "Kit medico",               ItemType.CONSUMABLE, 1, 1, 0.02, hp_restore=30, value=40),
    LootEntry("bandage_01",      "Bende Mediche",            ItemType.CONSUMABLE, 1, 1, 0.01, hp_restore=15, value=12),
    LootEntry("antibiotics_01",  "Antibiotici",              ItemType.CONSUMABLE, 1, 1, 0.01, hp_restore=20, value=50),
]













class TrashLootStrategy(ILootStrategy):
    """Strategy loot per zone degradate: solo materiali di scarso valore (junk, stracci)."""
    def generate(self, ctx: LootContext) -> list[Item]:
        pool = [
            Item("junk_01",    "Junk Vario",      ItemType.MATERIAL, quantity=random.randint(1, 3), value=1),
            Item("junk_cloth", "Straccio Sporco", ItemType.MATERIAL, quantity=random.randint(1, 2), value=1),
            Item("stracci_01", "Stracci",         ItemType.MATERIAL, quantity=1, value=2),
            Item("junk_can",   "Lattina Vuota",   ItemType.MATERIAL, quantity=random.randint(1, 2), value=1),
            Item("zolfo_01",   "Zolfo",           ItemType.MATERIAL, quantity=1, value=12),
        ]
        return random.sample(pool, random.randint(1, 2))






class ScaffaleStrategy(ILootStrategy):
    """Scaffali: material medie %, consumabili bassi, arma minima %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(SCAFFALE_LOOT, num_rolls=3)


class ScatoleStrategy(ILootStrategy):
    """Scatole: material medie %, consumabili bassi, arma minima %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(SCATOLE_LOOT, num_rolls=3)


class AutoStrategy(ILootStrategy):
    """Auto: material medie %, consumabili bassi, arma minima %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(AUTO_LOOT, num_rolls=3)



class FarmaciaStrategy(ILootStrategy):
    """Farmacia: curativi alta %, offensivi minima %, NO armi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(FARMACIA_LOOT, num_rolls=4)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class NegozioStrategy(ILootStrategy):
    """Negozio: cibo garantito (food_01 + food_02), consumabili molto basse %, NO armi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items: list[Item] = [
            Item("food_01", "Razioni",         ItemType.CONSUMABLE,
                 quantity=random.randint(2, 4), hp_restore=10, value=15),
            Item("food_02", "Cibo in Scatola", ItemType.CONSUMABLE,
                 quantity=random.randint(1, 3), hp_restore=15, value=20),
        ]
        items.extend(_roll_table(NEGOZIO_LOOT, num_rolls=2))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class SupermercatoStrategy(ILootStrategy):
    """Supermercato: cibo garantito, consumabili molto basse %, NO armi."""
    def __init__(self) -> None:
        self._occupant_type: str = "empty"

    def randomize_occupants(self) -> str:
        self._occupant_type = randomize_supermarket_occupants()
        return self._occupant_type

    def generate(self, ctx: LootContext) -> list[Item]:
        items: list[Item] = [
            Item("food_01", "Razioni",         ItemType.CONSUMABLE,
                 quantity=random.randint(2, 5), hp_restore=10, value=15),
            Item("food_02", "Cibo in Scatola", ItemType.CONSUMABLE,
                 quantity=random.randint(2, 4), hp_restore=15, value=20),
        ]
        items.extend(_roll_table(SUPERMERCATO_LOOT, num_rolls=3))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        if self._occupant_type == "razziatori":
            items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                              quantity=random.randint(5, 15), value=5))
        elif self._occupant_type == "zombie_horde":
            items = [it for it in items if it.item_id not in ("food_01", "food_02")]
        return items


class CasaStrategy(ILootStrategy):
    """Casa: cibo garantito, curativi medie %, NO offensivi, 1 arma minima %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items: list[Item] = [
            Item("food_01", "Razioni",         ItemType.CONSUMABLE,
                 quantity=random.randint(1, 3), hp_restore=10, value=15),
        ]
        if random.random() < 0.6:
            items.append(Item("food_02", "Cibo in Scatola", ItemType.CONSUMABLE,
                              quantity=random.randint(1, 2), hp_restore=15, value=20))
        items.extend(_roll_table(CASA_LOOT, num_rolls=3))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class ScuolaStrategy(ILootStrategy):
    """Scuola: curativi + offensivi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(SCUOLA_LOOT, num_rolls=3)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class StazioneGasStrategy(ILootStrategy):
    """Stazione Gas: curativi + offensivi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(STAZIONE_GAS_LOOT, num_rolls=3)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class VigiliDelFuocoStrategy(ILootStrategy):
    """Vigili del Fuoco: curativi + offensivi + max 2 armi % molto basse."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(VIGILI_FUOCO_LOOT, num_rolls=4)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        weapon_count = sum(1 for it in items if it.item_type == ItemType.WEAPON)
        if weapon_count > 2:
            kept, removed = [], []
            wc = 0
            for it in items:
                if it.item_type == ItemType.WEAPON:
                    if wc < 2:
                        kept.append(it)
                        wc += 1
                else:
                    kept.append(it)
            items = kept
        return items


class StazioneBenzinaStrategy(ILootStrategy):
    """Stazione di Benzina: curativi + offensivi + max 2 armi % molto basse."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(STAZIONE_BENZINA_LOOT, num_rolls=4)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        weapon_count = sum(1 for it in items if it.item_type == ItemType.WEAPON)
        if weapon_count > 2:
            kept, wc = [], 0
            for it in items:
                if it.item_type == ItemType.WEAPON:
                    if wc < 2:
                        kept.append(it)
                        wc += 1
                else:
                    kept.append(it)
            items = kept
        return items


class CasermaStrategy(ILootStrategy):
    """Caserma: solo offensivi + armi, medie quantità e %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(CASERMA_LOOT, num_rolls=4)
        items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                          quantity=random.randint(5, 12), value=5))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class StazionePoliziaStrategy(ILootStrategy):
    """Stazione di Polizia: solo offensivi + armi, medie quantità e %."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(STAZIONE_POLIZIA_LOOT, num_rolls=4)
        items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                          quantity=random.randint(4, 10), value=5))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class GrattacieloStrategy(ILootStrategy):
    """Grattacielo: tutto, quantità basse, % medie."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(GRATTACIELO_LOOT, num_rolls=3)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class CassaforteStrategy(ILootStrategy):
    """Cassaforte: SOLO data_chip + heavy_rifle_01 (garantiti)."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return [
            Item("data_chip",     "Chip dati",               ItemType.KEY_ITEM, quantity=1, value=50),
            Item("heavy_rifle_01","Fucile d'Assalto Pesante", ItemType.WEAPON,   quantity=1, value=200, damage=80),
        ]


class TendaDormitorioHangarStrategy(ILootStrategy):
    """Tenda/Dormitorio/Hangar: tutto, armi con tante munizioni, offensivi abbondanti, curativi pochi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(TENDA_DORMITORIO_HANGAR_LOOT, num_rolls=4)
        has_weapon = any(it.item_type == ItemType.WEAPON for it in items)
        if has_weapon:
            items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                              quantity=random.randint(10, 25), value=5))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class FattoriaStrategy(ILootStrategy):
    """Fattoria: tanto cibo + 1 arma garantita."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items: list[Item] = [
            Item("food_01", "Razioni",         ItemType.CONSUMABLE,
                 quantity=random.randint(3, 6), hp_restore=10, value=15),
            Item("food_02", "Cibo in Scatola", ItemType.CONSUMABLE,
                 quantity=random.randint(2, 4), hp_restore=15, value=20),
        ]
        items.extend(_roll_table(FATTORIA_LOOT, num_rolls=2))
        arma = random.choice([
            Item("improvised_club",  "Mazza di Fortuna",      ItemType.WEAPON, quantity=1, damage=18, value=10),
            Item("improvised_knife", "Coltello Improvvisato", ItemType.WEAPON, quantity=1, damage=14, value=8),
            Item("pistol_01",        "Pistola arrugginita",   ItemType.WEAPON, quantity=1, damage=15, value=60),
        ])
        items.append(arma)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class MulinoStrategy(ILootStrategy):
    """Mulino: tanti offensivi, armi con poche munizioni, curativi. % basse."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(MULINO_LOOT, num_rolls=4)
        has_weapon = any(it.item_type == ItemType.WEAPON for it in items)
        if has_weapon:
            items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                              quantity=random.randint(1, 4), value=5))
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items


class LaboratorioStrategy(ILootStrategy):
    """Laboratorio: key_card_01 garantita, 0 armi, qualche offensivo + curativi, NO cibo."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items: list[Item] = [
            Item("key_card_01", "Badge Accesso", ItemType.KEY_ITEM, quantity=1, value=0),
        ]
        items.extend(_roll_table(LABORATORIO_LOOT, num_rolls=3))
        items = [it for it in items if it.item_type != ItemType.WEAPON]
        return items


class CentraleElettricaStrategy(ILootStrategy):
    """Centrale Elettrica: solo offensivi, % basse."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(CENTRALE_ELETTRICA_LOOT, num_rolls=3)
        return items


class CampiStrategy(ILootStrategy):
    """Campi: solo cibo + material."""
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(CAMPI_LOOT, num_rolls=3)
        _maybe_add_material(items, UNIVERSAL_MATERIAL_POOL, rolls=1)
        return items



class CommonHouseLootStrategy(ILootStrategy):
    """Strategy loot per case comuni: mix di consumabili curativi e materiali."""
    NUM_ROLLS: int = 3
    def generate(self, ctx: LootContext) -> list[Item]:
        return generate_zone_loot("common_house", num_rolls=self.NUM_ROLLS)


class PharmacyLootStrategy(ILootStrategy):
    """Strategy loot per farmacie: priorità a kit medici e antibiotici."""
    NUM_ROLLS: int = 4
    def generate(self, ctx: LootContext) -> list[Item]:
        return generate_zone_loot("pharmacy", num_rolls=self.NUM_ROLLS)


class CityHighLootStrategy(ILootStrategy):
    """Strategy loot per zone urbane di alto valore: reagenti e componenti avanzati."""
    NUM_ROLLS: int = 3
    def generate(self, ctx: LootContext) -> list[Item]:
        items = generate_zone_loot("city_high", num_rolls=self.NUM_ROLLS)
        if random.random() < 0.15:
            items.append(Item("key_card_01", "Badge Accesso", ItemType.KEY_ITEM, quantity=1, value=0))
        return items


class MilitaryLootStrategy(ILootStrategy):
    """Strategy loot per zone militari: munizioni, esplosivi e armamenti."""
    NUM_ROLLS: int = 4
    def generate(self, ctx: LootContext) -> list[Item]:
        items = generate_zone_loot("military", num_rolls=self.NUM_ROLLS)
        items.append(Item("ammo_01", "Munizioni", ItemType.MATERIAL,
                          quantity=random.randint(3, 8), value=5))
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        if not gs.flags.get("landmine_looted", False):
            items.append(Item("landmine_01", "Mina Militare", ItemType.CONSUMABLE,
                              quantity=1, value=150, damage=150))
            gs.flags["landmine_looted"] = True
        return items


class RuralLootStrategy(ILootStrategy):
    """Strategy loot per zone rurali: cibo, materiali naturali e attrezzi improvvisati."""
    NUM_ROLLS: int = 3
    def generate(self, ctx: LootContext) -> list[Item]:
        return generate_zone_loot("rural", num_rolls=self.NUM_ROLLS)


class IndustrialLootStrategy(ILootStrategy):
    """Strategy loot per zone industriali: rottami, alluminio e carburante."""
    NUM_ROLLS: int = 3
    def generate(self, ctx: LootContext) -> list[Item]:
        items = generate_zone_loot("industrial", num_rolls=self.NUM_ROLLS)
        items.append(Item("scrap_metal", "Rottame", ItemType.MATERIAL, quantity=2, value=10))
        return items

class SolidaliBattleStrategy(ILootStrategy):
    """Solidali: curativi (alta %), mat. per curabili (media %), arma (rara)."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(SOLIDALI_BATTLE_LOOT, num_rolls=3)


class ErrantiBattleStrategy(ILootStrategy):
    """Erranti: offensivi (alta %), materiali per craftarli (media %). No armi, no cura."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(ERRANTI_BATTLE_LOOT, num_rolls=3)


class DannatiBattleStrategy(ILootStrategy):
    """Dannati: solo armi + offensivi. No curativi, no risorse."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(DANNATI_BATTLE_LOOT, num_rolls=3)


class RazziatoriiBattleStrategy(ILootStrategy):
    """Razziatori: pool ricco con tutto tranne junk."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(RAZZIATORI_BATTLE_LOOT, num_rolls=4)


class InfettoBattleStrategy(ILootStrategy):
    """Infetto: solo materiali/junk in quantità scarsa (1–2 item)."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(INFETTO_LOOT, num_rolls=2)


class OrdaBattleStrategy(ILootStrategy):
    """Orda: stesso tipo dell'Infetto, quantità maggiore (3–5 item)."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(ORDA_LOOT, num_rolls=4)


class CorazzatoBattleStrategy(ILootStrategy):
    """
    Corazzato: quasi garantisce un'arma.
    Restituisce anche la flag 'has_weapon' nel context tramite side-effect
    su ctx (aggiunta dell'attributo dynamic 'dropped_weapon').
    Il chiamante (_on_battle_ended) legge questa info per attivare il toggle.
    """
    def generate(self, ctx: LootContext) -> list[Item]:
        items = _roll_table(CORAZZATO_LOOT, num_rolls=3)
        ctx.dropped_weapon = any(it.item_type == ItemType.WEAPON for it in items)
        return items


class GiganteBattleStrategy(ILootStrategy):
    """Gigante di Carne: boss loot — armi alte %, offensivi medi, curativi minimi."""
    def generate(self, ctx: LootContext) -> list[Item]:
        return _roll_table(GIGANTE_LOOT, num_rolls=4)



class LootSystem(ISystem):
    """ISystem che gestisce i loot spot della mappa e coordina le strategie di loot.

        Si iscrive agli eventi di zona e dispatcha la strategy appropriata
        in base al tipo di zona (``zone_type``) dello spot interagito.
    """
    def __init__(self) -> None:
        self._bus = None
        self._supermarket_strategy = SupermercatoStrategy()

        self._strategies: dict[str, ILootStrategy] = {
            "environmental":        EnvironmentalLootStrategy(),
            "battle_solidali":    SolidaliBattleStrategy(),
            "battle_erranti":     ErrantiBattleStrategy(),
            "battle_dannati":     DannatiBattleStrategy(),
            "battle_razziatori":  RazziatoriiBattleStrategy(),

            "battle_infetto":     InfettoBattleStrategy(),
            "battle_orda":        OrdaBattleStrategy(),
            "battle_corazzato":   CorazzatoBattleStrategy(),
            "battle_gigante":     GiganteBattleStrategy(),
            "trash":                TrashLootStrategy(),

            "shelf":                ScaffaleStrategy(),
            "scaffale":             ScaffaleStrategy(),
            "box":                  ScatoleStrategy(),
            "scatole":              ScatoleStrategy(),
            "car":                  AutoStrategy(),
            "auto":                 AutoStrategy(),
            "crate":                ScatoleStrategy(),

            "farmacia":             FarmaciaStrategy(),
            "pharmacy":             FarmaciaStrategy(),
            "negozio":              NegozioStrategy(),
            "shop":                 NegozioStrategy(),
            "supermercato":         self._supermarket_strategy,
            "supermarket":          self._supermarket_strategy,
            "casa":                 CasaStrategy(),
            "common_house":         CasaStrategy(),
            "city_common":          CasaStrategy(),
            "scuola":               ScuolaStrategy(),
            "school":               ScuolaStrategy(),
            "stazione_gas":         StazioneGasStrategy(),
            "gas_station":          StazioneGasStrategy(),
            "vigili_fuoco":         VigiliDelFuocoStrategy(),
            "fire_station":         VigiliDelFuocoStrategy(),
            "stazione_benzina":     StazioneBenzinaStrategy(),
            "benzina":              StazioneBenzinaStrategy(),
            "caserma":              CasermaStrategy(),
            "barracks":             CasermaStrategy(),
            "stazione_polizia":     StazionePoliziaStrategy(),
            "police_station":       StazionePoliziaStrategy(),
            "grattacielo":          GrattacieloStrategy(),
            "city_high":            GrattacieloStrategy(),
            "cassaforte":           CassaforteStrategy(),
            "safe":                 CassaforteStrategy(),
            "tenda":                TendaDormitorioHangarStrategy(),
            "tent":                 TendaDormitorioHangarStrategy(),
            "dormitorio":           TendaDormitorioHangarStrategy(),
            "dorm":                 TendaDormitorioHangarStrategy(),
            "hangar":               TendaDormitorioHangarStrategy(),
            "fattoria":             FattoriaStrategy(),
            "farm":                 FattoriaStrategy(),
            "rural":                FattoriaStrategy(),
            "mulino":               MulinoStrategy(),
            "mill":                 MulinoStrategy(),
            "laboratorio":          LaboratorioStrategy(),
            "lab":                  LaboratorioStrategy(),
            "chem_lab":             LaboratorioStrategy(),
            "centrale_elettrica":   CentraleElettricaStrategy(),
            "power_plant":          CentraleElettricaStrategy(),
            "campi":                CampiStrategy(),
            "fields":               CampiStrategy(),

            "military":             MilitaryLootStrategy(),
            "industrial":           IndustrialLootStrategy(),
            "bushes":               TrashLootStrategy(),
        }
        self._bus: EventBus | None = None

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus
        bus.subscribe(EventType.BATTLE_ENDED,  self._on_battle_ended)
        bus.subscribe(EventType.LEVEL_LOADED,  self._on_level_loaded)

    def cleanup(self) -> None:
        if self._bus:
            self._bus.unsubscribe(EventType.BATTLE_ENDED, self._on_battle_ended)
            self._bus.unsubscribe(EventType.LEVEL_LOADED, self._on_level_loaded)

    def _on_battle_ended(self, data: dict) -> None:
        """
        Genera loot post-battaglia per ogni nemico sconfitto.

        - Fazioni (Solidali/Erranti/Dannati/Razziatori): usa tabella specifica.
        - Zombie generico (faction_name == "zombie"): discrimina per nome:
            "Infetto"        → InfettoBattleStrategy
            "Orda"           → OrdaBattleStrategy
            "Corazzato"      → CorazzatoBattleStrategy (+ flag toggle arma)
            "Gigante di Carne" → GiganteBattleStrategy
        - Il risultato è accumulato in gs.pending_battle_loot.
        - La flag corazzato_weapon_dropped viene scritta in gs.flags
        per permettere alla UI di mostrare/nascondere il toggle arma.
        """
        if data.get("result") != "victory" or not self._bus:
            return

        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()

        all_items: list[Item] = []
        corazzato_weapon_dropped: bool = False

        FACTION_STRATEGY_MAP = {
            "solidali":    "battle_solidali",
            "erranti":     "battle_erranti",
            "dannati":     "battle_dannati",
            "razziatori":  "battle_razziatori",
        }

        ZOMBIE_NAME_MAP = {
            "infetto":          "battle_infetto",
            "orda":             "battle_orda",
            "corazzato":        "battle_corazzato",
            "gigante di carne": "battle_gigante",
        }

        for enemy in data.get("enemies", []):
            faction_val = (
                getattr(enemy, "faction_name", None)
                or getattr(enemy, "faction", "")
            ).lower()

            enemy_name = getattr(enemy, "name", "").lower()

            if faction_val == "zombie":
                strategy_key = ZOMBIE_NAME_MAP.get(enemy_name, "battle_infetto")
            else:
                strategy_key = FACTION_STRATEGY_MAP.get(faction_val, "environmental")

            ctx = LootContext(faction=faction_val, source_type="faction")

            strat = self._strategies.get(strategy_key)
            if strat is None:
                strat = EnvironmentalLootStrategy()

            items = strat.generate(ctx)
            all_items.extend(items)

            if strategy_key == "battle_corazzato":
                if getattr(ctx, "dropped_weapon", False):
                    corazzato_weapon_dropped = True

        gs.flags["corazzato_weapon_available"] = corazzato_weapon_dropped

        if all_items:
            gs.pending_battle_loot = self._aggregate_and_cap_loot(all_items, max_slots=7)
    def _on_level_loaded(self, data: dict) -> None:
        occupant = self._supermarket_strategy.randomize_occupants()
        if self._bus:
            self._bus.publish(EventType.SUPERMARKET_OCCUPANT_SET, {"occupant_type": occupant})

    def generate_loot(self, ctx: LootContext) -> list[Item]:
        strat = (self._strategies.get(ctx.zone_type)
                 or self._strategies.get(ctx.source_type)
                 or EnvironmentalLootStrategy())
        items = strat.generate(ctx)

        return self._aggregate_and_cap_loot(items, max_slots=7)
    def loot_location(self, zone_type: str, player_luck: int = 0) -> list[Item]:
        ctx = LootContext(zone_type=zone_type, player_luck=player_luck)
        return self.generate_loot(ctx)

    def _aggregate_and_cap_loot(self, items: list[Item], max_slots: int = 7) -> list[Item]:
        """
        Riunisce gli item con lo stesso item_id sommando le quantità.
        Limita l'array finale a un massimo di 'max_slots' oggetti (mantenendo i primi generati).
        """
        aggregated: dict[str, Item] = {}
        for it in items:
            if it.item_id in aggregated:
                aggregated[it.item_id].quantity += it.quantity
            else:
                aggregated[it.item_id] = it

        result = list(aggregated.values())

        return result[:max_slots]