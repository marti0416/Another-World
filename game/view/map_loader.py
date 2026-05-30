"""
map_loader.py — Caricamento e parsing delle mappe tiled (Tiled Map Editor).

Carica file .tmj/.json prodotti da Tiled, costruisce i ``MapData`` con array
di collisione e offset pixel, pronti per essere usati da ``MovementSystem``
e dal renderer della città.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
import pygame
from game.view import asset_loader as AL
from game.view.asset_loader import AssetCache

import sys as _sys

def _get_map_root() -> Path:
    if hasattr(_sys, '_MEIPASS'):
        return Path(_sys._MEIPASS) / "assets" / "Map"
    return Path(__file__).parent.parent.parent / "assets" / "Map"

_ASSETS_MAP = _get_map_root()



class Tileset:
    def __init__(self, data: dict):
        self.firstgid  = data["firstgid"]
        self.columns   = data["columns"]
        self.tilewidth = data.get("tilewidth", 16)
        self.tileheight= data.get("tileheight", 16)
        img_path = _ASSETS_MAP / data["image"]
        self.surface = AssetCache.get_surface(str(img_path), alpha=True)

    def get_tile(self, gid: int, scale: int = AL.SCALE) -> Optional[pygame.Surface]:
        local = gid - self.firstgid
        if local < 0:
            return None
        row = local // self.columns
        col = local  % self.columns
        return AssetCache.get_tile(
            self.surface, col, row,
            self.tilewidth, self.tileheight, scale
        )



class TiledMap:
    """Carica e renderizza una mappa Tiled JSON."""

    def __init__(self, json_path: str, scale: int = AL.SCALE):
        self.scale = scale
        with open(json_path) as f:
            self._data = json.load(f)

        self.map_width  = self._data["width"]
        self.map_height = self._data["height"]
        self.tile_w     = self._data["tilewidth"]
        self.tile_h     = self._data["tileheight"]

        self.tilesets: list[Tileset] = []
        for ts_data in self._data.get("tilesets", []):
            if "image" in ts_data:
                try:
                    self.tilesets.append(Tileset(ts_data))
                except Exception as e:
                    print(f"[MapLoader] Skip tileset {ts_data.get('name')}: {e}")

        self.tile_layers:   list[dict] = []
        self.object_layers: list[dict] = []
        for layer in self._data.get("layers", []):
            if layer["type"] == "tilelayer":
                self.tile_layers.append(layer)
            elif layer["type"] == "objectgroup":
                self.object_layers.append(layer)

        self.npcs:      list[dict] = []
        self.terminals: list[tuple] = []
        self.loot_spots:list[tuple] = []
        self.spawn:     tuple = (18, 20)
        self._parse_objects()

    def _parse_objects(self):
        for ol in self.object_layers:
            for obj in ol.get("objects", []):
                tx = obj["x"] // self.tile_w
                ty = obj["y"] // self.tile_h
                otype = obj.get("type", "")
                name  = obj.get("name", "")
                props = {p["name"]: p["value"]
                         for p in obj.get("properties", [])}
                if otype == "npc":
                    self.npcs.append({
                        "name": name,
                        "pos": (tx, ty),
                        "faction": props.get("faction", "erranti"),
                    })
                elif otype == "terminal":
                    self.terminals.append((tx, ty))
                elif otype == "loot":
                    self.loot_spots.append((tx, ty))
                elif otype == "spawn":
                    self.spawn = (tx, ty)

    def _resolve_tile(self, gid: int) -> Optional[pygame.Surface]:
        if gid == 0:
            return None
        ts = None
        for t in sorted(self.tilesets, key=lambda t: t.firstgid, reverse=True):
            if gid >= t.firstgid:
                ts = t
                break
        if ts is None:
            return None
        return ts.get_tile(gid, self.scale)

    def get_tile_at(self, layer_name: str, tx: int, ty: int) -> int:
        """Restituisce il GID raw del tile alla posizione (tx,ty)."""
        for layer in self.tile_layers:
            if layer["name"] == layer_name:
                idx = ty * self.map_width + tx
                data = layer.get("data", [])
                if 0 <= idx < len(data):
                    return data[idx]
        return 0

    def draw(self, surf: pygame.Surface,
             cam_x: int, cam_y: int,
             view_cols: int, view_rows: int,
             offset_x: int = 8, offset_y: int = 8,
             layer_names: Optional[list[str]] = None):
        """
        Disegna i layer tile nella viewport.
        cam_x, cam_y  = origine camera in tile
        view_cols/rows = tile visibili
        layer_names   = lista layer da disegnare (None = tutti)
        """
        ts = self.tile_w * self.scale

        layers_to_draw = self.tile_layers
        if layer_names:
            layers_to_draw = [l for l in self.tile_layers
                              if l["name"] in layer_names]

        for layer in layers_to_draw:
            data = layer.get("data", [])
            opacity = layer.get("opacity", 1.0)
            for row in range(view_rows):
                for col in range(view_cols):
                    wx = col + cam_x
                    wy = row + cam_y
                    if not (0 <= wx < self.map_width and
                            0 <= wy < self.map_height):
                        continue
                    gid = data[wy * self.map_width + wx]
                    if gid == 0:
                        continue
                    tile_surf = self._resolve_tile(gid)
                    if tile_surf is None:
                        continue
                    if opacity < 1.0:
                        tile_surf = tile_surf.copy()
                        tile_surf.set_alpha(int(opacity * 255))
                    surf.blit(tile_surf,
                              (offset_x + col * ts,
                               offset_y + row * ts))
