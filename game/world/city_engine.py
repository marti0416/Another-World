"""
city_engine.py — Motore della città: caricamento mappe, player e rendering.

Carica i file di mappa Tiled (.tmj) per la città, costruisce i ``MapData``
con array di collisione pixel-perfect, gestisce le entità ``Player`` nella
scena di esplorazione e coordina il rendering tramite ``CityRenderer``.
"""

import re
"""
city_engine.py  –  RPG Map 2 city viewer / game engine
========================================================
Layout della città:
    [Q1][Q2]
    [Q3][Q4]

Asset richiesti (stessa cartella di questo file):
    Quartiere_residenziale1_player.png  (e 2,3,4)
    Quartiere_residenziale1.json        (e 2,3,4)
    Echo/
      idle/{south,north,east,west}/frame_000..003.png  (4 frame)
      walk/{south,north,east,west}/frame_000..005.png  (6 frame)
      attack/{south,north,east,west}/frame_000..006.png (7 frame)
Sprite: 48x48 px RGBA
Dipendenze: pip install pygame
"""

import pygame
from game.paths import ASSETS_ROOT as _ASSETS_ROOT
import numpy as np
import json
import base64
import io
import math
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional, List

SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
PLAYER_SPEED = 4
PLAYER_RUN_MULT = 2.0

MAP_TILE_PX = 2000 / 65

MAP_CONFIGS = [
    {"name": "Quartiere_residenziale1", "col": 0, "row": 0, "w": 65, "h": 36},
    {"name": "Quartiere_residenziale2", "col": 1, "row": 0, "w": 65, "h": 36},
    {"name": "Zona militare1",          "col": 2, "row": 0, "w": 65, "h": 36},

    {"name": "Quartiere_residenziale3", "col": 0, "row": 1, "w": 65, "h": 37},
    {"name": "Quartiere_residenziale4", "col": 1, "row": 1, "w": 65, "h": 37},
    {"name": "Zona militare2",          "col": 2, "row": 1, "w": 65, "h": 37},

    {"name": "Zona rurale1",            "col": 0, "row": 2, "w": 65, "h": 37},
    {"name": "Zona rurale2",            "col": 1, "row": 2, "w": 65, "h": 37},
    {"name": "Zona industriale1",       "col": 2, "row": 2, "w": 65, "h": 37},

    {"name": "Zona rurale3",            "col": 0, "row": 3, "w": 65, "h": 36},
    {"name": "Zona rurale4",            "col": 1, "row": 3, "w": 65, "h": 36},
    {"name": "Zona industriale2",       "col": 2, "row": 3, "w": 65, "h": 36},
]

def compute_offsets():
    """Calcola dinamicamente la posizione in pixel di ogni pezzo della mappa"""
    offsets = []
    row_heights = [36, 37, 37, 36]
    col_widths  = [65, 65, 65]

    for cfg in MAP_CONFIGS:
        col, row = cfg["col"], cfg["row"]
        x_tiles = sum(col_widths[:col])
        y_tiles = sum(row_heights[:row])

        ox = round(x_tiles * MAP_TILE_PX)
        oy = round(y_tiles * MAP_TILE_PX)
        offsets.append((ox, oy))
    return offsets


@dataclass
class IconCollider:
    rect:        object
    world_x:     float
    world_y:     float
    scale_inv_x: float = 1.0
    scale_inv_y: float = 1.0
    png_w:       int = 0
    png_h:       int = 0
    alpha:       object = None

@dataclass
@dataclass
class MapData:
    id: int
    w: int
    h: int
    offset_x: int
    offset_y: int
    bg_surface: pygame.Surface
    collision_cells: Set[Tuple[int, int]] = field(default_factory=set)
    icon_colliders: list = field(default_factory=list)
    lights:  list = field(default_factory=list)
    icon_sprites: list = field(default_factory=list)
    labels:  list = field(default_factory=list)
    mobs: list = field(default_factory=list)
    loot_spots: list = field(default_factory=list)
    door_labels: list = field(default_factory=list)
    mine_door_labels: list = field(default_factory=list)
    terminal_labels: list = field(default_factory=list)
    acid_tiles: Set[Tuple[int, int]] = field(default_factory=set)
    enclosed_zones: dict = field(default_factory=dict)
    power_house_pos: Optional[Tuple[int, int]] = None

    @property
    def width_px(self):
        return round(self.w * MAP_TILE_PX)

    @property
    def height_px(self):
        return round(self.h * MAP_TILE_PX)

    def is_collision(self, world_x: float, world_y: float) -> bool:
        tx = int((world_x - self.offset_x) / MAP_TILE_PX)
        ty = int((world_y - self.offset_y) / MAP_TILE_PX)
        if 0 <= tx < self.w and 0 <= ty < self.h:
            if (tx, ty) in self.collision_cells:
                return True
        for ic in self.icon_colliders:
            if not ic.rect.collidepoint(int(world_x), int(world_y)):
                continue

            if ic.alpha is None:
                return True

            px = int((world_x - ic.world_x) * ic.scale_inv_x)
            py = int((world_y - ic.world_y) * ic.scale_inv_y)
            if 0 <= px < ic.png_w and 0 <= py < ic.png_h:
                if ic.alpha[py, px] > 64:
                    return True
        return False


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def b64_to_surface(b64_str: str) -> Optional[pygame.Surface]:
    try:
        raw = base64.b64decode(b64_str + "==")
        buf = io.BytesIO(raw)
        surf = pygame.image.load(buf).convert_alpha()
        return surf
    except Exception as e:
        return None

