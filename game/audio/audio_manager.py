"""
audio_manager.py — Facade GoF sul sottosistema pygame.mixer.

``AudioManager`` è l'unico punto di contatto del gioco con ``pygame.mixer``.
Nessun altro modulo deve chiamare ``pygame.mixer`` direttamente.

Pattern utilizzati
------------------
- **Facade GoF** — nasconde l'intera API pygame.mixer dietro un'interfaccia
  semplice e coerente (``load_music``, ``play_music``, ``apply_for_screen``, ecc.).
- **Strategy GoF (Table-Driven)** — ogni screen è associata a una ``Callable``
  nel dizionario ``_screen_audio_map``. ``apply_for_screen()`` non usa una catena
  if/elif ma esegue la strategia registrata per la screen corrente.
  Aggiungere audio a una nuova screen richiede una sola riga in ``_build_audio_map()``
  o una chiamata a ``register_screen_audio()``, senza modificare la logica esistente
  (Open/Closed Principle).
"""

from __future__ import annotations
from typing import Callable
import pygame


class AudioManager:
    """Facade GoF sul sottosistema pygame.mixer.

    Gestisce il ciclo di vita del mixer (``initialize``/``shutdown``),
    il caricamento di tracce e suoni, la riproduzione, il controllo del volume
    e il dispatch audio per screen tramite Strategy Table-Driven.

    Attributes di classe:
        _MIXER_FREQUENCY: Frequenza di campionamento in Hz (44100).
        _MIXER_SIZE:      Dimensione del campione (-16 = 16 bit signed).
        _MIXER_CHANNELS:  Canali audio (2 = stereo).
        _MIXER_BUFFER:    Dimensione del buffer in frames (512).
    """

    _MIXER_FREQUENCY: int = 44100
    _MIXER_SIZE:      int = -16
    _MIXER_CHANNELS:  int = 2
    _MIXER_BUFFER:    int = 512

    def __init__(self):
        self.current_music_key:      str | None = None   # Chiave traccia corrente
        self.current_loop_sound_key: str | None = None   # Chiave suono in loop corrente

        self.music_volume: float = 0.6
        self.sfx_volume:   float = 0.8

        self.music_tracks:  dict[str, str]               = {}   # key → path
        self.sounds:        dict[str, pygame.mixer.Sound] = {}   # key → Sound
        self.music_volumes: dict[str, float]             = {}   # key → volume override

        self._mixer_ready:      bool                           = False
        self._screen_audio_map: dict[str, Callable[[], None]] = {}

    def _build_audio_map(self) -> None:
        """Costruisce la Strategy map ``screen_name → azione audio``.

        Chiamato dal ``GameManager`` dopo il caricamento delle risorse audio,
        quando le lambda possono catturare correttamente i suoni registrati.

        Per aggiungere audio a una nuova screen: aggiungere una voce qui.
        La logica di ``apply_for_screen()`` non va mai modificata.
        """
        self._screen_audio_map = {
            "menu": lambda: (
                self.stop_all_sounds(),
                self.play_sound("menu_zombie", loops=-1),
            ),
            "select": lambda: (
                self.stop_all_sounds(),
                self.play_sound("select_zombie", loops=-1),
            ),
            "explore": lambda: (
                self.stop_all_sounds(),
                self.play_music("explore", loops=-1, fade_ms=500),
            ),
            "battle": lambda: (
                self.stop_all_sounds(),
                self.play_music("combat", loops=-1, fade_ms=500),
            ),
            "gameover": lambda: (
                self.stop_music(fade_ms=0),
                setattr(self, "current_music_key", None),
            ),
            "victory":         lambda: self.play_music("victory", loops=-1, fade_ms=300),
            "factory_finale":  lambda: self.play_music("victory", loops=-1, fade_ms=300),
        }

    def register_screen_audio(
        self, screen_name: str, strategy: Callable[[], None]
    ) -> None:
        """Registra o sovrascrive la strategia audio per una screen.

        Permette a moduli esterni di collegare la propria logica audio
        senza modificare ``AudioManager`` (Open/Closed Principle).

        Args:
            screen_name: Nome della screen (es. "boss_fight").
            strategy:    Callable senza argomenti che esegue le operazioni audio.

        Esempio::

            audio.register_screen_audio(
                "boss_fight",
                lambda: audio.play_music("boss_theme", loops=-1, fade_ms=200)
            )
        """
        self._screen_audio_map[screen_name] = strategy

    # -----------------------------------------------------------------------
    # Ciclo di vita del mixer
    # -----------------------------------------------------------------------

    def initialize(self) -> None:
        """Inizializza ``pygame.mixer`` con i parametri di classe.

        Deve essere chiamato prima di qualsiasi operazione audio.
        Idempotente: chiamate successive a inizializzazione avvenuta sono no-op.
        """
        if self._mixer_ready:
            return
        try:
            pygame.mixer.init(
                frequency=self._MIXER_FREQUENCY,
                size=self._MIXER_SIZE,
                channels=self._MIXER_CHANNELS,
                buffer=self._MIXER_BUFFER,
            )
            self._mixer_ready = True
        except Exception as e:
            print(f"[AudioManager] Impossibile inizializzare pygame.mixer: {e}")

    def shutdown(self) -> None:
        """Ferma tutto l'audio e chiude ``pygame.mixer``.

        Deve essere chiamato alla chiusura del gioco per rilasciare
        le risorse audio in modo ordinato.
        """
        if not self._mixer_ready:
            return
        try:
            self.stop_all()
            pygame.mixer.quit()
        except Exception as e:
            print(f"[AudioManager] Errore durante lo shutdown del mixer: {e}")
        finally:
            self._mixer_ready = False

    def _guard(self) -> bool:
        """Verifica che il mixer sia inizializzato prima di qualsiasi operazione.

        Returns:
            ``True`` se il mixer è pronto, ``False`` altrimenti (con log).
        """
        if not self._mixer_ready:
            print("[AudioManager] Mixer non inizializzato — chiama initialize() prima.")
            return False
        return True

    # -----------------------------------------------------------------------
    # Caricamento risorse
    # -----------------------------------------------------------------------

    def load_music(self, key: str, path: str, volume: float | None = None) -> None:
        """Registra una traccia musicale nel dizionario interno (senza caricarla in memoria).

        Args:
            key:    Chiave di riferimento (es. "explore", "combat").
            path:   Path assoluto al file audio.
            volume: Volume specifico per questa traccia; se ``None`` usa ``music_volume``.
        """
        self.music_tracks[key]  = path
        self.music_volumes[key] = volume if volume is not None else self.music_volume

    def load_sound(self, key: str, path: str, volume: float | None = None) -> None:
        """Carica un effetto sonoro in memoria e lo registra nel dizionario interno.

        Args:
            key:    Chiave di riferimento (es. "menu_zombie", "gunshot").
            path:   Path assoluto al file audio.
            volume: Volume specifico; se ``None`` usa ``sfx_volume``.
        """
        if not self._guard():
            return
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(self.sfx_volume if volume is None else volume)
            self.sounds[key] = snd
        except Exception as e:
            print(f"[AudioManager] Errore caricamento suono '{key}': {e}")

    # -----------------------------------------------------------------------
    # Riproduzione musica
    # -----------------------------------------------------------------------

    def play_music_direct(self, path: str, volume: float = 1.0,
                          loops: int = -1, fade_ms: int = 0) -> None:
        """Carica e avvia una traccia direttamente da path, senza chiave registro.

        Usato da ``IntroScreen`` e ``SelectScreen`` per la musica dell'intro,
        che non è registrata nel dizionario ``music_tracks``.

        Args:
            path:    Path assoluto al file audio.
            volume:  Volume di riproduzione (0.0–1.0).
            loops:   Numero di ripetizioni (-1 = infinito).
            fade_ms: Millisecondi di fade-in.
        """
        if not self._guard():
            return
        try:
            import os
            if not os.path.exists(path):
                print(f"[AudioManager] File non trovato: {path}")
                return
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            self.current_music_key = None
        except Exception as e:
            print(f"[AudioManager] Errore play_music_direct('{path}'): {e}")

    def is_music_busy(self) -> bool:
        """Restituisce ``True`` se una traccia musicale è attualmente in riproduzione."""
        if not self._guard():
            return False
        try:
            return pygame.mixer.music.get_busy()
        except Exception:
            return False

    def play_music(self, key: str, loops: int = -1, fade_ms: int = 500) -> None:
        """Avvia la traccia registrata con ``key``, con fade-in opzionale.

        Se la traccia è già in riproduzione (``current_music_key == key``),
        la chiamata è no-op per evitare restart inutili.

        Args:
            key:     Chiave della traccia (registrata con ``load_music``).
            loops:   Numero di ripetizioni (-1 = infinito).
            fade_ms: Millisecondi di fade-in (e fade-out della traccia precedente).
        """
        if not self._guard():
            return
        if self.current_music_key == key:
            return
        path = self.music_tracks.get(key)
        if not path:
            print(f"[AudioManager] Traccia music '{key}' non trovata.")
            return
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
            pygame.mixer.music.load(path)
            vol = self.music_volumes.get(key, self.music_volume)
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self.current_music_key = key
        except Exception as e:
            print(f"[AudioManager] Errore play_music('{key}'): {e}")

    def stop_music(self, fade_ms: int = 300) -> None:
        """Ferma la musica corrente con fade-out opzionale.

        Args:
            fade_ms: Millisecondi di fade-out (0 = stop immediato).
        """
        if not self._guard():
            return
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
            self.current_music_key = None
        except Exception as e:
            print(f"[AudioManager] Errore stop_music: {e}")

    # -----------------------------------------------------------------------
    # Riproduzione effetti sonori
    # -----------------------------------------------------------------------

    def play_sound(self, key: str, loops: int = 0) -> None:
        """Avvia un effetto sonoro registrato.

        Args:
            key:   Chiave del suono (registrato con ``load_sound``).
            loops: Numero di ripetizioni (-1 = loop infinito).
        """
        snd = self.sounds.get(key)
        if not snd:
            print(f"[AudioManager] Suono '{key}' non trovato.")
            return
        try:
            snd.play(loops=loops)
            if loops == -1:
                self.current_loop_sound_key = key
        except Exception as e:
            print(f"[AudioManager] Errore play_sound('{key}'): {e}")

    def stop_sound(self, key: str) -> None:
        """Ferma un effetto sonoro specifico.

        Args:
            key: Chiave del suono da fermare.
        """
        snd = self.sounds.get(key)
        if snd:
            snd.stop()
        if self.current_loop_sound_key == key:
            self.current_loop_sound_key = None

    def stop_loop_sound(self) -> None:
        """Ferma il suono attualmente in loop (se presente)."""
        if self.current_loop_sound_key:
            snd = self.sounds.get(self.current_loop_sound_key)
            if snd:
                snd.stop()
            self.current_loop_sound_key = None

    def stop_all_sounds(self) -> None:
        """Ferma tutti gli effetti sonori caricati."""
        for snd in self.sounds.values():
            snd.stop()
        self.current_loop_sound_key = None

    # -----------------------------------------------------------------------
    # Dispatch audio per screen (Strategy Table-Driven)
    # -----------------------------------------------------------------------

    def apply_for_screen(self, screen_name: str) -> None:
        """Applica la strategia audio associata alla screen indicata.

        Esegue prima le operazioni di stop comuni (musica + suoni in loop),
        poi delega alla strategia registrata in ``_screen_audio_map``.

        Se la screen non ha una strategia (screen silenziose come pause, craft,
        ecc.), il metodo si limita allo stop comune: nessun nuovo suono viene
        avviato, che è il comportamento corretto per quelle screen.

        Per aggiungere audio a una nuova screen::

            audio.register_screen_audio("nuova_screen", lambda: ...)

        oppure aggiungere una voce in ``_build_audio_map()``.
        Non modificare mai la logica di questo metodo.

        Args:
            screen_name: Identificatore della screen corrente (es. "battle").
        """
        if not self._guard():
            return

        # Stop comune — sempre eseguito indipendentemente dalla screen
        self.stop_music(fade_ms=0)
        self.current_music_key = None
        self.stop_loop_sound()

        # Dispatch alla strategia specifica (se registrata)
        strategy = self._screen_audio_map.get(screen_name)
        if strategy:
            strategy()

    # -----------------------------------------------------------------------
    # Controllo volume
    # -----------------------------------------------------------------------

    def set_music_volume(self, volume: float) -> None:
        """Imposta il volume della musica (clampato tra 0.0 e 1.0).

        Args:
            volume: Nuovo volume musicale.
        """
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume: float) -> None:
        """Imposta il volume degli effetti sonori per tutti i suoni caricati.

        Args:
            volume: Nuovo volume SFX (0.0–1.0).
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        for snd in self.sounds.values():
            snd.set_volume(self.sfx_volume)

    def stop_all(self, fade_ms: int = 300) -> None:
        """Ferma musica e tutti gli effetti sonori.

        Args:
            fade_ms: Millisecondi di fade-out per la musica.
        """
        self.stop_music(fade_ms)
        self.stop_all_sounds()
