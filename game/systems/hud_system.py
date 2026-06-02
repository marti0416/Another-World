"""
hud_system.py — Pannello HUD inventario co-op e sistema HUD (ISystem).

Struttura
---------
- ``InventorySlot``       : singolo slot HUD con quantità o usi rimanenti.
- ``HUDInventoryPanel``   : pannello di N slot per un personaggio (rendering testo/pygame).
- ``SharedComponent``     : azione/oggetto condiviso tra i due personaggi.
- ``SharedComponentPanel``: pannello dei pulsanti co-op (mappa, crafting, ecc.).
- ``CoopInteractionSystem``: trasferimento oggetti e uso Medkit sul partner.
- ``HUDSystem``           : ISystem che orchestra tutto e si iscrive all'EventBus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.model.item import Item, ItemType, Inventory


# ---------------------------------------------------------------------------
# Slot inventario
# ---------------------------------------------------------------------------

@dataclass
class InventorySlot:
    """Singolo slot visibile nell'HUD di un personaggio.

    Può rappresentare un oggetto con quantità libera (``uses_remaining == -1``)
    oppure un oggetto con un numero fisso di usi (es. arma speciale con cariche).

    Attributes:
        slot_index:     Indice dello slot (0-based).
        item:           L'oggetto contenuto, o ``None`` se vuoto.
        uses_remaining: Usi rimanenti (-1 = nessun limite, usa la quantità).
    """
    slot_index:     int
    item:           Item | None = None
    uses_remaining: int         = -1

    @property
    def is_empty(self) -> bool:
        """``True`` se lo slot non contiene nessun oggetto."""
        return self.item is None

    @property
    def display_qty(self) -> str:
        """Stringa mostrata nell'HUD accanto all'icona dell'oggetto.

        - Se ``uses_remaining != -1``: mostra ``"X usi"``.
        - Altrimenti: mostra ``"×N"`` con la quantità dell'oggetto.
        """
        if self.item is None:
            return ""
        if self.uses_remaining >= 0:
            return f"{self.uses_remaining} usi"
        return f"×{self.item.quantity}"

    @property
    def display_name(self) -> str:
        """Nome dell'oggetto o ``"(vuoto)"`` se lo slot è libero."""
        return self.item.name if self.item else "(vuoto)"

    def set_item(self, item: Item | None, uses: int = -1) -> None:
        """Imposta l'oggetto nello slot.

        Args:
            item: L'oggetto da inserire (``None`` per svuotare lo slot).
            uses: Numero di usi rimanenti (-1 = usa la quantità dell'Item).
        """
        self.item = item
        self.uses_remaining = uses

    def consume_use(self) -> bool:
        """Consuma un uso dell'oggetto nello slot.

        - Se ``uses_remaining == -1``: decrementa la quantità; se scende a 0
          rimuove l'oggetto dallo slot.
        - Se ``uses_remaining > 0``: decrementa gli usi; se scende a 0
          rimuove l'oggetto.

        Returns:
            ``True`` se l'uso è stato consumato con successo,
            ``False`` se lo slot è vuoto o gli usi sono esauriti.
        """
        if self.item is None:
            return False
        if self.uses_remaining == -1:
            if self.item.quantity > 1:
                self.item.quantity -= 1
                return True
            self.item = None
            return False
        if self.uses_remaining > 0:
            self.uses_remaining -= 1
            if self.uses_remaining == 0:
                self.item = None
            return True
        return False


# ---------------------------------------------------------------------------
# Pannello inventario HUD
# ---------------------------------------------------------------------------

