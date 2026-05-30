"""
factory_finale_screen.py — Screen del finale alla Fabbrica Chimica (State GoF).

Sequenza finale narrativa con dialoghi, scelta morale e transizione alla
vittory_screen. Usa la musica "victory" con fade-in.
"""

from __future__ import annotations
import math
import random
import os
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.paths import asset
from game.world.world_data import (
    W, H, BG, CYAN, GREEN, RED, YELLOW, MAGENTA, GREY, WHITE, DARKGREY
)
from game.view.draw_utils import txt, panel, sep
from game.controller.game_manager import GameManager

_SCENE_LINES = [
    ("Narratore", "Abbattuta la porta blindata, Echo entra per prima seguita da Rivet."),
    ("Narratore", "Non appena si posa la polvere sollevata dalla detonazione, Echo si accorge di qualcosa..."),
    ("Narratore", "un qualcosa che li avrebbe aiutati a combattere."),
    ("Echo",      "«Guarda! C'è un silo, vediamo cosa contiene.»"),
    ("Echo",      "«Ma è...»"),
    ("Rivet",     "«Sì, è Soluzione Piranha. C'è pure l'avvertimento di pericolo.»"),
    ("Rivet",     "«Se cospargiamo la città potrebbe aiutarci a contrastare l'infezione.»"),
    ("Echo",      "«Ma così morirebbero anche tanti superstiti. Abbiamo conosciuto brave persone.»"),
    ("Rivet",     "«Però potremmo creare una roccaforte, liberi dalla pressione degli abomini.»"),
    ("Rivet",     "«Potremmo far arrivare persone da posti lontani e iniziare una controffensiva abbastanza forte da prendere terreno.»"),
    ("Echo",      "«Ma potremmo anche prenderne solo una parte e usarla per continuare a combattere.»"),
    ("Echo",      "«Potremmo aiutare i Solidali.»"),
]

_SCENE_IMG_MAP = [2, 2, 2, 1, 1, 1, 3, 3, 3, 3, 3, 3]

_CHOICE_TITLE   = "COSA FATE?"
_CHOICE_A_LABEL = "PURIFICATE LA CITTA'"
_CHOICE_A_DESC = [
    "Collegate il silo all'impianto di ventilazione",
    "e invertite il flusso verso l'esterno.",
    "Attendete che la nube si diradi.",
    "La città è ora purificata."
]
_CHOICE_A_COLOR = GREEN

_CHOICE_B_LABEL = "TORNATE A COMBATTERE"
_CHOICE_B_DESC  = [
    "Non riuscite a condannare vite innocenti,",
    "condannando però la città a una logorante guerra.",
    "Prendete qualche boccetta e tornate a combattere,",
    "sperando di aiutare le brave persone rimaste."
]
_CHOICE_B_COLOR = CYAN


