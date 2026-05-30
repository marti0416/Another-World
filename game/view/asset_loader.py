"""
asset_loader.py — Caricamento e caching delle risorse grafiche e audio (AssetLoader).

Single point of loading per sprite, font, suoni e musica.
Tutte le Surface caricate sono memorizzate in dizionari interni;
le richieste successive alla stessa chiave restituiscono l'oggetto già caricato.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
import pygame

SCALE = 3
import sys as _sys


def _get_assets_root() -> Path:
    if hasattr(_sys, '_MEIPASS'):
        return Path(_sys._MEIPASS) / "assets"
    return Path(__file__).parent.parent.parent / "assets"


ASSETS = _get_assets_root()



class AssetCache:
    """Flyweight Factory — unica cache centralizzata per tutte le Surface.

    Sostituisce le 4 cache distinte presenti nel codice originale:
      - asset_loader._cache          (Surface grezze + scalate)
      - renderer._cache              (Surface grezze + tile estratti)
      - map_loader._ts_cache         (tileset grezzi)
      - map_loader._tile_cache       (tile estratti + scalati)

    Ogni Surface è caricata da disco una sola volta e condivisa tra tutti
    i client che la richiedono con la stessa chiave. La scala e la posizione
    (stato estrinseco) rimangono responsabilità del client.

    Tutti i metodi sono @classmethod: non è necessario istanziare la classe.
    """

    _surfaces:  dict[tuple, pygame.Surface] = {}
    _scaled:    dict[tuple, pygame.Surface] = {}
    _tiles:     dict[tuple, pygame.Surface] = {}

    _hits:   int = 0
    _misses: int = 0


    @classmethod
    def get_surface(cls, abs_path: str, alpha: bool = False) -> pygame.Surface:
        """Restituisce la Surface grezza per abs_path, caricandola una sola volta.

        Stato intrinseco: il contenuto del file PNG/JPG su disco.
        I client non devono modificare la Surface restituita — è condivisa.
        Per modifiche, usare .copy() esplicitamente.

        Args:
            abs_path: percorso assoluto del file immagine
            alpha:    True  → convert_alpha() (trasparenza per canale)
                      False → convert() + colorkey (0,0,0)
        """
        key = (abs_path, alpha)
        if key in cls._surfaces:
            cls._hits += 1
            return cls._surfaces[key]
        cls._misses += 1
        surf = pygame.image.load(abs_path)
        if alpha:
            surf = surf.convert_alpha()
        else:
            surf = surf.convert()
            surf.set_colorkey((0, 0, 0))
        cls._surfaces[key] = surf
        return surf


    @classmethod
    def get_scaled(cls, abs_path: str, scale: int,
                   alpha: bool = False) -> pygame.Surface:
        """Restituisce la Surface scalata a (w*scale, h*scale).

        La Surface grezza e quella scalata sono entrambe cached: se lo stesso
        asset viene richiesto a scale diverse (es. SCALE=3 in gioco, SCALE=1
        in minimap), ogni versione è tenuta in cache separatamente.

        Args:
            abs_path: percorso assoluto del file
            scale:    fattore di scala intero (1 = nessuna scala)
            alpha:    modalità alpha (passata a get_surface)
        """
        key = (abs_path, scale, alpha)
        if key in cls._scaled:
            cls._hits += 1
            return cls._scaled[key]
        cls._misses += 1
        raw = cls.get_surface(abs_path, alpha)
        if scale == 1:
            scaled = raw
        else:
            w, h = raw.get_size()
            scaled = pygame.transform.scale(raw, (w * scale, h * scale))
        cls._scaled[key] = scaled
        return scaled


    @classmethod
    def get_tile(cls, surface: pygame.Surface,
                 col: int, row: int,
                 tw: int = 16, th: int = 16,
                 scale: int = 1) -> Optional[pygame.Surface]:
        """Estrae e scala un singolo tile da un tileset Surface.

        La chiave include id(surface) invece del path: questo garantisce
        correttezza anche se due tileset distinti condividono le stesse
        coordinate (col, row).

        Args:
            surface: la Surface tileset grezza (ottenuta da get_surface)
            col, row: coordinate del tile nel tileset
            tw, th:  dimensioni tile in pixel
            scale:   fattore di scala
        """
        key = (id(surface), col, row, tw, th, scale)
        if key in cls._tiles:
            cls._hits += 1
            return cls._tiles[key]
        cls._misses += 1
        x, y = col * tw, row * th
        if x + tw > surface.get_width() or y + th > surface.get_height():
            return None
        tile = surface.subsurface(pygame.Rect(x, y, tw, th)).copy()
        if scale != 1:
            tile = pygame.transform.scale(tile, (tw * scale, th * scale))
        cls._tiles[key] = tile
        return tile


    @classmethod
    def clear(cls) -> None:
        """Svuota tutte le cache. Utile in test o per un reload completo degli asset."""
        cls._surfaces.clear()
        cls._scaled.clear()
        cls._tiles.clear()
        cls._hits = 0
        cls._misses = 0

    @classmethod
    def stats(cls) -> dict:
        """Restituisce statistiche di utilizzo per debug e profiling."""
        total = cls._hits + cls._misses
        return {
            "surfaces_cached": len(cls._surfaces),
            "scaled_cached":   len(cls._scaled),
            "tiles_cached":    len(cls._tiles),
            "cache_hits":      cls._hits,
            "cache_misses":    cls._misses,
            "hit_rate":        f"{cls._hits / total:.1%}" if total else "n/a",
        }



def _load(rel: str) -> pygame.Surface:
    """Carica un'immagine con colorkey (0,0,0) tramite AssetCache (Flyweight)."""
    return AssetCache.get_surface(str(ASSETS / rel), alpha=False)


