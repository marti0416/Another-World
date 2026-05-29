"""
item_registry.py — Registry globale degli Item prototipo (pattern Prototype GoF).

Il registry memorizza un'istanza prototipo per ogni ``item_id`` conosciuto.
``Inventory.from_dict()`` lo usa per recuperare i valori base degli oggetti
durante il caricamento di un salvataggio, evitando di hardcodare le statistiche
degli item in più posti.

Flusso tipico
-------------
    register_default_items()   # chiamato all'avvio del gioco
    proto = get_item_proto("medkit_01")
    item  = proto.clone()      # Prototype GoF
"""

from game.model.item import Item, ItemType

# Dizionario interno: item_id → Item prototipo
_REGISTRY: dict[str, Item] = {}


def register_default_items() -> None:
    """Popola il registry globale con tutti gli Item del gioco.

    Va chiamata una sola volta all'avvio (es. in ``GameManager.initialize()``).
    In caso di ``item_id`` duplicati, l'ultima definizione sovrascrive la precedente.
    """
    defaults = [
        # --- Consumabili curativi ---
        Item("medkit_01",        "Kit medico",           ItemType.CONSUMABLE, hp_restore=30,  value=40),
        Item("medkit_advanced",  "Kit med. avanzato",    ItemType.CONSUMABLE, hp_restore=60,  value=80),
        Item("antibiotics_01",   "Antibiotici",          ItemType.CONSUMABLE, hp_restore=20,  value=50),
        Item("bandage_01",       "Bende Mediche",        ItemType.CONSUMABLE, hp_restore=15,  value=12),
        Item("food_01",          "Razioni",              ItemType.CONSUMABLE, hp_restore=10,  value=15),
        Item("food_02",          "Cibo in Scatola",      ItemType.CONSUMABLE, hp_restore=15,  value=20),

        # --- Consumabili offensivi ---
        Item("molotov_cocktail", "Cocktail Molotov",     ItemType.CONSUMABLE, damage=15,  value=35),
        Item("thermite_01",      "Termite",              ItemType.CONSUMABLE, damage=15,  value=60),
        Item("c4_01",            "Carica C4",            ItemType.CONSUMABLE, damage=50,  value=120),
        Item("piranha_solution", "Piranha Solution",     ItemType.CONSUMABLE, damage=10,  value=40),
        Item("battle_explosive", "Esplosivo Combatt.",   ItemType.CONSUMABLE, damage=25,  value=50),
        Item("grenade_01",       "Granata Flash",        ItemType.CONSUMABLE, damage=0,   value=90),
        Item("landmine_01",      "Mina Militare",        ItemType.CONSUMABLE, damage=80,  value=150),

        # --- Armi ---
        Item("pistol_01",        "Pistola arrugginita",  ItemType.WEAPON,     damage=20,  value=60),
        Item("light_pistol",     "Pistola leggera",      ItemType.WEAPON,     damage=15,  value=60),
        Item("heavy_rifle_01",   "Fucile d'Assalto",     ItemType.WEAPON,     damage=25,  value=200),
        Item("recovered_weapon", "Arma Recuperata",      ItemType.WEAPON,     damage=25,  value=200),
        Item("rail_gun",         "Rail Gun",             ItemType.WEAPON,     damage=35,  value=200),
        Item("acid_gun",         "Acid Gun",             ItemType.WEAPON,     damage=15,  value=200),
        Item("improvised_club",  "Mazza di Fortuna",     ItemType.WEAPON,     damage=18,  value=10),
        Item("improvised_knife", "Coltello Improvvisato",ItemType.WEAPON,     damage=14,  value=8),
        Item("antimatter_grenade","Granata Antimateria", ItemType.WEAPON,     damage=50,  value=500),
        Item("incendiary_missile","Missile Incendiario", ItemType.WEAPON,     damage=45,  value=400),
        Item("artillery",        "Designatore Artiglieria",ItemType.WEAPON,   damage=65,  value=800),
        Item("thermobaric_rocket","Razzo Termobarico",   ItemType.WEAPON,     damage=95,  value=600),

        # --- Materiali da crafting ---
        Item("chem_01",          "Reagente",             ItemType.MATERIAL,   value=20),
        Item("scrap_metal",      "Rottame",              ItemType.MATERIAL,   value=10),
        Item("alcol_01",         "Alcol",                ItemType.MATERIAL,   value=12),
        Item("carburante_01",    "Carburante",           ItemType.MATERIAL,   value=20),
        Item("stracci_01",       "Stracci",              ItemType.MATERIAL,   value=2),
        Item("carbone_01",       "Carbone",              ItemType.MATERIAL,   value=8),
        Item("zolfo_01",         "Zolfo",                ItemType.MATERIAL,   value=12),
        Item("nitrato_01",       "Nitrato di Potassio",  ItemType.MATERIAL,   value=18),
        Item("gunpowder_01",     "Polvere da Sparo",     ItemType.MATERIAL,   value=25),
        Item("polvere_ruggine_01","Polvere di Ruggine",  ItemType.MATERIAL,   value=8),
        Item("alluminio_01",     "Alluminio",            ItemType.MATERIAL,   value=10),
        Item("junk_01",          "Junk Vario",           ItemType.MATERIAL,   value=1),
        Item("electronics_01",   "Componenti Bio-Tech",  ItemType.MATERIAL,   value=45),
        Item("kevlar_scrap",     "Fibre Kevlar",         ItemType.MATERIAL,   value=18),
        Item("ammo_01",          "Munizioni",            ItemType.MATERIAL,   value=5),

        # --- Junk (bassa rilevanza) ---
        Item("junk_can",         "Lattina Vuota",        ItemType.MATERIAL,   value=1),
        Item("junk_cloth",       "Straccio Sporco",      ItemType.MATERIAL,   value=1),
        Item("junk_electronics", "Elettronica Rotta",    ItemType.MATERIAL,   value=2),

        # --- Oggetti chiave ---
        Item("data_chip",        "Chip dati",            ItemType.KEY_ITEM,   value=50),
        Item("key_card_01",      "Badge Accesso",        ItemType.KEY_ITEM,   value=0),

        # --- Mina militare (versione potenziata da crafting) ---
        Item("landmine_01",      "Mina Militare",        ItemType.CONSUMABLE, damage=150, value=150),
    ]

    for it in defaults:
        _REGISTRY[it.item_id] = it


def get_item_proto(item_id: str) -> Item | None:
    """Restituisce il prototipo dell'Item con l'id specificato.

    Il prototipo non va modificato direttamente; usare ``proto.clone()``
    per ottenere una copia indipendente (pattern Prototype GoF).

    Args:
        item_id: Identificatore dell'oggetto (es. "medkit_01").

    Returns:
        L'``Item`` prototipo, oppure ``None`` se l'id non è registrato.
    """
    return _REGISTRY.get(item_id)