class FactoryFinaleScreen(Screen):
    def __init__(self, fonts):
        self.fonts    = fonts
        self._anim    = 0.0
        self._phase   = "scene"
        self._line    = 0
        self._cursor  = 0
        self._particles: list[dict] = []

        pygame.font.init()
        self.simboli_font = pygame.font.SysFont(
            "segoeuisymbol, applesymbols, dejavusans, arial", 18
        )
        self._load_images()

    def _load_images(self):
        """Carica le immagini di cutscene in memoria in modo dinamico."""
        self._bg_imgs = {}

        base_dir = os.path.dirname(__file__)
        img_dir = asset("images/backgrounds")

        paths = {
            1: os.path.join(img_dir, "scelta_finale1.png"),
            2: os.path.join(img_dir, "scelta_finale2.png"),
            3: os.path.join(img_dir, "scelta_finale3.png"),
        }
        for key, path in paths.items():
            try:
                img = pygame.image.load(path).convert()
                self._bg_imgs[key] = pygame.transform.scale(img, (W, H))
            except Exception as e:
                print(f"[FactoryFinale] Immagine non trovata: {path}")
                s = pygame.Surface((W, H))
                s.fill((20, 25, 20))
                self._bg_imgs[key] = s

    def _init_particles(self):
        self._particles = [
            {
                "x":     random.uniform(0, W),
                "y":     random.uniform(0, H),
                "vy":    random.uniform(-0.4, -1.2),
                "size":  random.randint(1, 3),
                "side":  random.choice([0, 1]),
                "alpha": random.randint(60, 180),
            }
            for _ in range(80)
        ]

    def _update_particles(self):
        for p in self._particles:
            p["y"] += p["vy"]
            if p["y"] < -10:
                p["y"] = H + 5
                p["x"] = random.uniform(0, W)

    def _draw_particles(self, surf: Surface):
        ps = pygame.Surface((W, H), pygame.SRCALPHA)
        for p in self._particles:
            col = (
                (0, 200, 80, p["alpha"]) if p["side"] == 0
                else (0, 200, 220, p["alpha"])
            )
            pygame.draw.circle(ps, col, (int(p["x"]), int(p["y"])), p["size"])
        surf.blit(ps, (0, 0))

    def on_enter(self):
        self._anim   = 0.0
        self._phase  = "scene"
        self._line   = 0
        self._cursor = 0
        self._init_particles()

    def update(self):
        self._anim += 0.04
        if self._phase == "choice":
            self._update_particles()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if self._phase == "scene":
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                self._line += 1
                if self._line >= len(_SCENE_LINES):
                    self._phase = "choice"
        elif self._phase == "choice":
            if k in (
                pygame.K_UP, pygame.K_LEFT, pygame.K_w, pygame.K_a,
                pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s, pygame.K_d
            ):
                self._cursor = 1 - self._cursor
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_choice()

    def _draw_wrapped_text(self, surf, text, x, y, w, color, font):
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < w:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

        line_height = font.get_height() + 4
        for i, line in enumerate(lines):
            txt(surf, line, x, y + i * line_height, color, font)
        return len(lines) * line_height

    def draw(self, surf: Surface):
        if self._phase == "scene":
            self._draw_scene(surf)
        else:
            self._draw_choice(surf)

    def _draw_scene(self, surf: Surface):
        img_key = _SCENE_IMG_MAP[self._line]
        surf.blit(self._bg_imgs[img_key], (0, 0))

        pw, ph = 860, 160
        px = W // 2 - pw // 2
        py = H - ph - 30

        overlay = pygame.Surface((pw, ph), pygame.SRCALPHA)
        overlay.fill((15, 18, 22, 230))
        surf.blit(overlay, (px, py))
        pygame.draw.rect(surf, YELLOW, (px, py, pw, ph), 2, border_radius=8)

        speaker, text = _SCENE_LINES[self._line]

        base_col = WHITE
        if speaker == "Echo":   base_col = CYAN
        elif speaker == "Rivet": base_col = GREEN

        text_y = py + 35
        if speaker != "Narratore":
            txt(surf, speaker.upper(), px + 30, py + 20, base_col, self.fonts["bold"])
            sep(surf, px + 30, py + 45, pw - 60, base_col)
            text_y = py + 60

        self._draw_wrapped_text(surf, text, px + 30, text_y, pw - 60, WHITE, self.fonts["md"])

        blink = abs(math.sin(self._anim * 3.0)) > 0.4
        hint_col = YELLOW if blink else (100, 100, 0)
        prompt = "[INVIO]  Avanti..."
        prompt_w = self.fonts["bold"].size(prompt)[0]

        text_x = px + pw - prompt_w - 20
        text_y = py + ph - 30

        txt(surf, prompt, text_x, text_y, YELLOW, self.fonts["bold"])

    def _draw_choice(self, surf: Surface):
        fn = self.fonts
        cx = W // 2

        surf.blit(self._bg_imgs[3], (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))

        self._draw_particles(surf)

        txt(surf, _CHOICE_TITLE, cx, 80, WHITE, self.fonts["xl"], center=True)
        sep(surf, 100, 130, W - 200, (60, 60, 80))

        self._draw_option_modern(
            surf, cx - 320, H // 2 + 20,
            _CHOICE_A_LABEL, _CHOICE_A_DESC, _CHOICE_A_COLOR,
            (self._cursor == 0)
        )
        self._draw_option_modern(
            surf, cx + 320, H // 2 + 20,
            _CHOICE_B_LABEL, _CHOICE_B_DESC, _CHOICE_B_COLOR,
            (self._cursor == 1)
        )

        txt(
            surf, "← → Naviga   |   INVIO Conferma",
            cx, H - 45, (100, 110, 120), fn["sm"], center=True
        )

    def _draw_option_modern(self, surf, cx, cy, label, desc, color, selected):
        fn = self.fonts
        pw, ph = 500, 320
        px, py = cx - pw // 2, cy - ph // 2

        btn_bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        if selected:
            btn_bg.fill((color[0] // 8, color[1] // 8, color[2] // 8, 240))
            surf.blit(btn_bg, (px, py))
            pygame.draw.rect(surf, color, (px, py, pw, ph), 2, border_radius=8)
            pygame.draw.rect(
                surf, color, (px, py, 6, ph),
                border_top_left_radius=8, border_bottom_left_radius=8
            )
            ico_cursor = self.simboli_font.render("➤", True, color)
            surf.blit(ico_cursor, (px + 20, py + 30))
            text_col = WHITE
        else:
            btn_bg.fill((15, 18, 22, 180))
            surf.blit(btn_bg, (px, py))
            pygame.draw.rect(surf, (40, 50, 60), (px, py, pw, ph), 1, border_radius=8)
            text_col = GREY

        txt(
            surf, label,
            cx + (20 if selected else 0), py + 30,
            color if selected else GREY, fn["bold"], center=True
        )
        sep(surf, px + 20, py + 70, pw - 40, color if selected else (40, 50, 60))

        start_dy = py + 110
        for i, line in enumerate(desc):
            txt(surf, line, cx, start_dy + i * 35, text_col, fn["sm"], center=True)

        if selected:
            pygame.draw.rect(surf, color, (cx - 50, py + ph - 40, 100, 22), border_radius=4)
            txt(surf, "INVIO", cx, py + ph - 29, (0, 0, 0), fn["sm"], center=True)

    def _confirm_choice(self):
        gs = GameManager.get_instance()
        gs.flags["ending_choice"] = "purify" if self._cursor == 0 else "battle"
        gs.flags["finale_choice_made"] = True
        gs.flags["Q03_done"]           = True
        if hasattr(gs, "quest_sys"):
            gs.quest_sys.notify_flag_set("finale_choice_made", True)
            gs.quest_sys.notify_flag_set("Q03_done", True)
        gs.screen = "victory"