class HUDInventoryPanel:
    """Pannello HUD che visualizza gli slot rapidi di un personaggio.

    Gestisce N slot visibili (default 6) popolati dall'inventario del personaggio.
    Espone rendering testuale (debug/fallback) e rendering pygame.

    Attributes:
        DEFAULT_SLOTS: Numero di slot di default per pannello.
    """

    DEFAULT_SLOTS: int = 6

    def __init__(self, character_name: str, slots: int = DEFAULT_SLOTS) -> None:
        self.character_name = character_name
        self.slots: list[InventorySlot] = [
            InventorySlot(i) for i in range(slots)
        ]

    def populate_from_inventory(self, inventory: Inventory) -> None:
        """Popola gli slot HUD con gli oggetti correnti dell'inventario.

        Gli slot in eccesso rispetto agli oggetti presenti vengono svuotati.

        Args:
            inventory: L'inventario del personaggio da cui leggere gli oggetti.
        """
        items = inventory.all_items()
        for i, slot in enumerate(self.slots):
            if i < len(items):
                slot.set_item(items[i])
            else:
                slot.set_item(None)

    def get_slot(self, index: int) -> InventorySlot | None:
        """Restituisce lo slot all'indice specificato, o ``None`` se fuori range.

        Args:
            index: Indice dello slot (0-based).
        """
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def render_text(self) -> list[str]:
        """Genera la rappresentazione testuale dell'HUD (debug/fallback senza pygame).

        Returns:
            Lista di stringhe, una per slot più una intestazione.
        """
        lines = [f"── Inventario {self.character_name} ──"]
        for slot in self.slots:
            if slot.is_empty:
                lines.append(f"  [{slot.slot_index}] (vuoto)")
            else:
                lines.append(f"  [{slot.slot_index}] {slot.display_name:<20} {slot.display_qty}")
        return lines

    def render_pygame(self, surface, font, x: int, y: int,
                      slot_w: int = 80, slot_h: int = 80,
                      selected_index: int = -1) -> list[tuple]:
        """Rendering pygame degli slot inventario con quantità visibile.

        Restituisce una lista di ``(index, Rect)`` per il hit-testing
        (selezione slot con click del mouse).

        Nota: Richiede pygame importato. Se non disponibile, restituisce lista vuota.

        Args:
            surface:        Surface pygame di destinazione.
            font:           Font pygame per il testo degli slot.
            x, y:           Posizione topleft del pannello.
            slot_w/slot_h:  Dimensioni di ogni slot in pixel.
            selected_index: Indice dello slot selezionato (-1 = nessuno).

        Returns:
            Lista di tuple ``(slot_index, pygame.Rect)`` per ogni slot.
        """
        try:
            import pygame
        except ImportError:
            return []

        rects: list[tuple] = []
        GAP = 4

        for i, slot in enumerate(self.slots):
            sx = x + i * (slot_w + GAP)
            sy = y
            rect = pygame.Rect(sx, sy, slot_w, slot_h)

            color = (60, 60, 80) if i != selected_index else (80, 120, 160)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            pygame.draw.rect(surface, (100, 100, 130), rect, 2, border_radius=6)

            if not slot.is_empty:
                name_surf = font.render(slot.display_name[:10], True, (220, 220, 220))
                surface.blit(name_surf, (sx + 4, sy + 4))

                qty_surf = font.render(slot.display_qty, True, (255, 214, 0))
                surface.blit(qty_surf, (sx + slot_w - qty_surf.get_width() - 4,
                                        sy + slot_h - qty_surf.get_height() - 4))

            rects.append((i, rect))

        return rects


# ---------------------------------------------------------------------------
# Componenti condivisi co-op
# ---------------------------------------------------------------------------

@dataclass
class SharedComponent:
    """Azione o funzionalità condivisa tra entrambi i personaggi nel pannello HUD.

    Attributes:
        component_id: Identificatore univoco (es. "map", "crafting").
        label:        Nome visualizzato nel pulsante.
        icon_key:     Chiave dello sprite icona nell'AssetLoader.
        is_enabled:   ``False`` durante il combattimento (Barricata, Trappole).
        callback:     Callable opzionale invocato da ``activate()``.
    """
    component_id: str
    label:        str
    icon_key:     str
    is_enabled:   bool             = True
    callback:     Callable | None  = field(default=None, repr=False)

    def activate(self) -> str:
        """Attiva il componente invocando il callback se presente.

        Returns:
            Messaggio di stato dell'attivazione.
        """
        if not self.is_enabled:
            return f"[{self.label}] Non disponibile."
        if self.callback:
            return self.callback() or f"[{self.label}] attivato."
        return f"[{self.label}] attivato."


