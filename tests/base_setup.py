"""base_setup.py — Inizializzazione globale per tutti i test unittest.

Imposta SDL in modalità headless (dummy) prima di importare pygame,
aggiunge il root del progetto al sys.path.
Da importare in ogni modulo di test PRIMA di qualsiasi import di pygame/game.
"""
import os
import sys

# ── Headless SDL: deve stare PRIMA di qualsiasi `import pygame` ──────────────
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ── sys.path: rende importabile il package `game` ───────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame

# Inizializza pygame una volta sola
pygame.init()
pygame.display.set_mode((640, 480))