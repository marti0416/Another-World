"""
loot_protocols.py — Strategie di generazione del loot (pattern Strategy GoF).

Struttura
---------
- ``LootContext``             : DTO con il contesto della sessione di loot.
- ``ILootStrategy``           : interfaccia Strategy GoF.
- ``EnvironmentalLootStrategy``: loot da fonti ambientali (contenitori, stanze).
- ``FactionDropStrategy``     : loot da nemici sconfitti appartenenti a una fazione.

Le strategie sono intercambiabili: il LootSystem può scegliere la strategia
appropriata in base al contesto (tipo di fonte, distretto, fazione).
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

from game.model.item import Item, ItemType


# ---------------------------------------------------------------------------
# DTO contesto
# ---------------------------------------------------------------------------

@dataclass
class LootContext:
    """Contesto passato alla strategia di loot per personalizzare la generazione.

    Attributes:
        district:    Identificatore del distretto corrente (es. "CENTER_LAB").
        faction:     Nome della fazione del nemico sconfitto (es. "erranti").
        source_type: Tipo di sorgente loot ("environmental", "faction_drop", ecc.).
        zone_type:   Tipo di zona (es. "default", "safe_zone").
        player_luck: Modificatore di fortuna del giocatore (riserva per usi futuri).
    """
    district:    str = "CENTER_LAB"
    faction:     str = "erranti"
    source_type: str = "environmental"
    zone_type:   str = "default"
    player_luck: int = 0


# ---------------------------------------------------------------------------
# Interfaccia Strategy
# ---------------------------------------------------------------------------

class ILootStrategy(ABC):
    """Strategy astratta GoF per la generazione del loot.

    Ogni ConcreteStrategy implementa ``generate()`` con la logica specifica
    di selezione e quantità degli oggetti.
    """

    @abstractmethod
    def generate(self, ctx: LootContext) -> list[Item]:
        """Genera e restituisce la lista di Item da consegnare al giocatore.

        Args:
            ctx: Contesto della sessione di loot con distretto, fazione, ecc.

        Returns:
            Lista di ``Item`` (può essere vuota in caso di loot fallito).
        """
        ...


# ---------------------------------------------------------------------------
# ConcreteStrategy — loot ambientale
# ---------------------------------------------------------------------------

class EnvironmentalLootStrategy(ILootStrategy):
    """Loot generato da fonti ambientali (contenitori, stanze abbandonate, ecc.).

    La selezione degli oggetti dipende dal distretto corrente:
    - CENTER_LAB        : chip dati e reagenti chimici.
    - INDUSTRIAL_FACTORY: rottami, alluminio e carbone.
    - Altri            : pool casuale di oggetti generici.
    """

    def generate(self, ctx: LootContext) -> list[Item]:
        """Genera loot in base al distretto attivo nel ``LootContext``.

        Args:
            ctx: Contesto con il distretto corrente.

        Returns:
            Lista di ``Item`` specifici per il distretto, o campione casuale
            dal pool generico per distretti non mappati.
        """
        if ctx.district == "CENTER_LAB":
            return [
                Item("data_chip",   "Chip dati",  ItemType.KEY_ITEM, quantity=1, value=50),
                Item("chem_01",     "Reagente",   ItemType.MATERIAL, quantity=2, value=20),
            ]
        elif ctx.district == "INDUSTRIAL_FACTORY":
            return [
                Item("scrap_metal", "Rottame",    ItemType.MATERIAL, quantity=3, value=10),
                Item("alluminio_01","Alluminio",  ItemType.MATERIAL, quantity=2, value=10),
                Item("carbone_01",  "Carbone",    ItemType.MATERIAL, quantity=2, value=8),
            ]

        # Pool generico per distretti non mappati
        pool = [
            Item("scrap_metal", "Rottame",    ItemType.MATERIAL,   quantity=random.randint(1, 2), value=10),
            Item("junk_01",     "Junk Vario", ItemType.MATERIAL,   quantity=random.randint(1, 2), value=1),
            Item("food_01",     "Razioni",    ItemType.CONSUMABLE, quantity=1, hp_restore=10, value=15),
            Item("alcol_01",    "Alcol",      ItemType.MATERIAL,   quantity=1, value=12),
        ]
        return random.sample(pool, random.randint(1, 2))


# ---------------------------------------------------------------------------
# ConcreteStrategy — loot da fazione
# ---------------------------------------------------------------------------

class FactionDropStrategy(ILootStrategy):
    """Loot generato dalla sconfitta di un nemico appartenente a una fazione.

    Ogni fazione ha un set di drop tematici:
    - Razziatori: pistola e munizioni.
    - Solidali  : kit medico e razioni.
    - Altre fazioni / default: rottami generici.
    """

    def generate(self, ctx: LootContext) -> list[Item]:
        """Genera loot in base alla fazione del nemico sconfitto.

        Args:
            ctx: Contesto con il nome della fazione (case-insensitive).

        Returns:
            Lista di ``Item`` tematici per la fazione, o rottami di default.
        """
        faction = ctx.faction.lower() if ctx.faction else ""

        if faction == "razziatori":
            return [
                Item("pistol_01", "Pistola arrugginita", ItemType.WEAPON,    quantity=1, value=60, damage=15),
                Item("ammo_01",   "Munizioni",           ItemType.MATERIAL,  quantity=10, value=5),
            ]
        if faction == "solidali":
            return [
                Item("medkit_01", "Kit medico",          ItemType.CONSUMABLE, quantity=2, hp_restore=30, value=40),
                Item("food_01",   "Razioni",             ItemType.CONSUMABLE, quantity=3, value=15),
            ]

        # Drop di default per fazioni non mappate (es. Erranti, Dannati)
        return [Item("scrap_metal", "Rottame", ItemType.MATERIAL, quantity=2, value=10)]