class SharedComponentPanel:
    """Pannello dei pulsanti co-op condivisi tra i due personaggi.

    Gestisce i pulsanti Mappa, Diario, Crafting, Radio, Barricata, Trappole,
    Partner. Durante il combattimento, Barricata e Trappole vengono disabilitate
    da ``HUDSystem._on_combat_start()``.
    """

    def __init__(self) -> None:
        self._components: dict[str, SharedComponent] = {}

    def register(self, component: SharedComponent) -> None:
        """Registra un componente nel pannello.

        Args:
            component: Il componente da aggiungere.
        """
        self._components[component.component_id] = component

    def get(self, component_id: str) -> SharedComponent | None:
        """Restituisce un componente per ID, o ``None`` se non presente."""
        return self._components.get(component_id)

    def enable(self, component_id: str) -> None:
        """Abilita un componente (rende il pulsante cliccabile).

        Args:
            component_id: ID del componente da abilitare.
        """
        c = self._components.get(component_id)
        if c:
            c.is_enabled = True

    def disable(self, component_id: str) -> None:
        """Disabilita un componente (es. Barricata e Trappole in combattimento).

        Args:
            component_id: ID del componente da disabilitare.
        """
        c = self._components.get(component_id)
        if c:
            c.is_enabled = False

    def render_text(self) -> list[str]:
        """Rendering testuale del pannello per debug/fallback."""
        lines = ["── Componenti Condivisi ──"]
        for c in self._components.values():
            status = "✔" if c.is_enabled else "✖"
            lines.append(f"  [{status}] {c.label}")
        return lines

    def render_pygame(self, surface, font, x: int, y: int,
                      btn_w: int = 120, btn_h: int = 36) -> list[tuple]:
        """Rendering pygame dei pulsanti componenti condivisi.

        Args:
            surface:        Surface pygame di destinazione.
            font:           Font pygame per il testo dei pulsanti.
            x, y:           Posizione topleft del pannello.
            btn_w/btn_h:    Dimensioni di ogni pulsante in pixel.

        Returns:
            Lista di tuple ``(component_id, pygame.Rect)`` per hit-testing.
        """
        try:
            import pygame
        except ImportError:
            return []

        rects: list[tuple] = []
        GAP = 6
        for i, (cid, comp) in enumerate(self._components.items()):
            bx = x
            by = y + i * (btn_h + GAP)
            rect = pygame.Rect(bx, by, btn_w, btn_h)

            color = (40, 100, 60) if comp.is_enabled else (60, 40, 40)
            pygame.draw.rect(surface, color, rect, border_radius=5)
            pygame.draw.rect(surface, (90, 90, 110), rect, 1, border_radius=5)

            text_color = (220, 220, 220) if comp.is_enabled else (120, 120, 120)
            label_surf = font.render(comp.label, True, text_color)
            surface.blit(label_surf,
                         (bx + (btn_w - label_surf.get_width()) // 2,
                          by + (btn_h - label_surf.get_height()) // 2))

            rects.append((cid, rect))

        return rects

    def build_default_components(self) -> None:
        """Costruisce e registra i componenti co-op di default.

        Componenti registrati: Mappa, Diario, Crafting, Radio,
        Barricata, Trappole, Partner.
        Barricata e Trappole iniziano abilitati e vengono disabilitati
        da ``HUDSystem._on_combat_start()`` durante il combattimento.
        """
        defaults = [
            SharedComponent("map",       "Mappa",    "icon_map"),
            SharedComponent("quests",    "Diario",   "icon_quests"),
            SharedComponent("crafting",  "Crafting", "icon_crafting"),
            SharedComponent("radio",     "Radio",    "icon_radio"),
            SharedComponent("barricade", "Barricata","icon_barricade"),
            SharedComponent("traps",     "Trappole", "icon_traps"),
            SharedComponent("partner",   "Partner",  "icon_partner"),
        ]
        for c in defaults:
            self.register(c)


# ---------------------------------------------------------------------------
# Interazione co-op
# ---------------------------------------------------------------------------

class CoopInteractionSystem:
    """Gestisce il trasferimento oggetti e l'uso del Medkit sul partner.

    Le interazioni sono limitate a una distanza massima di ``MAX_INTERACT_DIST``
    tile tra i due personaggi. L'uso del Medkit è consentito solo se il partner
    è in stato critico (HP < 30% del massimo).

    Attributes:
        MAX_INTERACT_DIST: Distanza massima di interazione in tile.
        CRITICAL_HP_RATIO: Soglia HP (rapporto) sotto cui il partner è "in crisi".
    """

    MAX_INTERACT_DIST: int   = 2
    CRITICAL_HP_RATIO: float = 0.30

    def __init__(self) -> None:
        self._bus: EventBus | None = None

    def set_bus(self, bus: EventBus) -> None:
        """Imposta l'EventBus per pubblicare gli eventi di interazione.

        Args:
            bus: L'istanza condivisa dell'EventBus.
        """
        self._bus = bus

    @staticmethod
    def _distance(pos1: tuple, pos2: tuple) -> float:
        """Distanza euclidea tra due posizioni tile.

        Args:
            pos1, pos2: Coppie (col, row).

        Returns:
            Distanza in tile.
        """
        import math
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _are_adjacent(self, pos1: tuple, pos2: tuple) -> bool:
        """Verifica se due posizioni sono entro ``MAX_INTERACT_DIST`` tile.

        Returns:
            ``True`` se la distanza è ≤ ``MAX_INTERACT_DIST``.
        """
        return self._distance(pos1, pos2) <= self.MAX_INTERACT_DIST

    def give_item_to_partner(self,
                             giver, giver_pos: tuple,
                             receiver, receiver_pos: tuple,
                             item_id: str, qty: int = 1) -> dict:
        """Trasferisce un oggetto dall'inventario di ``giver`` a ``receiver``.

        La distanza tra i due personaggi deve essere ≤ ``MAX_INTERACT_DIST``.
        Pubblica ``ITEM_TRANSFERRED`` sull'EventBus in caso di successo.

        Args:
            giver:        Personaggio che cede l'oggetto.
            giver_pos:    Posizione tile di ``giver``.
            receiver:     Personaggio che riceve l'oggetto.
            receiver_pos: Posizione tile di ``receiver``.
            item_id:      ID dell'oggetto da trasferire.
            qty:          Quantità da trasferire (default 1).

        Returns:
            Dict con chiavi ``success`` (bool) e ``message`` (str).
        """
        if not self._are_adjacent(giver_pos, receiver_pos):
            dist = self._distance(giver_pos, receiver_pos)
            return {
                "success": False,
                "message": (f"Troppo lontano dal partner "
                            f"({dist:.1f} tile, max {self.MAX_INTERACT_DIST})."),
            }

        item = giver.inventory.get_item(item_id)
        if not item:
            return {"success": False,
                    "message": f"'{item_id}' non trovato nell'inventario di {giver.name}."}
        if item.quantity < qty:
            return {"success": False,
                    "message": f"Quantità insufficiente: {item.quantity}/{qty}."}

        giver.inventory.remove_item(item_id, qty)
        from game.model.item import Item as ItemClass
        transferred = ItemClass(item.item_id, item.name, item.item_type,
                                quantity=qty, value=item.value,
                                hp_restore=item.hp_restore, damage=item.damage,
                                defense=item.defense)
        receiver.inventory.add_item(transferred)

        if self._bus:
            self._bus.publish(EventType.ITEM_TRANSFERRED, {
                "from": giver.name, "to": receiver.name,
                "item_id": item_id, "qty": qty,
            })

        return {
            "success": True,
            "message": f"✔ {giver.name} dà {item.name}×{qty} a {receiver.name}.",
        }

    def use_medkit_on_partner(self,
                              healer, healer_pos: tuple,
                              partner, partner_pos: tuple,
                              medkit_id: str = "medkit_01") -> dict:
        """Usa un Medkit per curare il partner in stato critico.

        Controlla che:
        - I due personaggi siano entro ``MAX_INTERACT_DIST`` tile.
        - Il partner abbia HP < ``CRITICAL_HP_RATIO`` × HP massimi.
        - ``healer`` abbia un Medkit nell'inventario.

        Pubblica ``PARTNER_HEALED`` in caso di successo.

        Args:
            healer:     Il personaggio che cura.
            healer_pos: Posizione tile del guaritore.
            partner:    Il personaggio da curare.
            partner_pos:Posizione tile del partner.
            medkit_id:  ID dell'oggetto curativo da cercare prima (default "medkit_01").

        Returns:
            Dict con chiavi ``success`` (bool) e ``message`` (str).
        """
        if not self._are_adjacent(healer_pos, partner_pos):
            return {"success": False,
                    "message": "Troppo lontano dal partner per usare il Medkit."}

        hp_ratio = partner.stats.hp / partner.stats.max_hp
        if hp_ratio > self.CRITICAL_HP_RATIO:
            return {
                "success": False,
                "message": (f"{partner.name} non è in stato critico "
                            f"({partner.stats.hp}/{partner.stats.max_hp} HP). "
                            f"Medkit disponibili per HP < {int(self.CRITICAL_HP_RATIO*100)}%."),
            }

        medkit = (healer.inventory.get_item(medkit_id)
                  or healer.inventory.get_item("medkit_advanced"))
        if not medkit:
            return {"success": False,
                    "message": f"{healer.name} non ha Medkit nell'inventario."}

        healed = partner.stats.heal(medkit.hp_restore)
        healer.inventory.remove_item(medkit.item_id, 1)

        if self._bus:
            self._bus.publish(EventType.PARTNER_HEALED, {
                "healer": healer.name, "partner": partner.name,
                "healed": healed, "medkit_id": medkit.item_id,
            })

        return {
            "success": True,
            "message": (f"✔ {healer.name} usa {medkit.name} su {partner.name}: "
                        f"+{healed} HP ({partner.stats.hp}/{partner.stats.max_hp})."),
        }


# ---------------------------------------------------------------------------
# Sistema HUD (ISystem)
# ---------------------------------------------------------------------------

class HUDSystem(ISystem):
    """Orchestratore dell'HUD co-op.

    Gestisce i pannelli inventario, i componenti condivisi e le interazioni
    partner. Si iscrive a ``START_ENCOUNTER`` e ``BATTLE_ENDED`` per
    disabilitare/riabilitare Barricata e Trappole durante il combattimento.

    Attributes:
        COMBAT_LOCKED_COMPONENTS: Tuple degli ID componenti bloccati in combattimento.
    """

    COMBAT_LOCKED_COMPONENTS = ("barricade", "traps")

    def __init__(self) -> None:
        self._bus:        EventBus | None    = None
        self.panel_Rivet  = HUDInventoryPanel("Rivet")
        self.panel_Echo   = HUDInventoryPanel("Echo")
        self.shared_panel = SharedComponentPanel()
        self.coop         = CoopInteractionSystem()
        self._in_combat:  bool = False

    def initialize(self, bus: EventBus) -> None:
        """Costruisce i componenti condivisi di default e si iscrive agli eventi.

        Args:
            bus: L'istanza condivisa dell'EventBus.
        """
        self._bus = bus
        self.coop.set_bus(bus)
        self.shared_panel.build_default_components()
        bus.subscribe(EventType.START_ENCOUNTER, self._on_combat_start)
        bus.subscribe(EventType.BATTLE_ENDED,    self._on_combat_end)
        bus.subscribe(EventType.ITEM_PICKUP,     self._on_item_pickup)
        bus.subscribe(EventType.QUEST_AVAILABLE, self._on_quest_available)
        bus.subscribe(EventType.QUEST_COMPLETED, self._on_quest_completed)
        bus.subscribe(EventType.QUEST_FAILED,    self._on_quest_failed)

    def cleanup(self) -> None:
        """Rimuove tutte le iscrizioni dall'EventBus."""
        if self._bus:
            self._bus.unsubscribe(EventType.START_ENCOUNTER, self._on_combat_start)
            self._bus.unsubscribe(EventType.BATTLE_ENDED,    self._on_combat_end)
            self._bus.unsubscribe(EventType.ITEM_PICKUP,     self._on_item_pickup)
            self._bus.unsubscribe(EventType.QUEST_AVAILABLE, self._on_quest_available)
            self._bus.unsubscribe(EventType.QUEST_COMPLETED, self._on_quest_completed)
            self._bus.unsubscribe(EventType.QUEST_FAILED,    self._on_quest_failed)

    # --- Handler eventi ---

    def _on_combat_start(self, data: dict) -> None:
        """Disabilita Barricata e Trappole all'inizio del combattimento."""
        self._in_combat = True
        for cid in self.COMBAT_LOCKED_COMPONENTS:
            self.shared_panel.disable(cid)

    def _on_combat_end(self, data: dict) -> None:
        """Riabilita Barricata e Trappole al termine del combattimento."""
        self._in_combat = False
        for cid in self.COMBAT_LOCKED_COMPONENTS:
            self.shared_panel.enable(cid)

    def _on_item_pickup(self, data: dict) -> None:
        """Aggiorna il pannello HUD quando viene raccolto un oggetto (placeholder)."""
        pass

    def _on_quest_available(self, data: dict) -> None:
        """Mostra un flash UI quando una nuova quest diventa disponibile."""
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        gs.flash(f"Nuova quest: {data.get('title', '')}", 120)

    def _on_quest_completed(self, data: dict) -> None:
        """Mostra un flash UI quando una quest è completata con successo."""
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        gs.flash(f"Quest completata: {data.get('title', '')}!", 150)

    def _on_quest_failed(self, data: dict) -> None:
        """Mostra un flash UI quando una quest fallisce."""
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        gs.flash(f"Quest fallita: {data.get('quest_id', '')}", 120)

    # --- API pubblica ---

    def refresh_panels(self, Rivet, Echo) -> None:
        """Aggiorna i pannelli HUD con i dati correnti dell'inventario.

        Da chiamare ogni frame o ogni volta che l'inventario cambia.

        Args:
            Rivet: Oggetto ``Character`` di Rivet.
            Echo:  Oggetto ``Character`` di Echo.
        """
        self.panel_Rivet.populate_from_inventory(Rivet.inventory)
        self.panel_Echo.populate_from_inventory(Echo.inventory)

    def is_component_enabled(self, component_id: str) -> bool:
        """Verifica se un componente condiviso è attualmente abilitato.

        Args:
            component_id: ID del componente.

        Returns:
            ``True`` se abilitato, ``False`` se disabilitato o non trovato.
        """
        comp = self.shared_panel.get(component_id)
        return comp.is_enabled if comp else False

    def debug_render(self, Rivet, Echo) -> list[str]:
        """Rendering testuale completo per debug senza pygame.

        Aggiorna prima i pannelli, poi concatena: inventario Rivet,
        inventario Echo, componenti condivisi, stato combattimento.

        Args:
            Rivet: Oggetto ``Character`` di Rivet.
            Echo:  Oggetto ``Character`` di Echo.

        Returns:
            Lista di stringhe pronte per la stampa.
        """
        self.refresh_panels(Rivet, Echo)
        lines: list[str] = []
        lines += self.panel_Rivet.render_text()
        lines += self.panel_Echo.render_text()
        lines += self.shared_panel.render_text()
        lines.append(f"Combattimento attivo: {self._in_combat}")
        return lines