def _load_alpha(rel: str) -> pygame.Surface:
    """Carica un'immagine con canale alpha tramite AssetCache (Flyweight)."""
    return AssetCache.get_surface(str(ASSETS / rel), alpha=True)


def _slice(surf: pygame.Surface, n_frames: int,
           scale: int = SCALE) -> list[pygame.Surface]:
    """Taglia uno sheet orizzontale in n_frames e scala ciascun frame."""
    fw = surf.get_width() // n_frames
    fh = surf.get_height()
    frames = []
    for i in range(n_frames):
        frame = surf.subsurface(pygame.Rect(i * fw, 0, fw, fh))
        if scale != 1:
            frame = pygame.transform.scale(
                frame, (fw * scale, fh * scale)
            )
        frames.append(frame)
    return frames


def _flip(frames: list[pygame.Surface]) -> list[pygame.Surface]:
    return [pygame.transform.flip(f, True, False) for f in frames]



def _load_Rivet_frames(anim: str, direction: str,
                     scale: int = SCALE) -> list[pygame.Surface]:
    """
    Carica i frame PNG individuali del nuovo sprite isometrico (Rivet).
    anim      : "walk" | "idle" | "attack"
    direction : "south" | "north" | "east" | "west"

    Ogni frame è caricato tramite AssetCache.get_scaled() (Flyweight):
    lo stesso frame condiviso tra più istanze di Rivet sullo schermo.
    """
    folder = ASSETS / "Character" / "Rivet" / anim / direction
    if not folder.exists():
        fallback = ASSETS / "Character" / "Rivet" / f"{direction}.png"
        if fallback.exists():
            return [AssetCache.get_scaled(str(fallback), scale, alpha=True)]
        s = pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)
        s.fill((180, 0, 180, 200))
        return [s]
    frames = []
    i = 0
    while True:
        p = folder / f"frame_{i:03d}.png"
        if not p.exists():
            break
        frames.append(AssetCache.get_scaled(str(p), scale, alpha=True))
        i += 1
    return frames if frames else [pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)]


