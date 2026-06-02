from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()   # Fallback Windows 7/8
        except Exception:
            pass

import pygame
from game.view.compat import check_pygame_ce
from game.controller.game_manager import GameManager
gs = GameManager.get_instance()
gs.initialize()

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.mixer.init()
    check_pygame_ce()
    pygame.display.set_caption("Another World")
    surf = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    gs.run(surf)
    pygame.quit()

if __name__ == "__main__":
    main()
    