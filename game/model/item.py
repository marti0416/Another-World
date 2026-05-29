"""
item.py — Modello degli oggetti (Item) e dell'inventario (Inventory).

Struttura
---------
- ``ItemType``   : enum dei tipi di oggetto.
- ``ICloneable`` : interfaccia Prototype GoF.
- ``Item``       : dataclass che implementa Prototype (``clone()``).
- ``Inventory``  : contenitore di Item con gestione del peso massimo,
                   serializzazione JSON e ricostruzione da dict.
"""

from __future__ import annotations
import copy
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Enum tipo oggetto
# ---------------------------------------------------------------------------

class ItemType(Enum):
    """Categoria di un oggetto nell'inventario.

    Usata per filtrare gli oggetti per tipo (es. ``Inventory.get_by_type()``).
    """
    CONSUMABLE = auto()   # Oggetti usabili (medkit, cibo, esplosivi, ecc.)
    MATERIAL   = auto()   # Materiali da crafting (rottami, reagenti, ecc.)
    WEAPON     = auto()   # Armi (anche quelle gestite da WeaponSystem)
    ARMOR      = auto()   # Armature (non ancora implementate)
    KEY_ITEM   = auto()   # Oggetti chiave di trama (chip dati, badge accesso)


# ---------------------------------------------------------------------------
# Interfaccia Prototype
# ---------------------------------------------------------------------------

class ICloneable(ABC):
    """Interfaccia Prototype GoF.

    Il client chiama sempre ``obj.clone()`` per ottenere una copia indipendente.
    La semantica della copia (shallow vs deep) è responsabilità dell'oggetto stesso.
    """

    @abstractmethod
    def clone(self) -> "ICloneable":
        """Restituisce una copia indipendente di questo oggetto."""
        ...


# ---------------------------------------------------------------------------
# Prodotto — Item
# ---------------------------------------------------------------------------

