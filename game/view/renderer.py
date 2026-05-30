"""
renderer.py — Renderer principale della scena di esplorazione.

Disegna la città (tile layer, oggetti, NPC, giocatori) centrata sulla camera,
applica il camera shake e il glitch effect, e compone il frame finale.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import pygame
from game.view import asset_loader as AL
from game.view.asset_loader import AssetCache
from game.view.sprite_sheet import Animation, AnimatedSprite

TILE_SRC = 16
TILE_DST = TILE_SRC * AL.SCALE

BG       = (13,  13,  13)
CYAN     = (0,  229, 255)
GREEN    = (57, 255,  20)
RED      = (255, 45,  45)
YELLOW   = (255,214,   0)
WHITE    = (224,224, 224)
GREY     = ( 85, 85,  85)
DARKGREY = ( 34, 34,  34)
ORANGE   = (255,145,   0)

import sys as _sys

def _get_map_dir() -> Path:
    if hasattr(_sys, '_MEIPASS'):
        return Path(_sys._MEIPASS) / "assets" / "Map"
    return Path(__file__).parent.parent.parent / "assets" / "Map"

_MAP_DIR = _get_map_dir()


def _load(name: str, alpha: bool = True) -> pygame.Surface:
    """Carica un asset dalla cartella Map tramite AssetCache (Flyweight).

    Sostituisce la vecchia coppia (_cache dict + _load()) locale.
    """
    p = _MAP_DIR / name
    if not p.exists():
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        s.fill((180, 0, 180, 180))
        return s
    return AssetCache.get_surface(str(p), alpha=alpha)

def _tile(sheet, col, row, tw=16, th=16, sc=AL.SCALE) -> pygame.Surface:
    """Estrae un tile da sheet tramite AssetCache (Flyweight).

    Sostituisce la vecchia coppia (_cache dict + _tile()) locale.
    Fallback: Surface magenta se fuori dai bordi.
    """
    result = AssetCache.get_tile(sheet, col, row, tw, th, sc)
    if result is None:
        s = pygame.Surface((tw * sc, th * sc), pygame.SRCALPHA)
        s.fill((100, 0, 100, 120))
        return s
    return result



def load_lpc_frames(asset_dir: str, char_folder: str, lpc_anim: str,
                    lpc_dir: str, n_frames: int = 1):
    """Carica i frame LPC direttamente dalla cartella 'standard' estratta dallo ZIP.

    lpc_anim : nome cartella LPC (walk, idle, run, hurt, 1h_halfslash, …)
    lpc_dir  : down | up | left | right
    n_frames : numero di frame da caricare (1-based)
    """
    frames = []
    for i in range(1, n_frames + 1):
        path = os.path.join(asset_dir, char_folder, "standard", lpc_anim, lpc_dir, f"{i}.png")

        if not os.path.exists(path) and lpc_anim == "idle":
            path = os.path.join(asset_dir, char_folder, "standard", "walk", lpc_dir, "1.png")

        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            frames.append(img)
        else:
            err = pygame.Surface((64, 64), pygame.SRCALPHA)
            err.fill((0, 0, 0, 0))
            frames.append(err)

    return frames


def build_lpc_sprite(char_folder_path: str) -> AnimatedSprite:
    """Costruisce uno sprite LPC completo con tutte le 4 direzioni per explore e battle."""
    s = AnimatedSprite()
    asset_dir = str(_get_map_dir().parent)

    STATES = [
        ("walk_dn",  "walk", "down",  9,  10, True),
        ("walk_up",  "walk", "up",    9,  10, True),
        ("walk_l",   "walk", "left",  9,  10, True),
        ("walk_r",   "walk", "right", 9,  10, True),
        ("idle_dn",  "idle", "down",  2,   4, True),
        ("idle_up",  "idle", "up",    2,   4, True),
        ("idle_l",   "idle", "left",  2,   4, True),
        ("idle_r",   "idle", "right", 2,   4, True),
        ("idle",     "idle",         "right", 2,   4, True),
        ("idle_l_b", "idle",         "left",  2,   4, True),
        ("walk",     "walk",         "right", 9,  10, True),
        ("walk_l_b", "walk",         "left",  9,  10, True),
        ("attack",   "1h_halfslash", "right", 6,  12, False),
        ("attack_l", "1h_halfslash", "left",  6,  12, False),
        ("death",    "hurt",         "right", 3,   6, False),
    ]

    for (sname, lanim, ldir, nf, fps, loop) in STATES:
        frames = load_lpc_frames(asset_dir, char_folder_path, lanim, ldir, nf)
        s.add_state(sname, Animation(frames, fps=fps, loop=loop))

    s.set_state("idle_dn")
    return s


def make_Rivet_sprite() -> AnimatedSprite:
    return build_lpc_sprite(os.path.join("Character", "Protagonisti", "Rivet"))

def make_Echo_sprite() -> AnimatedSprite:
    return build_lpc_sprite(os.path.join("Character", "Protagonisti", "Echo"))

def make_enemy_sprite(enemy_name: str, faction: str, sprite_key: str | None = None) -> AnimatedSprite:
    """Crea lo sprite per il nemico usando la cartella LPC esatta.

    Per zombie: sprite_key è il nome cartella in assets/Character/Zombie/ (es. "Orda").
    Per umani:  sprite_key è il nome NPC in assets/Character/<Fazione>/ (es. "Tomas").
    Se sprite_key manca, prova con enemy_name, poi fallback su "Infetto" per zombie.
    """
    s = AnimatedSprite()
    asset_dir = str(_get_map_dir().parent)

    faction_lower = faction.lower() if faction else "zombie"

    if faction_lower in ("zombie", "infetti"):
        candidates = []
        if sprite_key:
            candidates.append(sprite_key)
        if enemy_name and enemy_name != sprite_key:
            candidates.append(enemy_name)
        candidates.append("Infetto")

        char_folder = None
        for candidate in candidates:
            path = os.path.join(asset_dir, "Character", "Zombie", candidate)
            if os.path.isdir(path):
                char_folder = os.path.join("Character", "Zombie", candidate)
                break
        if char_folder is None:
            char_folder = os.path.join("Character", "Zombie", "Infetto")
    else:
        char_name = sprite_key if sprite_key else enemy_name
        char_folder = os.path.join("Character", faction.capitalize(), char_name)

    s.add_state("idle",   Animation(load_lpc_frames(asset_dir, char_folder, "idle", "right", 2), fps=6))
    s.add_state("walk",   Animation(load_lpc_frames(asset_dir, char_folder, "walk", "right", 9), fps=8))
    s.add_state("attack", Animation(load_lpc_frames(asset_dir, char_folder, "1h_halfslash", "right", 6), fps=10, loop=False))
    s.add_state("death",  Animation(load_lpc_frames(asset_dir, char_folder, "hurt", "right", 3), fps=8, loop=False))

    s.set_state("idle")
    return s



def _zone(wx: int, wy: int) -> str:
    if 29 <= wy <= 30:             return "fiume"
    if wx >= 42 and wy <= 28:      return "militare"
    if wx >= 38 and wy >= 30:      return "industriale"
    if wy >= 32:                   return "rurale"
    if wy <= 13:                   return "residential"
    if 14 <= wy <= 16:             return "road"
    if 8 <= wx <= 30 and 14 <= wy <= 28: return "centro"
    return "residential"


LANDMARKS = [
    (14, 20, 0, "GRATTACIELO",    CYAN),
    (20, 22, 1, "[POLIZIA]",      (110,140,255)),
    (24, 24, 2, "OSPEDALE",       RED),
    ( 4,  4, 2, "$$",             YELLOW),
    ( 9,  6, 1, "[Rx]",           (100,255,100)),
    (17,  5, 0, "[Ds]",           ORANGE),
    (25,  3, 2, "$$",             YELLOW),
    (31,  7, 1, "[Ds]",           ORANGE),
    ( 2,  9, 0, "",               WHITE),
    ( 8,  2, 2, "",               WHITE),
    (16, 10, 1, "",               WHITE),
    (22,  2, 0, "",               WHITE),
    (35,  4, 2, "",               WHITE),
    (44,  4, 1, "[AEROPORTO]",    GREY),
    (52, 12, 0, "X-LAB (TopSec)", RED),
    (44, 18, 2, "MILITARE",       (180,200,100)),
    (42, 33, 1, "[ELETTRICA]",    YELLOW),
    (52, 32, 0, "☢ CHIMICA ☢",   (200,80,200)),
    (48, 40, 2, "[Ds]",           ORANGE),
    ( 5, 38, 0, "FATTORIA",       GREEN),
    (14, 38, 1, "FATTORIA",       GREEN),
    (24, 38, 2, "FATTORIA",       GREEN),
    ( 1, 34, 0, "(MUL)",          YELLOW),
]

ZONE_LABELS = [
    (18,  3, "NORD — Residenziale denso",  (180,220,180)),
    (18, 15, "── VIALE PRINCIPALE ──",      (220,220,160)),
    (14, 20, "CENTRO CITTÀ",               CYAN),
    (47,  3, "ZONA MILITARE",              (180,200,100)),
    (48, 11, "[AEROPORTO]",                GREY),
    (50, 17, "X-LAB (TopSec)",             RED),
    (47, 36, "ZONA INDUSTRIALE",           ORANGE),
    (14, 37, "ZONA RURALE",                GREEN),
    (20, 30, "LUNGOFIUME",                 (100,160,255)),
]

ROADS = [
    (0, 15, 63, 15),
    (0, 16, 63, 16),
    (40, 0,  40, 48),
    (41, 0,  41, 48),
    (18, 0, 18, 15),
    (19, 0, 19, 15),
    (18,16, 18, 30),
    (19,16, 19, 30),
    (0, 28, 40, 28),
]


class BuildingSheet:
    _CROPS = [
        (  0, 0, 220, 216),
        (228, 0, 170, 216),
        (408, 0, 180, 216),
    ]
    def __init__(self):
        raw = _load("Buildings.png", alpha=False)
        raw.set_colorkey((0,0,0))
        rw, rh = raw.get_size()
        self._surfs = []
        for (x, y, bw, bh) in self._CROPS:
            x  = min(x,  max(0, rw - 1))
            y  = min(y,  max(0, rh - 1))
            bw = max(1, min(bw, rw - x))
            bh = max(1, min(bh, rh - y))
            try:
                sub = raw.subsurface(pygame.Rect(x, y, bw, bh)).copy()
                sub = sub.convert_alpha()
                sub.set_colorkey((0, 0, 0))
            except Exception:
                sub = pygame.Surface((bw, bh), pygame.SRCALPHA)
                sub.fill((100, 80, 60, 200))
            nw = int(bw * 2.2); nh = int(bh * 2.2)
            self._surfs.append(pygame.transform.scale(sub, (nw, nh)))
        if not self._surfs:
            ph = pygame.Surface((80, 80), pygame.SRCALPHA)
            ph.fill((100, 80, 60, 200))
            self._surfs.append(ph)
    def get(self, i): return self._surfs[i % len(self._surfs)]


class HeartHUD:
    MAX_HEARTS = 5
    def __init__(self):
        self._full  = AL.ui_heart_full(scale=2)
        self._half  = AL.ui_heart_half(scale=2)
        self._empty = AL.ui_heart_empty(scale=2)
        self._w = self._full.get_width()
        self._h = self._full.get_height()

    def draw(self, surf, x, y, hp, max_hp):
        ratio = hp / max(1, max_hp)
        filled = ratio * self.MAX_HEARTS
        for i in range(self.MAX_HEARTS):
            ix = x + i*(self._w+2)
            if filled >= i+1:   surf.blit(self._full,  (ix,y))
            elif filled >= i+.5:surf.blit(self._half,  (ix,y))
            else:               surf.blit(self._empty, (ix,y))


class BattleRenderer:
    PARTY_POSITIONS  = [(420, 450), (370, 510)]
    ENEMY_POSITIONS  = [(600, 220), (650, 380), (480, 320)]

    def __init__(self, Rivet_sprite, Echo_sprite):
        self._Rivet = Rivet_sprite
        self._Echo = Echo_sprite
        self._Rivet.set_state("idle")
        self._Echo.set_state("idle_l")
        self._enemy_sprites = []

    def setup_enemies(self, enemies):
        self._enemy_sprites = []
        for e in enemies:
            faction    = getattr(e, "faction_name", "zombie")
            sprite_key = getattr(e, "sprite_key", None)
            sp = make_enemy_sprite(e.name, faction, sprite_key)
            sp.flip_x = True
            self._enemy_sprites.append(sp)

    def trigger_attack(self, attacker="Rivet"):
        if attacker=="Rivet": self._Rivet.set_state("attack",force=True)
        else:               self._Echo.set_state("attack_l",force=True)

    def trigger_enemy_attack(self, idx=0):
        if idx < len(self._enemy_sprites):
            self._enemy_sprites[idx].set_state("attack",force=True)

    def trigger_death(self, idx):
        if idx < len(self._enemy_sprites):
            self._enemy_sprites[idx].set_state("death",force=True)

    def draw(self, surf, x, y, w, h, dt, Rivet, Echo, enemies, font_sm):
        if len(enemies) > len(self._enemy_sprites):
            for e in enemies[len(self._enemy_sprites):]:
                faction    = getattr(e, "faction_name", "zombie")
                sprite_key = getattr(e, "sprite_key", None)
                sp = make_enemy_sprite(e.name, faction, sprite_key)
                sp.flip_x = True
                self._enemy_sprites.append(sp)

        arena = pygame.Surface((w,h), pygame.SRCALPHA)

        def _draw_shadow(surf, pos, sp):
            """Disegna un'ombra ellittica sotto lo sprite, proporzionale alle sue dimensioni."""
            frame = sp.image
            if frame is None:
                return
            fw = frame.get_width()
            fh = frame.get_height()
            if sp.scale != 1.0:
                fw = max(1, int(fw * sp.scale))
                fh = max(1, int(fh * sp.scale))
            shadow_w = max(fw // 2, 20)
            shadow_h = max(shadow_w // 4, 8)
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, shadow_w, shadow_h))
            sx = pos[0] + fw // 2 - shadow_w // 2
            sy = pos[1] + (fh * 12 // 13) - shadow_h // 2
            surf.blit(shadow_surf, (sx, sy))

        for i,(e,sp) in enumerate(zip(enemies,self._enemy_sprites)):
            if not e.is_alive(): sp.set_state("death")
            sp.update(dt)
            ex,ey = self.ENEMY_POSITIONS[i%len(self.ENEMY_POSITIONS)]
            ex-=x; ey-=y
            _draw_shadow(arena, (ex, ey), sp)
            sp.draw(arena,(ex,ey))

        for i,(char,sp,_) in enumerate([(Rivet,self._Rivet,"h"),(Echo,self._Echo,"h")]):
            if not char.is_alive(): sp.set_state("death")
            sp.update(dt)
            px,py = self.PARTY_POSITIONS[i]; px-=x; py-=y
            _draw_shadow(arena, (px, py), sp)
            sp.draw(arena,(px,py))

        surf.blit(arena,(x,y))