def load_map(map_id: int, offset_x: int, offset_y: int,
             asset_dir: str = ".") -> MapData:
    cfg = MAP_CONFIGS[map_id - 1]
    w, h = cfg["w"], cfg["h"]
    name = cfg["name"]

    png_path = os.path.join(asset_dir, f"{name}.png")
    raw_surf = pygame.image.load(png_path).convert()
    target_w = round(w * MAP_TILE_PX)
    target_h = round(h * MAP_TILE_PX)
    bg = pygame.transform.scale(raw_surf, (target_w, target_h))

    json_path = os.path.join(asset_dir, f"{name}.json")
    data = load_json(json_path)

    img_cache:        Dict[int, pygame.Surface] = {}
    uid_to_filename:  Dict[int, str]            = {}
    for img_entry in data["imageLib"]["images"]:
        uid = img_entry["uid"]
        try:
            raw_path = base64.b64decode(img_entry["path"] + "==").decode("utf-8", errors="replace")
            fname = raw_path.replace("\\", "/").split("/")[-1]
        except Exception:
            fname = ""
        uid_to_filename[uid] = fname
        surf = b64_to_surface(img_entry["b64"])
        if surf:
            img_cache[uid] = surf

    collision_cells: Set[Tuple[int, int]] = set()
    for c in data["collisions"]:
        idx = int(c.split(":")[0])
        col = idx % w
        row = idx // w
        collision_cells.add((col, row))

    loot_spots = []

    etichette = data.get("labels", [])

    for obj in etichette:
        if "s" in obj and isinstance(obj["s"], str) and obj["s"].strip():
            label = obj["s"].lower().strip()

            if "porta" in label or "terminale" in label or "mina" in label:
                continue

            mappatura_zone = {
                "grattacielo":        ("city_high",          200),
                "supermercato":       ("supermarket",         200),
                "fabbrica":           ("industrial",          200),
                "centrale elettrica": ("centrale_elettrica",  200),
                "centrale":           ("industrial",          200),
                "aeroporto":          ("military",            200),
                "stazione di polizia":("stazione_polizia",    120),
                "polizia":            ("military",            120),
                "militare":           ("military",            120),
                "farmacia":           ("pharmacy",             90),
                "gas":                ("gas_station",          90),
                "benzina":            ("gas_station",          90),
                "casa":               ("city_common",          90),
                "negozio":            ("negozio",              90),
                "fattoria":           ("rural",               150),
                "mulino":             ("mulino",              100),
                "chimica":            ("chem_lab",             90),
                "auto":               ("car",                  40),
                "vigili":             ("vigili_fuoco",        120),
                "scuola":             ("scuola",               90),
                "tenda":              ("tenda",                60),
                "dormitorio":         ("dormitorio",           80),
                "hangar":             ("hangar",              150),
                "campi":              ("campi",               200),
                "scaffale":           ("shelf",                20),
                "scatol":             ("box",                  20),
                "spazzatura":         ("trash",                30),
                "cespugli":           ("bushes",               30),
            }

            zone_type = "city_common"
            radius = 50

            for keyword, (z_type, z_radius) in mappatura_zone.items():
                if keyword in label:
                    zone_type = z_type
                    radius = z_radius
                    break

            wx = (obj["x"] * MAP_TILE_PX) + offset_x + (MAP_TILE_PX // 2)
            wy = (obj["y"] * MAP_TILE_PX) + offset_y + (MAP_TILE_PX // 2)

            rect = pygame.Rect(wx - radius, wy - radius, radius * 2, radius * 2)

            loot_spots.append({
                "rect": rect,
                "zone_type": zone_type,
                "label": obj["s"],
                "pos": (round(obj["x"]), round(obj["y"])),
                "looted": False
            })

    icon_sprites   = []
    icon_colliders = []

    SCALE_INV = 16.0 / MAP_TILE_PX

    WALKABLE_NAMES = (
        "carpet", "rug", "mat",
        "basketball_court",
        "soccer_court",
        "landing_pad",
        "mine"
    )

    WALKABLE_BUILTIN_PARAMS = ("carpet", "rug", "mat")

    acid_tiles: Set[Tuple[int, int]] = set()
    _is_acid_map = (name == "Zona industriale1")

    for pool_entry in data.get("pools", []):
        idx = int(pool_entry.split(":")[0])
        col = idx % w
        row = idx // w
        if _is_acid_map:
            acid_tiles.add((col, row))
        else:
            collision_cells.add((col, row))

    BUILTIN_COLLISIONS = {
        2: (1.5, 2.0),
        5: (1.0, 1.0),
    }
    power_house_pos = None

    for icon in data["icons"]:
        iid = icon["icon"]["id"]

        if iid != 1:
            params = icon["icon"].get("p", [])
            param_str = params[0].lower() if params and isinstance(params[0], str) else ""

            if any(k in param_str for k in WALKABLE_BUILTIN_PARAMS):
                continue

            if iid in BUILTIN_COLLISIONS:
                scale = icon.get("scale", icon.get("s", 1.0))
                if isinstance(scale, list):
                    scale_x, scale_y = float(scale[0]), float(scale[1])
                else:
                    scale_x = scale_y = float(scale)

                base_w, base_h = BUILTIN_COLLISIONS[iid]
                w_tile = base_w * scale_x
                h_tile = base_h * scale_y

                wx0 = offset_x + (icon["x"] - w_tile / 2) * MAP_TILE_PX
                wy0 = offset_y + (icon["y"] - h_tile / 2) * MAP_TILE_PX

                rw  = int(w_tile * MAP_TILE_PX)
                rh  = int(h_tile * MAP_TILE_PX)
                rect = pygame.Rect(int(wx0), int(wy0), rw, rh)

                icon_colliders.append(IconCollider(
                    rect=rect, world_x=wx0, world_y=wy0, alpha=None
                ))
            else:
                pass
            continue

        params = icon["icon"].get("p", [])
        if not params or not isinstance(params[0], int):
            continue
        uid = params[0]
        if uid not in img_cache:
            continue

        surf  = img_cache[uid]
        fname = uid_to_filename.get(uid, "").lower()

        scale = icon.get("scale", icon.get("s", 1.0))
        if isinstance(scale, list):
            scale_x, scale_y = float(scale[0]), float(scale[1])
        else:
            scale_x = scale_y = float(scale)

        w_tile = (surf.get_width() / 32.0) * scale_x
        h_tile = (surf.get_height() / 32.0) * scale_y

        if "power_house" in fname:
            center_x = icon["x"]
            center_y = icon["y"] + scale_y
            power_house_pos = (round(center_x), round(center_y))

        parole_loot = ["crate", "box", "cassa", "scatola", "trash", "garbage", "bin", "spazzatura", "dumpster"]

        if any(k in fname for k in parole_loot):
            lx = round(icon["x"])
            ly = round(icon["y"])
            z_type = "crate" if any(x in fname for x in ["box", "crate", "cassa", "scatola"]) else "trash"

            label_testo = "Cassa" if z_type == "crate" else "Spazzatura"

            loot_spots.append({
                "pos": (lx, ly),
                "zone_type": z_type,
                "label": label_testo,
                "looted": False
            })

        if any(k in fname for k in WALKABLE_NAMES):
            continue


        wx0 = offset_x + (icon["x"] - w_tile / 2) * MAP_TILE_PX
        wy0 = offset_y + (icon["y"] - h_tile / 2) * MAP_TILE_PX

        rw  = int(w_tile * MAP_TILE_PX)
        rh  = int(h_tile * MAP_TILE_PX)
        rect = pygame.Rect(int(wx0), int(wy0), rw, rh)

        inv_x = 32.0 / (scale_x * MAP_TILE_PX)
        inv_y = 32.0 / (scale_y * MAP_TILE_PX)

        try:
            raw_bytes = pygame.image.tostring(surf, "RGBA")
            arr = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
                surf.get_height(), surf.get_width(), 4)
            alpha_arr = arr[:, :, 3].copy()
        except Exception:
            alpha_arr = np.full((surf.get_height(), surf.get_width()), 255, dtype=np.uint8)

        icon_colliders.append(IconCollider(
            rect        = rect,
            alpha       = alpha_arr,
            world_x     = wx0,
            world_y     = wy0,
            scale_inv_x = inv_x,
            scale_inv_y = inv_y,
            png_w       = surf.get_width(),
            png_h       = surf.get_height(),
        ))


    OBJ_TWEAKS = {
    }

    WALKABLE_OBJECT_IDS = {2, 4, 10, 14}

    _all_id2 = [(round(o["x"]), round(o["y"]))
                for o in data.get("objects", [])
                if o.get("t", {}).get("id") == 2]
    _labelled_door_tiles: set = set()
    _has_door_or_mine_label = False
    for lbl in data.get("labels", []):
        _s = lbl.get("s", "").lower()
        if not re.search(r"\bmina\b", _s) and not re.search(r"\bporta\b", _s):
            continue
        _has_door_or_mine_label = True
        _lx, _ly = round(lbl["x"]), round(lbl["y"])
        for tx, ty in _all_id2:
            if abs(tx - _lx) <= 3 and abs(ty - _ly) <= 3:
                _labelled_door_tiles.add((tx, ty))

    door_tiles = set()

    for obj in data.get("objects", []):
        t_id = obj.get("t", {}).get("id", -1)
        colore = obj.get("c")

        if colore == 16777215:
            continue

        ox = obj.get("x", 0)
        oy = obj.get("y", 0)

        if t_id == 10:
            door_tiles.add((round(ox), round(oy)))

        if t_id in WALKABLE_OBJECT_IDS:
            continue
        ox = obj.get("x", 0)
        oy = obj.get("y", 0)
        ow = obj.get("w", 1)
        oh = obj.get("h", 1)


        if t_id in OBJ_TWEAKS:
            off_x, off_y, custom_w, custom_h = OBJ_TWEAKS[t_id]
            ox += off_x
            oy += off_y
            ow = custom_w
            oh = custom_h

        wx0 = offset_x + ox * MAP_TILE_PX
        wy0 = offset_y + oy * MAP_TILE_PX
        rw  = int(ow * MAP_TILE_PX)
        rh  = int(oh * MAP_TILE_PX)

        rect = pygame.Rect(int(wx0), int(wy0), rw, rh)

        icon_colliders.append(IconCollider(
            rect=rect,
            world_x=wx0,
            world_y=wy0,
            alpha=None
        ))
    lights = []
    for lt in data["lights"]:
        wx = offset_x + lt["x"] * MAP_TILE_PX
        wy = offset_y + lt["y"] * MAP_TILE_PX
        radius_tile = lt["radius"]
        intensity = lt.get("int", 0.6)
        core_int = lt["core"]
        core_r = (core_int >> 16) & 0xFF
        core_g = (core_int >> 8) & 0xFF
        core_b = core_int & 0xFF
        lights.append({
            "wx": wx, "wy": wy,
            "radius_tile": radius_tile,
            "intensity": intensity,
            "color": (core_r, core_g, core_b),
        })

    labels = []
    for lbl in data.get("labels", []):
        text = lbl.get("s", "")
        text_lower = text.lower()
        wx = offset_x + lbl["x"] * MAP_TILE_PX
        wy = offset_y + lbl["y"] * MAP_TILE_PX
        labels.append((text, wx, wy))

    door_labels: list = []
    for lbl in data.get("labels", []):
        text = lbl.get("s", "")
        if not re.search(r"\bporta\b", text.lower()):
            continue

        orig_tx = round(lbl["x"])
        orig_ty = round(lbl["y"])

        tx, ty = orig_tx, orig_ty
        best_gap = None
        min_dist = 999

        for dy in range(-2, 3):
            for dx in range(-2, 3):
                cx = orig_tx + dx
                cy = orig_ty + dy

                if (cx, cy) not in collision_cells:
                    horiz = (cx - 1, cy) in collision_cells and (cx + 1, cy) in collision_cells
                    vert  = (cx, cy - 1) in collision_cells and (cx, cy + 1) in collision_cells

                    if horiz or vert:
                        dist = dx*dx + dy*dy
                        if dist < min_dist:
                            min_dist = dist
                            best_gap = (cx, cy)

        if best_gap:
            tx, ty = best_gap

        wx = offset_x + tx * MAP_TILE_PX
        wy = offset_y + ty * MAP_TILE_PX

        collision_cells.add((tx, ty))

        door_collision_cells = [(tx, ty)]

        import re as _re
        m_thresh = _re.search(r"\[(\d+)\]", text)
        threshold = int(m_thresh.group(1)) if m_thresh else 14

        door_labels.append({
            "pos":              (tx, ty),
            "label":            text,
            "breached":         False,
            "collision_cells":  door_collision_cells,
            "strength_threshold": threshold,
            "world_x":          wx,
            "world_y":          wy,
        })

    mine_door_labels: list = []

    _mine_tiles: list = []
    for tx, ty in _labelled_door_tiles:
        near_mina = any(
            re.search(r"\bmina\b", lbl.get("s", "").lower())
            and abs(tx - round(lbl["x"])) <= 5
            and abs(ty - round(lbl["y"])) <= 5
            for lbl in data.get("labels", [])
        )
        if near_mina or not _has_door_or_mine_label:
            _mine_tiles.append((tx, ty))

    def _group_adjacent(tiles):
        """Raggruppa tile in cluster adiacenti (4-connected)."""
        remaining = set(tiles)
        groups = []
        while remaining:
            seed = next(iter(remaining))
            cluster = set()
            frontier = {seed}
            while frontier:
                cur = frontier.pop()
                cluster.add(cur)
                remaining.discard(cur)
                x, y = cur
                for nb in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if nb in remaining:
                        frontier.add(nb)
            groups.append(sorted(cluster))
        return groups

    for group in _group_adjacent(_mine_tiles):
        for cell in group:
            collision_cells.add(cell)
        first = group[0]
        wx = offset_x + first[0] * MAP_TILE_PX
        wy = offset_y + first[1] * MAP_TILE_PX
        mine_door_labels.append({
            "pos":             first,
            "label":           "mina",
            "blown":           False,
            "collision_cells": group,
            "world_x":         wx,
            "world_y":         wy,
        })

    terminal_labels: list = []
    for lbl in data.get("labels", []):
        text = lbl.get("s", "")
        if "terminale" not in text.lower():
            continue
        tx = round(lbl["x"])
        ty = round(lbl["y"])
        wx = offset_x + tx * MAP_TILE_PX
        wy = offset_y + ty * MAP_TILE_PX
        terminal_labels.append({
            "pos":   (tx, ty),
            "label": text,
            "world_x": wx,
            "world_y": wy,
        })

    for key in ["objs", "objects", "entities"]:
        if key in data:
            for i, obj in enumerate(data[key][:3]):
                break

    mobs_list = []
    if "mobs" in data:
        for mob_data in data["mobs"]:
            grid_x = mob_data.get("x", 0)
            grid_y = mob_data.get("y", 0)
            nome_mob = mob_data.get("n", "Sconosciuto")

            fazione_o_desc = mob_data.get("d")
            if fazione_o_desc is None:
                fazione = "zombie"
            else:
                fazione = fazione_o_desc.lower()

            soglie_reputazione = {
                "solidali": -20,
                "erranti": -30,
                "dannati": 40,
                "razziatori": 30,
                "zombie": 999
            }
            soglia_rep = soglie_reputazione.get(fazione, 0)

            statistiche_hp = {
                "Infetto": 100,
                "Corazzato": 200,
                "Orda": 150,
                "Gigante di Carne": 300,
            }

            if nome_mob in statistiche_hp:
                hp_base = statistiche_hp[nome_mob]
            else:
                hp_base = 100

            npc_dict = {
                "name": nome_mob,
                "faction": fazione,
                "hp": hp_base,
                "max_hp": hp_base,
                "rep_threshold": soglia_rep,
                "pos": (grid_x, grid_y),
            }
            mobs_list.append(npc_dict)

    enclosed_zones = {}

    for text, wx, wy in labels:
        label_str = text.lower()

        if "grattacielo" in label_str:
            start_tx = int((wx - offset_x) / MAP_TILE_PX)
            start_ty = int((wy - offset_y) / MAP_TILE_PX)

            room_cells = set()
            queue = [(start_tx, start_ty)]
            visited = {(start_tx, start_ty)}

            while queue and len(room_cells) < 1500:
                cx, cy = queue.pop(0)

                if (cx, cy) in collision_cells or (cx, cy) in door_tiles:
                    continue

                room_cells.add((cx, cy))

                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))

            global_cells = set()
            offset_tx = round(offset_x / MAP_TILE_PX)
            offset_ty = round(offset_y / MAP_TILE_PX)
            for cx, cy in room_cells:
                global_cells.add((cx + offset_tx, cy + offset_ty))

            enclosed_zones["Grattacielo"] = global_cells

    return MapData(
        id=map_id,
        w=w,
        h=h,
        offset_x=offset_x,
        offset_y=offset_y,
        bg_surface=bg,
        collision_cells=collision_cells,
        icon_colliders=icon_colliders,
        lights=lights,
        labels=labels,
        mobs=mobs_list,
        loot_spots=loot_spots,
        door_labels=door_labels,
        mine_door_labels=mine_door_labels,
        terminal_labels=terminal_labels,
        acid_tiles=acid_tiles,
        enclosed_zones=enclosed_zones,
        power_house_pos=power_house_pos
    )


