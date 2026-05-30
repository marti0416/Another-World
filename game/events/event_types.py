"""
event_types.py — Enumerazione di tutti i tipi di evento del gioco.

``EventType`` è l'unico punto di definizione degli eventi: publisher e subscriber
usano sempre questa enum come chiave, garantendo type safety e autocompletamento IDE.

Aggiungere un nuovo evento significa aggiungere un valore all'enum; non è necessario
modificare ``EventBus`` o i sistemi non interessati.
"""

from enum import Enum, auto


class EventType(Enum):
    """Tutti i tipi di evento pubblicabili sull'``EventBus``.

    I valori sono raggruppati per area funzionale (ciclo di gioco, combattimento,
    reputazione, quests, crafting, armi, HUD, salvataggio, mondo, flag di trama).
    """

    # --- Ciclo di gioco ---
    GAME_STARTED          = auto()   # Il gioco è iniziato (schermata intro completata)
    GAME_OVER             = auto()   # Entrambi i personaggi sono morti
    GAME_WON              = auto()   # Il giocatore ha completato il gioco
    BATTLE_ENDED          = auto()   # Una battaglia è terminata (vittoria o sconfitta)
    START_ENCOUNTER       = auto()   # Inizia uno scontro (trigger da mappa)
    BATTLE_COMMAND        = auto()   # Comando di battaglia inviato dall'UI
    ITEM_PICKUP           = auto()   # Il giocatore raccoglie un oggetto
    REQUEST_BASE_STATE    = auto()   # Richiesta di tornare allo stato base dello schermo
    REQUEST_OVERLAY_STATE = auto()   # Richiesta di aprire un overlay (inventario, mappa, ecc.)
    REQUEST_CLOSE_OVERLAY = auto()   # Richiesta di chiudere l'overlay corrente

    # --- Combattimento ---
    ENEMY_KILLED          = auto()   # Un nemico è stato eliminato
    ENEMY_REANIMATED      = auto()   # Un nemico si è rianimato (Infetto con respawn_chance)
    HEADSHOT              = auto()   # Colpo alla testa (danno bonus)
    CHAIN_EXPLOSION       = auto()   # Esplosione a catena innescata
    NOISE_EVENT           = auto()   # Rumore generato in battaglia (attira nemici)
    NPC_SAVED             = auto()   # Un NPC alleato è stato salvato dagli infetti
    NPC_DAMAGED           = auto()   # Un NPC alleato è stato ferito dal giocatore

    # --- Reputazione e fazioni ---
    REPUTATION_CHANGED    = auto()   # La reputazione verso una fazione è cambiata
    DEVASTATING_WEAPON    = auto()   # Un'arma devastante è stata usata (penalità reputazione)
    TRADE_UNLOCKED        = auto()   # Il commercio con una fazione è stato sbloccato
    SPAWN_PRIORITY        = auto()   # Priorità di spawn modificata (es. bosco cittadino)
    ETHICS_CHANGED        = auto()   # L'etica di coppia è cambiata
    ETHICS_UPDATED        = auto()   # Aggiornamento UI dell'etica di coppia
    FRIENDLY_FIRE         = auto()   # Fuoco amico (colpisce un alleato)

    # --- Esplorazione e mondo ---
    PLAYER_MOVED          = auto()   # Il giocatore si è mosso sulla mappa
    ZONE_ENTERED          = auto()   # Il giocatore è entrato in una zona speciale
    CHEMICAL_DAMAGE_TICK  = auto()   # Tick di danno da zona chimica (senza protezione)
    PLAYER_DAMAGED        = auto()   # Il giocatore ha subito danno
    HEAL_PLAYER           = auto()   # Il giocatore è stato curato

    # --- Dialogo ---
    DIALOGUE_STARTED      = auto()   # Un dialogo è iniziato
    DIALOGUE_ENDED        = auto()   # Un dialogo è terminato

    # --- Quest ---
    QUEST_AVAILABLE       = auto()   # Una quest è diventata disponibile
    QUEST_ACCEPTED        = auto()   # Il giocatore ha accettato una quest
    QUEST_COMPLETED       = auto()   # Una quest è stata completata con successo
    QUEST_FAILED          = auto()   # Una quest è fallita

    # --- Crafting e oggetti ---
    ITEM_CRAFTED          = auto()   # Un oggetto è stato craftato
    ITEM_DISASSEMBLED     = auto()   # Un oggetto è stato smontato
    ITEM_TRANSFERRED      = auto()   # Un oggetto è stato trasferito tra inventari
    DOOR_BREACHED         = auto()   # Una porta blindata è stata sfondata
    OBSTACLE_CLEARED      = auto()   # Un ostacolo è stato rimosso
    TRAP_PLACED           = auto()   # Una trappola è stata piazzata
    TRAP_TRIGGERED        = auto()   # Una trappola è scattata

    # --- Armi ---
    WEAPON_JAMMED         = auto()   # Un'arma si è inceppata
    WEAPON_FIRED          = auto()   # Un colpo è stato sparato
    SPECIAL_WEAPON_USED   = auto()   # Un'arma speciale è stata usata

    # --- UI / HUD ---
    PARTNER_HEALED        = auto()   # Un personaggio ha curato il partner
    HUD_REFRESH           = auto()   # L'HUD deve essere aggiornato

    # --- Salvataggio ---
    SAVE_REQUESTED        = auto()   # Richiesta di salvataggio
    LOAD_REQUESTED        = auto()   # Richiesta di caricamento
    GAME_SAVED            = auto()   # Salvataggio completato con successo
    GAME_LOADED           = auto()   # Caricamento completato con successo
    SAVE_DELETED          = auto()   # Un salvataggio è stato eliminato

    # --- Livello e mappa ---
    LEVEL_LOADED          = auto()   # Un livello (distretto) è stato caricato
    SUPERMARKET_OCCUPANT_SET = auto()# L'occupante del supermercato è stato impostato
    COMBAT_RISK_EVALUATED = auto()   # Il rischio di combattimento è stato valutato

    # --- Flag di trama ---
    FLAG_SET_EVENT        = auto()   # Un flag di trama è stato impostato
    ITEM_DELIVERED        = auto()   # Un oggetto di trama è stato consegnato
    OBJECTIVE_COMPLETED   = auto()   # Un obiettivo narrativo è stato completato