@dataclass
class Item(ICloneable):
    """Oggetto dell'inventario, implementa il pattern Prototype GoF.

    Tutti i campi sono primitivi, quindi la copia superficiale (``copy.copy``)
    è sufficiente per garantire l'indipendenza del clone.

    Attributes:
        item_id:    Identificatore univoco (es. "medkit_01", "chem_01").
        name:       Nome visualizzato nell'interfaccia.
        item_type:  Categoria dell'oggetto (``ItemType``).
        quantity:   Quantità posseduta (default 1).
        value:      Valore in crediti per vendita/acquisto.
        hp_restore: HP ripristinati quando l'oggetto viene usato (0 se non applicabile).
        damage:     Danno inflitto quando l'oggetto viene usato (0 se non applicabile).
        defense:    Bonus di difesa quando l'oggetto è equipaggiato (0 se non applicabile).
    """

    item_id:    str
    name:       str
    item_type:  ItemType
    quantity:   int   = 1
    value:      int   = 0
    hp_restore: int   = 0
    damage:     int   = 0
    defense:    int   = 0

    def clone(self) -> "Item":
        """Prototype: copia superficiale dell'Item (tutti i campi sono primitivi).

        Returns:
            Nuovo oggetto ``Item`` indipendente con gli stessi valori.
        """
        return copy.copy(self)

    def __repr__(self) -> str:
        return f"Item({self.name} x{self.quantity})"


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class Inventory:
    """Contenitore di oggetti con vincolo di peso massimo.

    Gli oggetti sono indicizzati per ``item_id``; aggiungere un oggetto
    già presente incrementa la sua ``quantity`` invece di duplicarlo.

    Args:
        max_weight: Peso massimo consentito (0 = nessun limite).
    """

    def __init__(self, max_weight: int = 0) -> None:
        self._items: dict[str, Item] = {}
        self.max_weight = max_weight

    @property
    def current_weight(self) -> int:
        """Peso attuale dell'inventario (1 unità di peso per ogni item, indipendentemente dal tipo)."""
        return sum(i.quantity for i in self._items.values())

    @property
    def is_overweight(self) -> bool:
        """``True`` se il peso attuale supera il limite massimo."""
        return self.max_weight > 0 and self.current_weight > self.max_weight

    def can_add(self, qty: int = 1) -> bool:
        """Verifica se c'è spazio per aggiungere ``qty`` unità aggiuntive.

        Args:
            qty: Numero di unità da aggiungere (default 1).

        Returns:
            ``True`` se l'aggiunta non supererebbe il limite di peso,
            o se non c'è limite (``max_weight <= 0``).
        """
        if self.max_weight <= 0:
            return True
        return self.current_weight + qty <= self.max_weight

    def add_item(self, item: Item) -> None:
        """Aggiunge un oggetto all'inventario, incrementando la quantità se già presente.

        Args:
            item: L'oggetto da aggiungere (viene copiato se non già presente).
        """
        if item.item_id in self._items:
            self._items[item.item_id].quantity += item.quantity
        else:
            self._items[item.item_id] = Item(
                item.item_id, item.name, item.item_type,
                item.quantity, item.value,
                item.hp_restore, item.damage, item.defense
            )

    def get_item(self, item_id: str) -> Item | None:
        """Restituisce l'Item con l'id specificato, o ``None`` se assente.

        Args:
            item_id: Identificatore dell'oggetto.
        """
        return self._items.get(item_id)

    def remove_item(self, item_id: str, qty: int = 1) -> bool:
        """Rimuove ``qty`` unità dell'oggetto specificato dall'inventario.

        Se la quantità scende a 0 (o meno), l'oggetto viene rimosso completamente.

        Args:
            item_id: Identificatore dell'oggetto da rimuovere.
            qty:     Numero di unità da rimuovere (default 1).

        Returns:
            ``True`` se la rimozione è avvenuta con successo,
            ``False`` se l'oggetto non esiste o la quantità è insufficiente.
        """
        it = self._items.get(item_id)
        if not it or it.quantity < qty:
            return False
        it.quantity -= qty
        if it.quantity <= 0:
            del self._items[item_id]
        return True

    def get_by_type(self, item_type: ItemType) -> list[Item]:
        """Restituisce tutti gli oggetti di un determinato tipo.

        Args:
            item_type: Il tipo di oggetto da filtrare (``ItemType``).

        Returns:
            Lista di ``Item`` con ``item_type`` corrispondente.
        """
        return [i for i in self._items.values() if i.item_type == item_type]

    def all_items(self) -> list[Item]:
        """Restituisce tutti gli oggetti presenti nell'inventario.

        Returns:
            Lista di tutti gli ``Item`` (ordine non garantito).
        """
        return list(self._items.values())

    def __len__(self) -> int:
        """Restituisce il numero totale di unità nell'inventario (somma delle quantità)."""
        return sum(i.quantity for i in self._items.values())

    def to_dict(self) -> dict:
        """Serializza l'inventario in un dict JSON-friendly per il salvataggio.

        Returns:
            Dizionario con chiavi ``max_weight`` e ``items`` (lista di dict per ogni Item).
        """
        return {
            "max_weight": self.max_weight,
            "items": [
                {
                    "item_id":   it.item_id,
                    "name":      it.name,
                    "item_type": it.item_type.name,
                    "quantity":  it.quantity,
                    "value":     it.value,
                    "hp_restore":it.hp_restore,
                    "damage":    it.damage,
                    "defense":   it.defense,
                }
                for it in self._items.values()
            ]
        }

    @classmethod
    def from_dict(cls, data) -> "Inventory":
        """Ricostruisce un ``Inventory`` da un dict serializzato (o lista legacy).

        Usa il registry degli item (``item_registry.get_item_proto()``) per
        recuperare i valori base degli oggetti; i valori del salvataggio
        sovrascrivono solo la quantità, non le statistiche prototipo.

        Args:
            data: Dict prodotto da ``to_dict()``, oppure lista di dict (formato legacy).

        Returns:
            Nuovo oggetto ``Inventory`` con tutti gli oggetti ripristinati.
        """
        from game.model.item_registry import get_item_proto
        if isinstance(data, dict):
            max_weight = data.get("max_weight", 0)
            items_data = data.get("items", [])
        else:
            # Formato legacy: lista di dict senza max_weight
            max_weight = 0
            items_data = data

        inv = cls(max_weight=max_weight)
        for d in items_data:
            item_id = d["item_id"]
            proto   = get_item_proto(item_id)

            try:
                itype = ItemType[d.get("item_type", "CONSUMABLE")]
            except KeyError:
                itype = ItemType.CONSUMABLE

            base_name       = proto.name       if proto else d.get("name", item_id)
            base_type       = proto.item_type  if proto else itype
            base_value      = proto.value      if proto else d.get("value", 0)
            base_hp_restore = proto.hp_restore if proto else d.get("hp_restore", 0)
            base_damage     = proto.damage     if proto else d.get("damage", 0)
            base_defense    = proto.defense    if proto else d.get("defense", 0)

            inv.add_item(Item(
                item_id   = item_id,
                name      = base_name,
                item_type = base_type,
                quantity  = d.get("quantity", 1),
                value     = base_value,
                hp_restore= base_hp_restore,
                damage    = base_damage,
                defense   = base_defense
            ))
        return inv
