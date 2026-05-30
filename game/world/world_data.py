"""
world_data.py — Costanti globali di configurazione del gioco e dati statici del mondo.

Questo modulo è importato da quasi tutti gli altri moduli; non deve avere
dipendenze su altri moduli del gioco (evita import circolari).

Sezioni
-------
- Dimensioni schermo e mappa
- Palette colori
- Distretti della mappa
- Colori e ostilità di default per fazione
- NPC con posizioni, dialoghi e soglie di reputazione
- Terminali, mine, loot spot
- Helper ``npc_is_hostile``
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Dimensioni schermo e mappa
# ---------------------------------------------------------------------------

W, H      = 1200, 750   # Risoluzione logica del canvas di gioco (pixel)
FPS       = 60           # Frame per secondo target
TILE      = 48           # Dimensione di una tile (pixel) nella mappa di esplorazione
MAP_COLS  = 64           # Numero di colonne della mappa di esplorazione
MAP_ROWS  = 48           # Numero di righe della mappa di esplorazione

# ---------------------------------------------------------------------------
# Palette colori (RGB)
# ---------------------------------------------------------------------------

BG       = (13,  13,  13)    # Sfondo principale
BG2      = (22,  22,  22)    # Sfondo secondario (pannelli)
BG3      = (30,  30,  30)    # Sfondo terziario
CYAN     = (0,   229, 255)   # Colore accento principale (giocatore P1, highlight)
GREEN    = (57,  255, 20)    # HP alta / fazione Solidali / conferma
RED      = (255, 45,  45)    # HP bassa / pericolo / errore
YELLOW   = (255, 214, 0)     # HP media / loot / giocatore P2
MAGENTA  = (255, 0,   255)   # Accento secondario
GREY     = (85,  85,  85)    # Bordi, testo secondario
WHITE    = (224, 224, 224)   # Testo principale
ORANGE   = (255, 145, 0)     # Avviso / armi speciali
DARKGREY = (34,  34,  34)    # Sfondo barre HP
PANEL    = (18,  18,  28)    # Sfondo pannelli UI

# ---------------------------------------------------------------------------
# Distretti della mappa
# ---------------------------------------------------------------------------

# Mappa: (col_centro, row_centro) → (nome, sigla, colore_sfondo_tile)
DISTRICTS: dict[tuple[int,int], tuple[str,str,tuple]] = {
    (90, 60):  ("Città",             "C", (0,  50,  68)),
    (160, 20): ("Areoporto Militare","A", (45, 26,   0)),
    (30, 120): ("Zona Rurale",       "R", (20, 55,  10)),
    (160, 120):("Fabbrica Chimica",  "F", (55, 28,  10)),
}

# ---------------------------------------------------------------------------
# Fazioni: colori marker mappa e flag ostilità di default
# ---------------------------------------------------------------------------

FACTION_COLOR: dict[str, tuple] = {
    "solidali":   (57,  255, 20),    # verde brillante
    "erranti":    (255, 214,  0),    # giallo
    "dannati":    (180,  80, 80),    # rosso scuro
    "razziatori": (255,  80,  0),    # arancione
    "zombie":     (120, 200,  60),   # verde malsano
}

# True = la fazione è ostile per default (attacca alla vista se rep bassa)
FACTION_ENEMY: dict[str, bool] = {
    "solidali":   False,
    "erranti":    False,
    "dannati":    True,
    "razziatori": True,
    "zombie":     True,
}

# ---------------------------------------------------------------------------
# NPC statici della mappa
# ---------------------------------------------------------------------------

# Ogni NPC è un dict con:
#   name         : nome visualizzato
#   pos          : (col, row) sulla mappa di esplorazione
#   faction      : fazione di appartenenza
#   sprite       : chiave dello sprite nell'AssetLoader
#   rep_threshold: soglia di reputazione sotto cui attacca (solo per faction ostili)
#   lines        : lista di battute di dialogo casuali
NPCS: list[dict] = [
    {"name": "Marco", "pos": (20, 22), "faction": "solidali",
     "sprite": "Solidale_1", "rep_threshold": -20,
     "lines": [
         "La Resistenza ha bisogno di voi!",
         "Portate medicine all'ospedale.",
         "Ho sentito di scorte nel magazzino nord.",
         "Attenti ai Dannati, non si può ragionare con loro.",
     ]},
    {"name": "Vera", "pos": (16, 20), "faction": "solidali",
     "sprite": "Solidale_2", "rep_threshold": -20,
     "lines": [
         "Abbiamo ancora fede nell'umanità.",
         "Se hai cibo da spartire, vieni da noi.",
         "I Razziatori bloccano la strada per l'aeroporto.",
         "Cerca il terminale nascosto vicino al viale.",
     ]},
    {"name": "Sybil", "pos": (10,  8), "faction": "erranti",
     "sprite": "Errante_1", "rep_threshold": -30,
     "lines": [
         "Attenti ai Razziatori all'aeroporto.",
         "Ho sentito di un terminale nascosto.",
         "Non mi fido di nessuno, ma voi sembrate ok.",
         "Il fiume è l'unica via sicura verso sud.",
     ]},
    {"name": "Rael", "pos": (12, 14), "faction": "erranti",
     "sprite": "Errante_2", "rep_threshold": -30,
     "lines": [
         "Vago da settimane. Niente di sicuro.",
         "Ho visto uno zombie corazzato a est.",
         "Se trovate acqua potabile, venite a dirmelo.",
         "I Solidali pagano bene per informazioni.",
     ]},
    {"name": "Tomas", "pos": (25, 36), "faction": "dannati",
     "sprite": "Dannato_1", "rep_threshold": 40,
     "lines": ["...", "Non potete aiutarci.", "Andatevene.", "Qui non siete i benvenuti."]},
    {"name": "Griss", "pos": (28, 40), "faction": "dannati",
     "sprite": "Dannato_2", "rep_threshold": 40,
     "lines": ["Siete ancora vivi? Strano.", "Questo territorio è nostro.", "Fuori dai piedi.", "Non fidarsi è l'unica legge."]},
    {"name": "Scar", "pos": (44, 10), "faction": "razziatori",
     "sprite": "Razziatore_1", "rep_threshold": 30,
     "lines": ["Paghi il pedaggio o passi con la forza.", "L'aeroporto è nostro.", "Avete qualcosa di valore?", "Fate i bravi e non vi faremo del male."]},
    {"name": "Vex", "pos": (50, 12), "faction": "razziatori",
     "sprite": "Razziatore_2", "rep_threshold": 30,
     "lines": ["Ho visto cose peggiori di voi.", "Questo è territorio Razziatore.", "Portate un tributo al capo.", "Circolate."]},
    {"name": "Infetto",         "pos": (30, 20), "faction": "zombie",
     "sprite": "Infetto_Lento",     "rep_threshold": 999,
     "lines": ["...RRGH...", "...*ruggito*..."]},
    {"name": "Gigante di Carne","pos": (46, 30), "faction": "zombie",
     "sprite": "Infetto_Gigante",   "rep_threshold": 999,
     "lines": ["*urlo acuto*", "...*sibilo*..."]},
    {"name": "Corazzato",       "pos": (52, 20), "faction": "zombie",
     "sprite": "Infetto_Corazzato", "rep_threshold": 999,
     "lines": ["*fragore metallico*", "..."]},
    {"name": "Orda",            "pos": (20, 42), "faction": "zombie",
     "sprite": "Orda_Infetta",      "rep_threshold": 999,
     "lines": ["...rumore di passi...", "..."]},
]

# ---------------------------------------------------------------------------
# Punti di interazione del mondo
# ---------------------------------------------------------------------------

# Terminali hackabili (solo Echo può interagire)
TERMINALS: list[tuple[int,int]] = [
    (61, 56),
    (162, 31),
    (171, 103),
]

# Posizioni dove si possono piazzare mine
MINE_SPOTS: list[tuple[int,int]] = [
    (146, 54), (152, 58), (156, 51), (143, 63),
    (167, 59), (170, 47), (176, 63), (182, 58),
    (175, 54), (162, 52), (140, 55), (138, 48),
]

# Spot speciale per il piazzamento delle mine nella fabbrica
MINE_PLACEMENT_SPOT: tuple[int,int] = (167, 130)

# Pannello di controllo della centrale elettrica
POWER_PANEL_SPOT: tuple[int,int] = (177, 150)

# Spot di loot sulla mappa: ogni entry ha posizione, tipo di zona e label UI
LOOT_SPOTS: list[dict] = [
    {"pos": (22, 24), "zone_type": "common_house",  "label": "Casa Comune"},
    {"pos": (16, 10), "zone_type": "pharmacy",      "label": "Farmacia"},
    {"pos": (50, 14), "zone_type": "supermarket",   "label": "Supermercato"},
    {"pos": (42, 36), "zone_type": "laboratorio",   "label": "Laboratorio"},
    {"pos": ( 6, 38), "zone_type": "common_house",  "label": "Edificio Residenziale"},
    {"pos": (28, 24), "zone_type": "industrial",    "label": "Impianto Industriale"},
    {"pos": (14, 22), "zone_type": "common_house",  "label": "Appartamenti"},
]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def npc_is_hostile(npc: dict, reps: dict) -> bool:
    """Verifica se un NPC attacca alla vista in base alla fazione e reputazione.

    Un NPC è ostile se la sua fazione è intrinsecamente nemica
    (``FACTION_ENEMY[faction] == True``) E la reputazione del giocatore
    verso quella fazione è inferiore alla soglia dell'NPC.

    Args:
        npc:  Dizionario dell'NPC (da ``NPCS``), con chiavi "faction" e "rep_threshold".
        reps: Dizionario ``{nome_fazione: reputazione_corrente}``.

    Returns:
        ``True`` se l'NPC deve attaccare alla vista, ``False`` altrimenti.
    """
    f = npc["faction"]
    if FACTION_ENEMY.get(f, False):
        return reps.get(f, 0) < npc["rep_threshold"]
    return False
