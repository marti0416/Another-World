"""
help_screen.py — Screen della guida in-game (State GoF).

Visualizza la lista dei controlli, le meccaniche di gioco e i suggerimenti
organizzati in sezioni navigabili.
"""

from __future__ import annotations
import pygame
from pygame import Surface

from game.screens.base_screen import Screen
from game.world.world_data import (
    W, H, BG, BG2, CYAN, GREEN, GREY, WHITE, YELLOW, DARKGREY, MAGENTA, RED, ORANGE
)
from game.view.draw_utils import txt, panel, sep
from game.controller.game_manager import GameManager



_PW           = 660
_MARGIN_X     = 30
_TITLE_H      = 60
_FOOTER_H     = 30
_SCROLL_SPEED = 28
_LINE_H       = 22
_SECTION_H    = 32
_SECTION_GAP  = 14



_SCANLINE_COLOR   = (0, 0, 0, 40)
_GLOW_CYAN        = (0, 220, 255, 60)
_PANEL_BORDER_LIT = (0, 255, 220)
_LINE_ACCENT      = (0, 180, 200, 80)



_HELP_SECTIONS: list[dict] = [
    {
        "title": "CONTROLLI — RIVET (Giocatore 1)",
        "color": GREEN,
        "lines": [
            "W / A / S / D        Movimento (su / sx / giù / dx)",
            "E                    Interagisci (NPC, loot, porte, quest)",
            "C                    Schermata Crafting",
            "R                    Ruota Abilità (Skill Wheel)",
            "1 - 5                Seleziona slot inventario",
            "Z / X                Scorri inventario su / giù",
            "G                    Butta oggetto a terra",
            "P                    Pausa",
            "M                    Mappa del mondo",
            "Q                    Quest log",
            "ESC                  Torna al menu principale",
        ],
    },
    {
        "title": "CONTROLLI — ECHO (Giocatore 2)",
        "color": CYAN,
        "lines": [
            "Frecce ↑ ← ↓ →      Movimento (su / sx / giù / dx)",
            "H                    Hackera terminali vicini",
            "6 - 9 / 0            Seleziona slot inventario (6=slot1 … 0=slot5)",
            "O / P                Scorri inventario su / giù",
            "J                    Butta oggetto a terra",
        ],
    },
    {
        "title": "MENU BOTTINO (si apre con E vicino a loot)",
        "color": YELLOW,
        "lines": [
            "↑ / ↓                Naviga la lista oggetti",
            "TAB                  Cambia personaggio destinatario",
            "INVIO / E            Prendi l'oggetto selezionato",
            "ESC                  Chiudi (lascia il resto)",
        ],
    },
    {
        "title": "MENU ABBANDONO OGGETTI (G / J)",
        "color": ORANGE,
        "lines": [
            "↑ / ↓  o  W / S      Naviga la lista oggetti",
            "INVIO                Butta 1 unità dell'oggetto selezionato",
            "SPAZIO               Butta tutte le unità",
            "ESC / G / J          Chiudi il menu",
        ],
    },
    {
        "title": "GAMEPLAY / MECCANICHE",
        "color": YELLOW,
        "lines": [
            "Il gioco si controlla con due personaggi in co-op locale:",
            "Rivet ed Echo.",
            "",
            "Rivet: forza fisica, crafting, sfonda porte blindate.",
            "Echo:  hacking, terminali, tecnologia elettronica.",
            "",
            "Collaborate per esplorare la mappa, raccogliere risorse,",
            "combattere zombie e completare le 3 quest principali.",
            "",
            "Attenzione alle piscine acide: danneggiano chi ci cammina sopra!",
            "Non allontanatevi troppo l'uno dall'altro: la co-op è vitale.",
            "",
            "Risorse da tenere d'occhio:",
            "  HP  — Punti vita. Se entrambi arrivano a 0, è Game Over.",
            "  AP  — Punti azione. Si usano in battaglia.",
            "  XP  — Esperienza. Sbloccano abilità nella Skill Wheel.",
        ],
    },
    {
        "title": "SISTEMA DI COMBATTIMENTO",
        "color": MAGENTA,
        "lines": [
            "Il combattimento è a turni. Ogni turno puoi:",
            "  - Attaccare con l'arma equipaggiata o a mani nude",
            "  - Usare un oggetto dall'inventario",
            "  - Usare la Combo di coppia (Rivet + Echo insieme)",
            "  - Fuggire (non sempre possibile)",
            "",
            "La Combo di coppia ha un cooldown di alcuni turni dopo ogni uso.",
            "Le armi hanno munizioni limitate — gestiscile con cura!",
            "Gli AP si azzerano ad ogni battaglia e si rigenerano al turno.",
        ],
    },
    {
        "title": "HACKING (Solo Echo)",
        "color": CYAN,
        "lines": [
            "Echo può hackerare 3 terminali speciali nella mappa:",
            "",
            "  Terminale Grattacielo → Puzzle PIPE",
            "    Sblocca la porta blindata e la cassaforte interna.",
            "",
            "  Torre Radar            → Puzzle RADAR",
            "    Richiede che la Centrale sia online prima.",
            "",
            "  Terminale Fabbrica     → Puzzle NODE",
            "    Richiede porta sfondata da Rivet e area sicura.",
            "",
            "Avvicinati al terminale con Echo e premi H per iniziare.",
        ],
    },
    {
        "title": "ETICA E REPUTAZIONE",
        "color": ORANGE,
        "lines": [
            "Le tue scelte influenzano due sistemi:",
            "",
            "Etica (da -10 a +10):",
            "  Scelte buone alzano l'etica, scelte corrotte la abbassano.",
            "  Ogni 5 punti di etica in salita: +15 XP a entrambi.",
            "",
            "Reputazione (per fazione):",
            "  Razziatori, Solidali, Erranti, Dannati.",
            "  Influenza dialoghi e comportamento degli NPC.",
            "  Ogni 5 punti di reputazione in salita: +15 XP a entrambi.",
        ],
    },
    {
        "title": "REGOLE PRINCIPALI",
        "color": RED,
        "lines": [
            "Vittoria: completa le 3 quest principali e affronta",
            "          la decisione finale nella Fabbrica.",
            "",
            "Sconfitta: se Rivet o Echo muoiono durante l'esplorazione",
            "           o entrambi muoiono in battaglia, è Game Over.",
            "",
            "Salvataggi: usa il menu Pausa (P) per salvare.",
            "            Sono disponibili 3 slot persistenti su disco.",
            "",
            "Le scelte nei dialoghi sono permanenti.",
            "Scegli il tono (Rivet: Minaccioso/Pragmatico,",
            "Echo: Empatico/Diplomatico) con attenzione.",
        ],
    },
]