def Rivet_idle(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("idle", "east", scale)

def Rivet_idle_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("idle", "west", scale)

def Rivet_run(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("walk", "east", scale)

def Rivet_run_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("walk", "west", scale)

def Rivet_punch(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("attack", "east", scale)

def Rivet_punch_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("attack", "west", scale)

def Rivet_death(scale: int = SCALE) -> list[pygame.Surface]:
    frames = _load_Rivet_frames("walk", "south", scale)
    return frames[::-1]

def Rivet_pickup(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Rivet_frames("idle", "south", scale)



def _load_Echo_frames(anim: str, direction: str,
                     scale: int = SCALE) -> list[pygame.Surface]:
    """
    Carica i frame PNG individuali del nuovo sprite femminile (Echo).
    anim      : "walk" | "idle" | "attack"
    direction : "south" | "north" | "east" | "west"

    Ogni frame è caricato tramite AssetCache.get_scaled() (Flyweight).
    """
    folder = ASSETS / "Character" / "Echo" / anim / direction
    if not folder.exists():
        fallback = ASSETS / "Character" / "Echo" / f"{direction}.png"
        if fallback.exists():
            return [AssetCache.get_scaled(str(fallback), scale, alpha=True)]
        s = pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)
        s.fill((180, 0, 180, 200))
        return [s]
    frames = []
    i = 0
    while True:
        p = folder / f"frame_{i:03d}.png"
        if not p.exists():
            break
        frames.append(AssetCache.get_scaled(str(p), scale, alpha=True))
        i += 1
    return frames if frames else [pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)]


def Echo_idle(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("idle", "east", scale)

def Echo_idle_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("idle", "west", scale)

def Echo_run(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("walk", "east", scale)

def Echo_run_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("walk", "west", scale)

def Echo_shoot(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("attack", "east", scale)

def Echo_shoot_left(scale: int = SCALE) -> list[pygame.Surface]:
    return _load_Echo_frames("attack", "west", scale)

def Echo_death(scale: int = SCALE) -> list[pygame.Surface]:
    frames = _load_Echo_frames("walk", "south", scale)
    return frames[::-1]



def zombie_small_idle(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Small/Zombie_Small_Side_Idle-Sheet6.png"), 6, scale)

def zombie_small_walk(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Small/Zombie_Small_Side_Walk-Sheet6.png"), 6, scale)

def zombie_small_attack(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Small/Zombie_Small_Side_First-Attack-Sheet4.png"), 4, scale)

def zombie_small_death(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Small/Zombie_Small_Side_First-Death-Sheet6.png"), 6, scale)

def zombie_big_idle(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Big/Zombie_Big_Side_Idle-Sheet6.png"), 6, scale)

def zombie_big_walk(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Big/Zombie_Big_Side_Walk-Sheet8.png"), 8, scale)

def zombie_big_attack(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Big/Zombie_Big_Side_First-Attack-Sheet8.png"), 8, scale)

def zombie_big_death(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Big/Zombie_Big_Side_First-Death-Sheet7.png"), 7, scale)

def zombie_axe_idle(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Axe/Zombie_Axe_Side_Idle-Sheet6.png"), 6, scale)

def zombie_axe_walk(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Axe/Zombie_Axe_Side_Walk-Sheet8.png"), 8, scale)

def zombie_axe_attack(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Axe/Zombie_Axe_Side_First-Attack-Sheet7.png"), 7, scale)

def zombie_axe_death(scale: int = SCALE) -> list[pygame.Surface]:
    return _slice(_load("Enemies/Zombie_Axe/Zombie_Axe_Side_First-Death-Sheet6.png"), 6, scale)



def tile_background_dark() -> pygame.Surface:
    """384×272 → 16×16 tile grid (24×17 tiles)."""
    return _load("Tiles/Background_Dark-Green_TileSet.png")

def tile_background_bleak() -> pygame.Surface:
    return _load("Tiles/Background_Bleak-Yellow_TileSet.png")

def tile_background_green() -> pygame.Surface:
    return _load("Tiles/Background_Green_TileSet.png")

def tile_buildings_gray() -> pygame.Surface:
    return _load("Tiles/Buildings/Buildings_gray_TileSet.png")

def tile_buildings_dark() -> pygame.Surface:
    return _load("Tiles/Buildings/Buildings_dark_TileSet.png")

def tile_garbage() -> pygame.Surface:
    return _load("Tiles/Garbage_TileSet.png")

def tile_brick_wall() -> pygame.Surface:
    return _load("Tiles/Brick-Wall_TileSet.png")


def get_tile(sheet: pygame.Surface,
             col: int, row: int,
             tile_w: int = 16, tile_h: int = 16,
             scale: int = SCALE) -> pygame.Surface:
    """Estrae un singolo tile da un tileset tramite AssetCache (Flyweight)."""
    result = AssetCache.get_tile(sheet, col, row, tile_w, tile_h, scale)
    if result is None:
        s = pygame.Surface((tile_w * scale, tile_h * scale), pygame.SRCALPHA)
        return s
    return result



def _as(rel: str, scale: int = SCALE) -> pygame.Surface:
    """Shorthand interno: asset alpha + scala via Flyweight."""
    return AssetCache.get_scaled(str(ASSETS / rel), scale, alpha=True)

def ui_hp_bar(scale: int = SCALE) -> pygame.Surface:           return _as("UI/HP/HP-Bar.png", scale)
def ui_heart_full(scale: int = SCALE) -> pygame.Surface:       return _as("UI/HP/Heart_Full.png", scale)
def ui_heart_half(scale: int = SCALE) -> pygame.Surface:       return _as("UI/HP/Heart_Half.png", scale)
def ui_heart_empty(scale: int = SCALE) -> pygame.Surface:      return _as("UI/HP/Heart_Empty.png", scale)
def ui_inventory_cell(scale: int = SCALE) -> pygame.Surface:   return _as("UI/Inventory/Inventory-Cell.png", scale)
def ui_inventory_chosen(scale: int = SCALE) -> pygame.Surface: return _as("UI/Inventory/Inventory-Chosen.png", scale)
def ui_crafting_cell(scale: int = SCALE) -> pygame.Surface:    return _as("UI/Crafting/Crafting-cell.png", scale)
def ui_crafting_arrow(scale: int = SCALE) -> pygame.Surface:   return _as("UI/Crafting/Crafting_Arrow.png", scale)
def ui_crafting_plus(scale: int = SCALE) -> pygame.Surface:    return _as("UI/Crafting/Crafting_Plus.png", scale)
def ui_menu_play(scale: int = SCALE) -> pygame.Surface:        return _as("UI/Menu/Main Menu/Play_Not-Pressed.png", scale)
def ui_menu_play_pressed(scale: int = SCALE) -> pygame.Surface:return _as("UI/Menu/Main Menu/Play_Pressed.png", scale)
def ui_menu_load(scale: int = SCALE) -> pygame.Surface:        return _as("UI/Menu/Main Menu/Load_Not-Pressed.png", scale)
def ui_menu_load_pressed(scale: int = SCALE) -> pygame.Surface:return _as("UI/Menu/Main Menu/Load_Pressed.png", scale)
def ui_menu_quit(scale: int = SCALE) -> pygame.Surface:        return _as("UI/Menu/Main Menu/Quit_Not-Pressed.png", scale)
def ui_menu_quit_pressed(scale: int = SCALE) -> pygame.Surface:return _as("UI/Menu/Main Menu/Quit_Pressed.png", scale)
def ui_menu_save(scale: int = SCALE) -> pygame.Surface:        return _as("UI/Menu/Main Menu/Save_Not-Pressed.png", scale)
def ui_cursor(scale: int = SCALE) -> pygame.Surface:           return _as("UI/Menu/Cursor.png", scale)

def _icon(name: str, scale: int = SCALE) -> pygame.Surface:
    return _as(f"UI/Inventory/Objects/{name}", scale)

def icon_medkit() -> pygame.Surface:   return _icon("Icon_First-Aid-Kit_Red.png")
def icon_pistol() -> pygame.Surface:   return _icon("Icon_Pistol.png")
def icon_gun() -> pygame.Surface:      return _icon("Icon_Gun.png")
def icon_shotgun() -> pygame.Surface:  return _icon("Icon_Shotgun.png")
def icon_ammo() -> pygame.Surface:     return _icon("Icon_Bullet-box_Red.png")
def icon_food() -> pygame.Surface:     return _icon("Icon_Canned-food.png")
def icon_bandage() -> pygame.Surface:  return _icon("Icon_Bandage.png")

def pickable_medkit(scale: int = SCALE) -> pygame.Surface:     return _as("Objects/Pickable/Pistol.png", scale)
def pickable_pistol(scale: int = SCALE) -> pygame.Surface:     return _as("Objects/Pickable/Pistol.png", scale)
def pickable_canned_food(scale: int = SCALE) -> pygame.Surface:return _as("Objects/Pickable/Canned-food.png", scale)
def obj_barrel_red(scale: int = SCALE) -> pygame.Surface:      return _as("Objects/Barrel_red_1.png", scale)
def obj_trash_bag(scale: int = SCALE) -> pygame.Surface:       return _as("Objects/Trash-bag_1.png", scale)


def npc_sprite(sprite_key: str, direction: str = "south",
               scale: int = SCALE) -> pygame.Surface:
    """
    Carica la rotazione statica di un NPC tramite AssetCache (Flyweight).
    sprite_key : es. "Solidale_1", "Errante_2", "Infetto_Lento" …
    direction  : "south" | "north" | "east" | "west"
    """
    p = ASSETS / "Character" / "NPC" / sprite_key / f"{direction}.png"
    if not p.exists():
        p = ASSETS / "Character" / "NPC" / sprite_key / "south.png"
    if p.exists():
        return AssetCache.get_scaled(str(p), scale, alpha=True)
    surf = pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)
    surf.fill((180, 0, 180, 200))
    return surf
