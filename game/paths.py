from __future__ import annotations
import sys
from pathlib import Path


def _find_assets_root() -> Path:
    """
    Restituisce la cartella root degli asset in qualsiasi contesto:
    - Sviluppo normale  → <repo>/assets/
    - Eseguibile PyInstaller (onefile) → sys._MEIPASS/assets/
    """
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).parent.parent / "assets"


ASSETS_ROOT: Path = _find_assets_root()


def asset(relative_path: str) -> str:
    """
    Restituisce il path assoluto (stringa) di un asset relativo alla cartella assets/.

    Uso:
        from game.paths import asset
        pygame.mixer.music.load(asset("audio/intro_music.wav"))
        pygame.image.load(asset("images/backgrounds/menu_apocalypse.jpg"))
    """
    return str(ASSETS_ROOT / relative_path)


def asset_path(relative_path: str) -> Path:
    """Stessa cosa di asset() ma restituisce un oggetto Path invece di str."""
    return ASSETS_ROOT / relative_path