class HelpScreen(Screen):
    """
    Schermata di aiuto con scroll verticale ed effetti visivi.

    Ricorda la schermata di provenienza (menu / pause) tramite
    il flag gs.flags["help_return_screen"] impostato prima di
    navigare qui.
    """

    def __init__(self, fonts):
        self.fonts       = fonts
        self._scroll_y   = 0
        self._max_scroll = 0
        self._content_h  = 0
        self._return_to  = "menu"
        self._tick       = 0

        self._scanline_surf: Surface | None = None

        self._compute_content_height()


    def _compute_content_height(self) -> None:
        """Calcola l'altezza totale di tutte le sezioni per lo scroll."""
        h = 0
        for section in _HELP_SECTIONS:
            h += _SECTION_H
            h += len(section["lines"]) * _LINE_H
            h += _SECTION_GAP
        self._content_h = h


    def _build_scanline_surf(self, w: int, h: int) -> Surface:
        """Genera una superficie SRCALPHA con righe orizzontali scure ogni 2px."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for y in range(0, h, 2):
            pygame.draw.line(surf, _SCANLINE_COLOR, (0, y), (w, y))
        return surf


    def on_enter(self):
        gs = GameManager.get_instance()
        self._scroll_y  = 0
        self._tick      = 0
        self._return_to = gs.flags.get("help_return_screen", "menu")

        visible_h = H - _TITLE_H - _FOOTER_H - 40
        self._max_scroll = max(0, self._content_h - visible_h)

        self._scanline_surf = None

    def update(self):
        self._tick += 1

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            k = event.key

            if k in (pygame.K_UP, pygame.K_w):
                self._scroll_y = max(0, self._scroll_y - _SCROLL_SPEED)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self._scroll_y = min(self._max_scroll, self._scroll_y + _SCROLL_SPEED)

            elif k == pygame.K_PAGEUP:
                self._scroll_y = max(0, self._scroll_y - _SCROLL_SPEED * 6)
            elif k == pygame.K_PAGEDOWN:
                self._scroll_y = min(self._max_scroll, self._scroll_y + _SCROLL_SPEED * 6)

            elif k == pygame.K_HOME:
                self._scroll_y = 0
            elif k == pygame.K_END:
                self._scroll_y = self._max_scroll

            elif k in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE):
                self._go_back()

        elif event.type == pygame.MOUSEWHEEL:
            self._scroll_y -= event.y * _SCROLL_SPEED
            self._scroll_y = max(0, min(self._max_scroll, self._scroll_y))


    def draw(self, surf: Surface):
        fn = self.fonts
        cx = W // 2

        surf.fill(BG)

        self._draw_bg_dots(surf)

        px = cx - _PW // 2
        py = 20
        ph = H - 40

        shadow_surf = pygame.Surface((_PW, ph), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 90))
        surf.blit(shadow_surf, (px + 4, py + 4))

        panel(surf, px, py, _PW, ph, BG2, _PANEL_BORDER_LIT, 8)

        pygame.draw.rect(surf, CYAN, (px, py + 12, 4, ph - 24), border_radius=2)

        txt(surf, "══  REGOLE / AIUTO  ══", cx, py + 30, CYAN, fn["xl"], center=True)

        self._draw_fancy_sep(surf, px + 20, py + 54, _PW - 40, CYAN)

        content_x = px + _MARGIN_X
        content_y = py + _TITLE_H
        content_w = _PW - _MARGIN_X * 2
        content_h = ph - _TITLE_H - _FOOTER_H

        clip_rect = pygame.Rect(px, content_y, _PW, content_h)
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        draw_y = content_y - self._scroll_y

        for section in _HELP_SECTIONS:
            sec_color = section.get("color", WHITE)

            if content_y - _SECTION_H <= draw_y <= content_y + content_h:
                self._draw_section_highlight(surf, px + 6, draw_y,
                                             _PW - 12, _SECTION_H, sec_color)
                dot_x = content_x - 10
                dot_y = draw_y + _SECTION_H // 2
                pygame.draw.circle(surf, sec_color, (dot_x, dot_y), 4)
                pygame.draw.circle(surf, BG2, (dot_x, dot_y), 2)

                txt(surf, section["title"], content_x, draw_y + 7,
                    sec_color, fn["bold"], center=False)
            draw_y += _SECTION_H

            for line in section["lines"]:
                if content_y - _LINE_H <= draw_y <= content_y + content_h:
                    if line != "":
                        alpha = self._edge_fade_alpha(draw_y, content_y, content_y + content_h)
                        line_color = self._alpha_blend_color(WHITE, BG2, alpha)
                        txt(surf, line, content_x + 14, draw_y,
                            line_color, fn["sm"], center=False)
                draw_y += _LINE_H

            draw_y += _SECTION_GAP

        surf.set_clip(old_clip)

        if self._scanline_surf is None:
            self._scanline_surf = self._build_scanline_surf(_PW, ph)
        surf.blit(self._scanline_surf, (px, py))

        self._draw_content_fade(surf, px, content_y, _PW, content_h)

        if self._max_scroll > 0:
            self._draw_scrollbar(surf, px + _PW - 14, content_y, 6, content_h)

        footer_y = py + ph - _FOOTER_H
        self._draw_fancy_sep(surf, px + 20, footer_y, _PW - 40, GREY)

        txt(surf, "↑↓ scrolla  •  ESC indietro",
            cx, footer_y + 10, GREY, fn["sm"], center=True)


    def _draw_bg_dots(self, surf: Surface) -> None:
        """Griglia di punti molto sottile come texture di sfondo."""
        dot_color = (30, 40, 50)
        spacing = 28
        for gx in range(0, W, spacing):
            for gy in range(0, H, spacing):
                pygame.draw.circle(surf, dot_color, (gx, gy), 1)

    def _draw_glow_text(self, surf: Surface, text: str, x: int, y: int,
                        color: tuple, font, alpha: int) -> None:
        """Disegna un alone morbido sotto il testo del titolo."""
        glow_surf = pygame.Surface((len(text) * 14 + 40, 50), pygame.SRCALPHA)
        glow_color = (*color[:3], alpha)
        pygame.draw.ellipse(glow_surf, glow_color,
                            (0, 0, glow_surf.get_width(), glow_surf.get_height()))
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surf.blit(glow_surf,
                      (x - glow_surf.get_width() // 2 + ox,
                       y - 20 + oy))

    def _draw_fancy_sep(self, surf: Surface, x: int, y: int,
                        w: int, color: tuple) -> None:
        """Separatore con fade ai bordi."""
        sep_surf = pygame.Surface((w, 2), pygame.SRCALPHA)
        for i in range(w):
            ratio = i / w
            fade = int(255 * (1 - abs(ratio - 0.5) * 2))
            c = (*color[:3], fade)
            pygame.draw.line(sep_surf, c, (i, 0), (i, 1))
        surf.blit(sep_surf, (x, y))

    def _draw_section_highlight(self, surf: Surface, x: int, y: int,
                                w: int, h: int, color: tuple) -> None:
        """Rettangolo di highlight semitrasparente per i titoli di sezione."""
        hl = pygame.Surface((w, h), pygame.SRCALPHA)
        r, g, b = color[:3]
        hl.fill((r, g, b, 18))
        pygame.draw.rect(hl, (*color[:3], 140), (0, 0, 3, h))
        surf.blit(hl, (x, y))

    def _draw_content_fade(self, surf: Surface, x: int, y: int,
                           w: int, h: int) -> None:
        """Fade nero ai bordi superiore e inferiore dell'area contenuto."""
        fade_h = 28
        bg_r, bg_g, bg_b = BG2[:3] if len(BG2) >= 3 else (20, 22, 28)

        for i in range(fade_h):
            alpha = int(220 * (1 - i / fade_h))
            line_surf = pygame.Surface((w, 1), pygame.SRCALPHA)
            line_surf.fill((bg_r, bg_g, bg_b, alpha))
            surf.blit(line_surf, (x, y + i))

        for i in range(fade_h):
            alpha = int(220 * (i / fade_h))
            line_surf = pygame.Surface((w, 1), pygame.SRCALPHA)
            line_surf.fill((bg_r, bg_g, bg_b, alpha))
            surf.blit(line_surf, (x, y + h - fade_h + i))

    def _edge_fade_alpha(self, draw_y: int, top: int, bottom: int) -> int:
        """Restituisce alpha 0-255 per il fade-in ai bordi dell'area visibile."""
        fade_zone = 32
        if draw_y - top < fade_zone:
            return int(255 * max(0, (draw_y - top) / fade_zone))
        if bottom - draw_y < fade_zone:
            return int(255 * max(0, (bottom - draw_y) / fade_zone))
        return 255

    @staticmethod
    def _alpha_blend_color(fg: tuple, bg: tuple, alpha: int) -> tuple:
        """Blend lineare tra fg e bg dato alpha 0-255."""
        if alpha >= 255:
            return fg[:3]
        t = alpha / 255
        fr, fg_, fb = fg[:3]
        br, bg_, bb = bg[:3]
        return (
            int(fr * t + br * (1 - t)),
            int(fg_ * t + bg_ * (1 - t)),
            int(fb * t + bb * (1 - t)),
        )


    def _draw_scrollbar(self, surf: Surface, x: int, y: int, w: int, h: int):
        """Disegna una scrollbar verticale minimale."""
        if self._content_h <= 0:
            return

        pygame.draw.rect(surf, DARKGREY, (x, y, w, h), border_radius=3)

        visible_ratio = min(1.0, h / self._content_h)
        thumb_h = max(20, int(h * visible_ratio))

        if self._max_scroll > 0:
            scroll_ratio = self._scroll_y / self._max_scroll
        else:
            scroll_ratio = 0

        thumb_y = y + int((h - thumb_h) * scroll_ratio)

        glow_w = w + 4
        glow_surf = pygame.Surface((glow_w, thumb_h + 4), pygame.SRCALPHA)
        glow_surf.fill((0, 220, 255, 40))
        surf.blit(glow_surf, (x - 2, thumb_y - 2))

        pygame.draw.rect(surf, CYAN, (x, thumb_y, w, thumb_h), border_radius=3)


    def _go_back(self):
        """Torna alla schermata di provenienza."""
        gs = GameManager.get_instance()
        gs.screen = self._return_to
