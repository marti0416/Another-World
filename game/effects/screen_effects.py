"""
screen_effects.py — Effetti visivi a schermo: camera shake e glitch RGB.

Entrambe le classi seguono lo stesso ciclo di vita:
    trigger(...)  → avvia o sovrascrive un effetto in corso
    update()      → chiamato ogni frame, aggiorna lo stato interno
    draw(surf)    → applica l'effetto sulla surface (solo GlitchEffect)
    active        → property bool, True finché l'effetto è in corso
"""

from __future__ import annotations
import random
import pygame
from pygame import Surface


class CameraShake:
    """Scuotimento leggero dello schermo (camera shake).

    Genera un offset (dx, dy) casuale ad ogni frame per simulare
    l'impatto di un'esplosione, un colpo potente o un evento drammatico.
    L'intensità decade esponenzialmente finché la durata non si azzera.

    Uso tipico::

        shake = CameraShake()
        shake.trigger(intensity=6, duration=20)
        # ogni frame:
        offset = shake.update()
        surf.blit(scene, offset)
    """

    def __init__(self):
        self._intensity: float = 0.0
        self._duration:  int   = 0
        self._offset:    tuple[int, int] = (0, 0)

    def trigger(self, intensity: float = 5.0, duration: int = 20) -> None:
        """Avvia o intensifica lo shake.

        Se uno shake è già in corso, i parametri vengono combinati
        prendendo il massimo di intensità e durata (gli shake si sommano).

        Args:
            intensity: Ampiezza massima dello scuotimento in pixel.
            duration:  Numero di frame di durata dello shake.
        """
        self._intensity = max(self._intensity, intensity)
        self._duration  = max(self._duration,  duration)

    def update(self) -> tuple[int, int]:
        """Aggiorna lo shake e restituisce l'offset da applicare al blit.

        L'intensità decade del 8% per frame (fattore 0.92).
        Quando la durata scade, restituisce (0, 0).

        Returns:
            Coppia (dx, dy) in pixel da usare come offset per blit della scena.
        """
        if self._duration <= 0:
            self._offset = (0, 0)
            return self._offset

        dx = random.randint(-1, 1) * self._intensity
        dy = random.randint(-1, 1) * self._intensity
        self._offset    = (int(dx), int(dy))
        self._intensity *= 0.92   # decadimento esponenziale
        self._duration  -= 1
        return self._offset

    @property
    def active(self) -> bool:
        """``True`` se lo shake è ancora in corso."""
        return self._duration > 0


class GlitchEffect:
    """Effetto glitch digitale: RGB-split orizzontale e scanline corrotte.

    Simula artefatti video digitali sovrapposti alla surface.
    L'effetto ha due componenti:
    - **RGB-split**: un layer rosso leggermente spostato orizzontalmente.
    - **Scanline**: strisce orizzontali corrotte con shift e trasparenza variabile.

    Uso tipico::

        glitch = GlitchEffect()
        glitch.trigger(strength=8, duration=12)
        # ogni frame:
        glitch.update()
        glitch.draw(surf)
    """

    def __init__(self):
        self._strength:   int         = 0
        self._duration:   int         = 0
        self._lines:      list[dict]  = []
        self._rgb_offset: int         = 0

    def trigger(self, strength: int = 6, duration: int = 12) -> None:
        """Avvia o intensifica l'effetto glitch.

        Args:
            strength: Intensità del glitch (ampiezza shift scanline e offset RGB).
            duration: Durata in frame.
        """
        self._strength   = max(self._strength, strength)
        self._duration   = max(self._duration, duration)
        self._rgb_offset = random.randint(2, strength)
        self._lines      = self._gen_lines()

    def _gen_lines(self) -> list[dict]:
        """Genera un set casuale di scanline corrotte.

        Ogni scanline è descritta da un dict con:
            y     : posizione verticale di partenza,
            h     : altezza in pixel,
            shift : spostamento orizzontale da applicare,
            alpha : opacità del layer di correzione colore.

        Returns:
            Lista di 2–6 dizionari che descrivono le scanline.
        """
        from game.world.world_data import H, W
        lines = []
        n = random.randint(2, 6)
        for _ in range(n):
            lines.append({
                "y":     random.randint(0, H - 4),
                "h":     random.randint(1, 4),
                "shift": random.randint(-self._strength * 2, self._strength * 2),
                "alpha": random.randint(60, 160),
            })
        return lines

    def update(self) -> None:
        """Aggiorna lo stato interno dell'effetto ogni frame.

        Rigenera le scanline ogni 2 frame per simulare l'instabilità digitale.
        L'offset RGB decade di 1 per frame.
        """
        if self._duration <= 0:
            return
        self._duration -= 1
        if self._duration % 2 == 0:
            self._lines = self._gen_lines()
        self._rgb_offset = max(0, self._rgb_offset - 1)

    def draw(self, surf: Surface) -> None:
        """Applica l'effetto glitch sulla surface fornita.

        Disegna il layer RGB-split (canale rosso spostato) e poi le scanline
        corrotte direttamente sulla surface in-place.

        Args:
            surf: La surface pygame su cui applicare l'effetto.
        """
        if self._duration <= 0:
            return

        W, H = surf.get_size()

        # --- RGB-split: layer rosso spostato verso sinistra ---
        if self._rgb_offset > 0:
            o        = self._rgb_offset
            snapshot = surf.copy()

            red_surf  = pygame.Surface((W, H), pygame.SRCALPHA)
            blue_surf = pygame.Surface((W, H), pygame.SRCALPHA)

            # Estrae i pixel con componente rossa significativa ogni 4 righe
            for x in range(W):
                for y in range(0, H, 4):
                    try:
                        r, g, b, a = snapshot.get_at((x, y))
                        if r > 80:
                            red_surf.set_at((x, y), (r, 0, 0, 60))
                    except IndexError:
                        pass

            surf.blit(red_surf,  (-o, 0), special_flags=pygame.BLEND_ADD)
            surf.blit(blue_surf, ( o, 0), special_flags=pygame.BLEND_ADD)

        # --- Scanline corrotte: striscie spostate orizzontalmente ---
        for line in self._lines:
            ly, lh, shift, alpha = line["y"], line["h"], line["shift"], line["alpha"]
            try:
                strip = surf.subsurface((0, ly, W, lh)).copy()
                bar   = pygame.Surface((W, lh), pygame.SRCALPHA)
                bar.fill((200, 220, 255, alpha))
                strip.blit(bar, (0, 0))
                surf.blit(strip, (shift, ly))
            except ValueError:
                pass   # subsurface fuori dai limiti: ignorato silenziosamente

    @property
    def active(self) -> bool:
        """``True`` se l'effetto glitch è ancora in corso."""
        return self._duration > 0
