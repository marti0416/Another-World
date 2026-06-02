"""
mix_audio.py — Script standalone per mescolare due file audio WAV.

Questo script NON fa parte del runtime del gioco: è uno strumento di
preprocessing audio usato in fase di sviluppo per creare tracce miste
(es. la musica del menu che fonde due layer ambientali).

Flusso
------
1. Carica i due file WAV tramite pygame.mixer.
2. Taglia i primi ``TRIM_B_SECONDS`` secondi dal file B.
3. Porta entrambi i file in formato stereo.
4. Li porta alla stessa lunghezza (looping del più corto).
5. Mescola i due segnali con pesi 0.6/0.6 e clampa il risultato.
6. Salva il risultato in ``OUTPUT``.

Requisiti: numpy, pygame.
"""

import numpy as np
import pygame

# --- Parametri configurabili ---
PATH_A         = "iss_pygame/assets/audio/sound_zombie_screen.wav"   # Layer A (zombie ambient)
PATH_B         = "iss_pygame/assets/audio/sound_menu_screen.wav"     # Layer B (musica menu)
OUTPUT         = "iss_pygame/assets/audio/menu_mixed.wav"            # File di output
TRIM_B_SECONDS = 20        # Secondi iniziali da tagliare da B (intro non desiderata)
SAMPLE_RATE    = 44100     # Hz

pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)


def read_wav(path: str) -> np.ndarray:
    """Carica un file WAV tramite pygame e lo restituisce come array numpy.

    Args:
        path: Path al file WAV.

    Returns:
        Array numpy con shape (n_samples,) o (n_samples, 2).
    """
    sound = pygame.mixer.Sound(path)
    array = pygame.sndarray.array(sound)
    return array


def write_wav(path: str, rate: int, data: np.ndarray) -> None:
    """Salva un array numpy come file WAV stereo 16-bit signed.

    Args:
        path: Path di output del file WAV.
        rate: Sample rate in Hz.
        data: Array numpy (n_samples, 2) con dtype int16.
    """
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)       # 2 bytes = 16 bit
        f.setframerate(rate)
        f.writeframes(data.tobytes())


def to_stereo(data: np.ndarray) -> np.ndarray:
    """Converte un segnale mono in stereo duplicando il canale.

    Se il segnale è già stereo (ndim == 2), viene restituito invariato.

    Args:
        data: Array numpy mono (n_samples,) o stereo (n_samples, 2).

    Returns:
        Array numpy con shape (n_samples, 2).
    """
    if data.ndim == 1:
        return np.stack([data, data], axis=1)
    return data


def loop_to_length(data: np.ndarray, target_len: int) -> np.ndarray:
    """Ripete il segnale in loop finché raggiunge (almeno) ``target_len`` sample.

    Args:
        data:       Array del segnale sorgente.
        target_len: Lunghezza desiderata in sample.

    Returns:
        Array troncato esattamente a ``target_len`` sample.
    """
    result = data
    while len(result) < target_len:
        result = np.concatenate([result, data])
    return result[:target_len]


# --- Esecuzione dello script ---

print("Carico file A...")
data_a = to_stereo(read_wav(PATH_A))
print(f"  shape A: {data_a.shape}")

print("Carico file B...")
data_b = to_stereo(read_wav(PATH_B))
print(f"  shape B: {data_b.shape}")

# Taglia l'intro indesiderata di B
trim_samples = TRIM_B_SECONDS * SAMPLE_RATE
data_b = data_b[trim_samples:]
print(f"  shape B dopo trim: {data_b.shape}")

# Porta entrambi alla stessa lunghezza (looping del più corto)
max_len = max(len(data_a), len(data_b))
data_a  = loop_to_length(data_a, max_len)
data_b  = loop_to_length(data_b, max_len)
print(f"  lunghezza finale: {max_len} samples ({max_len / SAMPLE_RATE:.1f}s)")

# Mescola i due layer con pesi 0.6 ciascuno e clampa tra -32768 e 32767
mixed = data_a.astype(np.float32) * 0.6 + data_b.astype(np.float32) * 0.6
mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

write_wav(OUTPUT, SAMPLE_RATE, mixed)
print(f"Salvato: {OUTPUT}")