ANIM_FRAMES = {"idle": 4, "walk": 6, "attack": 7}
ANIM_FPS    = {"idle": 6, "walk": 10, "attack": 14}
_DIR_MAP = {
    "south": "south", "north": "north",
    "east":  "east",  "west":  "west",
}

def _load_anim_frames(base: str, state: str, direction: str) -> List[pygame.Surface]:
    """Carica i frame png di un'animazione e li scala a 2×MAP_TILE_PX per visibilità."""
    target = int(MAP_TILE_PX * 2)
    frames = []
    n = ANIM_FRAMES[state]
    for i in range(n):
        path = os.path.join(base, "Echo", state, direction, f"frame_{i:03d}.png")
        if not os.path.exists(path):
            break
        surf = pygame.image.load(path).convert_alpha()
        surf = pygame.transform.scale(surf, (target, target))
        frames.append(surf)
    return frames


class Player:
    COLL_R = int(MAP_TILE_PX * 0.45)

    @property
    def SPRITE_SIZE(self):
        return int(MAP_TILE_PX * 2)

    def __init__(self, world_x: float, world_y: float, asset_dir: str = "."):
        self.x = float(world_x)
        self.y = float(world_y)
        self.vel_x = 0.0
        self.vel_y = 0.0

        self.direction = "south"
        self.state     = "idle"
        self.anim_time = 0.0
        self.frame_idx = 0
        self.attacking    = False
        self.attack_done  = False

        self.frames: Dict[str, Dict[str, List[pygame.Surface]]] = {}
        for state in ("idle", "walk", "attack"):
            self.frames[state] = {}
            for direction in ("south", "north", "east", "west"):
                f = _load_anim_frames(asset_dir, state, direction)
                if f:
                    self.frames[state][direction] = f
        sz = self.SPRITE_SIZE
        self._fallback = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(self._fallback, (220, 80, 80), (sz//2, sz//2), self.COLL_R)

    def _current_frames(self) -> List[pygame.Surface]:
        return (self.frames
                .get(self.state, {})
                .get(self.direction,
                     self.frames.get("idle", {}).get(self.direction, [])))

    def handle_input(self, keys, speed: float):
        if self.attacking:
            self.vel_x = self.vel_y = 0.0
            return

        self.vel_x = 0.0
        self.vel_y = 0.0
        moved = False

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vel_x -= speed; self.direction = "west";  moved = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x += speed; self.direction = "east";  moved = True
        if keys[pygame.K_UP]    or keys[pygame.K_w]:
            self.vel_y -= speed; self.direction = "north"; moved = True
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:
            self.vel_y += speed; self.direction = "south"; moved = True

        if self.vel_x != 0 and self.vel_y != 0:
            f = 1.0 / math.sqrt(2)
            self.vel_x *= f
            self.vel_y *= f

        self.state = "walk" if moved else "idle"

    def trigger_attack(self):
        """Chiama quando il giocatore preme il tasto attacco."""
        if not self.attacking:
            self.attacking = True
            self.attack_done = False
            self.state = "attack"
            self.frame_idx = 0
            self.anim_time = 0.0

    def update(self, dt_sec: float):
        """Avanza l'animazione di dt_sec secondi."""
        fps = ANIM_FPS.get(self.state, 8)
        self.anim_time += dt_sec
        frames = self._current_frames()
        if not frames:
            return
        n = len(frames)
        self.frame_idx = int(self.anim_time * fps) % n

        if self.attacking:
            total_dur = n / ANIM_FPS["attack"]
            if self.anim_time >= total_dur:
                self.attacking = False
                self.attack_done = True
                self.state = "idle"
                self.anim_time = 0.0
                self.frame_idx = 0

    def move(self, dx: float, dy: float, maps: List[MapData],
             city_w: int, city_h: int):
        if self.attacking:
            return

        nx = self.x + dx
        ny = self.y + dy
        r = self.COLL_R

        nx = max(r, min(city_w - r, nx))
        ny = max(r, min(city_h - r, ny))

        def blocked(wx, wy):
            for m in maps:
                if (m.offset_x <= wx < m.offset_x + m.width_px and
                        m.offset_y <= wy < m.offset_y + m.height_px):
                    if m.is_collision(wx, wy):
                        return True
            return False

        if not (blocked(nx - r, ny) or blocked(nx + r, ny) or
                blocked(nx, ny - r) or blocked(nx, ny + r)):
            self.x, self.y = nx, ny
        elif not (blocked(nx - r, self.y) or blocked(nx + r, self.y) or
                  blocked(nx, self.y - r) or blocked(nx, self.y + r)):
            self.x = nx
        elif not (blocked(self.x - r, ny) or blocked(self.x + r, ny) or
                  blocked(self.x, ny - r) or blocked(self.x, ny + r)):
            self.y = ny

    def draw(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        frames = self._current_frames()
        surf = frames[self.frame_idx % len(frames)] if frames else self._fallback
        sz = self.SPRITE_SIZE
        sx = int(self.x - cam_x - sz // 2)
        sy = int(self.y - cam_y - sz // 2)
        screen.blit(surf, (sx, sy))


class Camera:
    def __init__(self, screen_w: int, screen_h: int, city_w: int, city_h: int):
        self.sw = screen_w
        self.sh = screen_h
        self.city_w = city_w
        self.city_h = city_h
        self.x = 0.0
        self.y = 0.0

    def follow(self, px: float, py: float):
        self.x = px - self.sw / 2
        self.y = py - self.sh / 2
        self.x = max(0, min(self.city_w - self.sw, self.x))
        self.y = max(0, min(self.city_h - self.sh, self.y))

    @property
    def int_x(self): return int(self.x)
    @property
    def int_y(self): return int(self.y)


_LIGHT_CACHE = {}

def build_light_overlay(maps: List[MapData], city_w: int, city_h: int,
                        cam_x: int, cam_y: int,
                        screen_w: int, screen_h: int) -> pygame.Surface:
    """Crea un overlay scuro con cerchi luminosi usando una cache ad alte performance."""
    overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 110))

    for m in maps:
        for lt in m.lights:
            sx = int(lt["wx"] - cam_x)
            sy = int(lt["wy"] - cam_y)
            r = int(lt["radius_tile"] * MAP_TILE_PX)

            if sx + r < 0 or sx - r > screen_w: continue
            if sy + r < 0 or sy - r > screen_h: continue

            intensity = lt["intensity"]
            cr, cg, cb = lt["color"]

            cache_key = (r, intensity, cr, cg, cb)

            if cache_key not in _LIGHT_CACHE:
                light_master = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                for step, (radius_f, alpha_f) in enumerate([(1.0, 0.0), (0.6, 0.3), (0.3, 0.5)]):
                    ring_r = int(r * radius_f)
                    alpha = int(255 * alpha_f * intensity)
                    temp_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, (cr, cg, cb, alpha), (ring_r, ring_r), ring_r)
                    light_master.blit(temp_surf, (r - ring_r, r - ring_r))
                _LIGHT_CACHE[cache_key] = light_master

            overlay.blit(_LIGHT_CACHE[cache_key], (sx - r, sy - r), special_flags=pygame.BLEND_RGBA_SUB)

    return overlay


class MiniMap:
    MINI_W = 200
    MINI_H = 150
    MARGIN = 10

    def __init__(self, maps: List[MapData], city_w: int, city_h: int):
        self.maps = maps
        self.city_w = city_w
        self.city_h = city_h
        self.scale_x = self.MINI_W / city_w
        self.scale_y = self.MINI_H / city_h
        self.bg = pygame.Surface((self.MINI_W, self.MINI_H))
        self.bg.fill((30, 40, 30))
        for m in maps:
            rx = int(m.offset_x * self.scale_x)
            ry = int(m.offset_y * self.scale_y)
            rw = int(m.width_px * self.scale_x)
            rh = int(m.height_px * self.scale_y)
            pygame.draw.rect(self.bg, (60, 80, 60), (rx, ry, rw, rh))
            pygame.draw.rect(self.bg, (100, 120, 100), (rx, ry, rw, rh), 1)
            for (tx, ty) in m.collision_cells:
                cx = int((m.offset_x + tx * MAP_TILE_PX) * self.scale_x)
                cy = int((m.offset_y + ty * MAP_TILE_PX) * self.scale_y)
                if 0 <= cx < self.MINI_W and 0 <= cy < self.MINI_H:
                    self.bg.set_at((cx, cy), (20, 20, 20))

    def draw(self, screen: pygame.Surface, player: Player,
             cam_x: int, cam_y: int):
        mm_x = SCREEN_W - self.MINI_W - self.MARGIN
        mm_y = SCREEN_H - self.MINI_H - self.MARGIN

        bg_copy = self.bg.copy()

        vx = int(cam_x * self.scale_x)
        vy = int(cam_y * self.scale_y)
        vw = int(SCREEN_W * self.scale_x)
        vh = int(SCREEN_H * self.scale_y)
        pygame.draw.rect(bg_copy, (200, 200, 100), (vx, vy, vw, vh), 1)

        px = int(player.x * self.scale_x)
        py = int(player.y * self.scale_y)
        pygame.draw.circle(bg_copy, (255, 80, 80), (px, py), 3)

        pygame.draw.rect(screen, (180, 180, 180),
                         (mm_x - 2, mm_y - 2, self.MINI_W + 4, self.MINI_H + 4), 2)
        screen.blit(bg_copy, (mm_x, mm_y))


def draw_hud(screen: pygame.Surface, font: pygame.font.Font,
             player: Player, maps: List[MapData], fps: float):
    fps_surf = font.render(f"FPS: {fps:.0f}", True, (255, 255, 100))
    screen.blit(fps_surf, (10, 10))

    pos_surf = font.render(f"X:{player.x:.0f}  Y:{player.y:.0f}", True, (200, 255, 200))
    screen.blit(pos_surf, (10, 30))

    q_name = ""
    for m in maps:
        if (m.offset_x <= player.x < m.offset_x + m.width_px and
                m.offset_y <= player.y < m.offset_y + m.height_px):
            q_name = f"Quartiere residenziale {m.id}"
            break
    if q_name:
        q_surf = font.render(q_name, True, (180, 220, 255))
        screen.blit(q_surf, (10, 50))

    ctrl = font.render("WASD/↑↓←→ = Muovi  |  SHIFT = Corri  |  SPAZIO/J = Attacca  |  ESC = Esci", True, (160, 160, 160))
    screen.blit(ctrl, (10, SCREEN_H - 24))


def main():
    asset_dir = str(_ASSETS_ROOT)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Città RPG – City Engine")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 14)
    font_label = pygame.font.SysFont("sans", 16, bold=True)

    offsets = compute_offsets()

    maps: List[MapData] = []
    for i, (ox, oy) in enumerate(offsets, start=1):
        m = load_map(i, ox, oy, asset_dir)
        maps.append(m)

    city_w = maps[1].offset_x + maps[1].width_px
    city_h = maps[2].offset_y + maps[2].height_px

    start_x = maps[0].offset_x + maps[0].width_px // 2
    start_y = maps[0].offset_y + maps[0].height_px // 2
    player = Player(float(start_x), float(start_y), asset_dir)

    camera = Camera(SCREEN_W, SCREEN_H, city_w, city_h)
    camera.follow(player.x, player.y)

    minimap = MiniMap(maps, city_w, city_h)

    show_lights = True
    show_labels = True
    show_minimap = True
    show_collisions = False

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        fps = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_l:
                    show_lights = not show_lights
                if event.key == pygame.K_t:
                    show_labels = not show_labels
                if event.key == pygame.K_m:
                    show_minimap = not show_minimap
                if event.key == pygame.K_c:
                    show_collisions = not show_collisions
                if event.key == pygame.K_SPACE or event.key == pygame.K_j:
                    player.trigger_attack()

        keys = pygame.key.get_pressed()
        run = PLAYER_RUN_MULT if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else 1.0
        speed = PLAYER_SPEED * run
        player.handle_input(keys, speed)
        player.move(player.vel_x, player.vel_y, maps, city_w, city_h)
        dt_sec = dt_ms / 1000.0
        player.update(dt_sec)
        camera.follow(player.x, player.y)

        cam_x = camera.int_x
        cam_y = camera.int_y

        screen.fill((20, 30, 20))

        for m in maps:
            draw_x = m.offset_x - cam_x
            draw_y = m.offset_y - cam_y
            if (draw_x + m.width_px < 0 or draw_x > SCREEN_W or
                    draw_y + m.height_px < 0 or draw_y > SCREEN_H):
                continue
            screen.blit(m.bg_surface, (draw_x, draw_y))


        if show_collisions:
            for m in maps:
                for (tx, ty) in m.collision_cells:
                    rx = int(m.offset_x + tx * MAP_TILE_PX - cam_x)
                    ry = int(m.offset_y + ty * MAP_TILE_PX - cam_y)
                    rw = int(MAP_TILE_PX)
                    rh = int(MAP_TILE_PX)
                    if rx + rw < 0 or rx > SCREEN_W: continue
                    if ry + rh < 0 or ry > SCREEN_H: continue
                    dbg = pygame.Surface((rw, rh), pygame.SRCALPHA)
                    dbg.fill((255, 0, 0, 80))
                    screen.blit(dbg, (rx, ry))
                    pygame.draw.rect(screen, (255, 60, 60), (rx, ry, rw, rh), 1)
                for ic in m.icon_colliders:
                    sx = ic.rect.x - cam_x
                    sy = ic.rect.y - cam_y
                    rw_i, rh_i = ic.rect.w, ic.rect.h
                    if sx + rw_i < 0 or sx > SCREEN_W: continue
                    if sy + rh_i < 0 or sy > SCREEN_H: continue

                    if ic.alpha is None:
                        dbg = pygame.Surface((rw_i, rh_i), pygame.SRCALPHA)
                        dbg.fill((255, 140, 0, 160))
                        screen.blit(dbg, (sx, sy))
                        pygame.draw.rect(screen, (255, 200, 0), (sx, sy, rw_i, rh_i), 1)
                    else:
                        alpha_raw = ic.alpha
                        small = pygame.Surface((ic.png_w, ic.png_h), pygame.SRCALPHA)
                        pxa = pygame.surfarray.pixels_alpha(small)
                        pxa[:, :] = alpha_raw.T
                        del pxa
                        rgb_surf = pygame.Surface((ic.png_w, ic.png_h))
                        rgb_surf.fill((255, 140, 0))
                        small.blit(rgb_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                        dbg = pygame.transform.scale(small, (rw_i, rh_i))
                        dbg.set_alpha(160)
                        screen.blit(dbg, (sx, sy))
                        pygame.draw.rect(screen, (255, 200, 0), (sx, sy, rw_i, rh_i), 1)
        player.draw(screen, cam_x, cam_y)

        if show_lights and not show_collisions:
            overlay = build_light_overlay(maps, city_w, city_h,
                                          cam_x, cam_y, SCREEN_W, SCREEN_H)
            screen.blit(overlay, (0, 0))

        if show_labels:
            for m in maps:
                for (text, wx, wy) in m.labels:
                    sx = int(wx - cam_x)
                    sy = int(wy - cam_y)
                    if -200 < sx < SCREEN_W + 200 and -50 < sy < SCREEN_H + 50:
                        lbl_surf = font_label.render(text, True, (255, 255, 180))
                        bg_r = lbl_surf.get_rect(center=(sx, sy))
                        bg_surf = pygame.Surface((bg_r.w + 8, bg_r.h + 4), pygame.SRCALPHA)
                        bg_surf.fill((0, 0, 0, 140))
                        screen.blit(bg_surf, (bg_r.x - 4, bg_r.y - 2))
                        screen.blit(lbl_surf, bg_r)

        draw_hud(screen, font, player, maps, fps)

        if show_minimap:
            minimap.draw(screen, player, cam_x, cam_y)

        hints = [
            "L = Luci on/off",
            "T = Label on/off",
            "M = Minimappa on/off",
            "C = Collisioni debug",
            "SPAZIO/J = Attacca",
        ]
        for hi, hint in enumerate(hints):
            hs = font.render(hint, True, (140, 140, 140))
            screen.blit(hs, (SCREEN_W - 160, 10 + hi * 18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()