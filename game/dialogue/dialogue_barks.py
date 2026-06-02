import random


EXPLORE_BARKS = {
    "ethics_up": [
        "Rivet: 'Siamo una squadra perfetta. Te l'ho mai detto?'",
        "Echo: 'Sincronizzazione di coppia ottimale. Bel lavoro, amore.'",
        "Rivet: 'Non ce la farei mai ad uscirne vivo senza di te, Echo.'",
        "Echo: 'I miei parametri indicano un picco di affinità. Continuiamo così.'",
    ],
    "ethics_down": [
        "Rivet: 'Ma a cosa diavolo stavi pensando?!'",
        "Echo: 'Avviso: divergenza comportamentale rilevata. Stiamo perdendo la sintonia.'",
        "Rivet: 'Se continuiamo a litigare in questo modo, ci faranno fuori.'",
        "Echo: 'Calcolo delle probabilità di rottura... in aumento. Concentriamoci, Rivet.'",
        "Rivet: 'Per favore, Echo... cerca di non farmi saltare i nervi oggi.'",
    ],
    "rep_allied": [
        "Rivet: 'Bene. Sembra che i {faction} ora ci coprano le spalle.'",
        "Echo: 'Stato di alleanza con i {faction} confermato.'",
    ],
    "rep_hostile": [
        "Rivet: 'Merda... i {faction} ci hanno messo una taglia sulla testa.'",
        "Echo: 'Attenzione: i membri della fazione {faction} ora sono ostili a vista.'",
    ],
    "safe_needs_echo": [
        "Rivet: 'È blindata elettronicamente. Echo, mi serve la tua magia.'",
    ],
    "safe_needs_rivet": [
        "Echo: 'I circuiti sono fritti. Rivet, devi usare la forza bruta per scardinarla.'",
    ],
    "safe_empty": [
        "{char}: 'Vuota. Qualcuno è arrivato prima di noi.'",
    ],
    "safe_success": [
        "Rivet: 'Jackpot. Vediamo cosa c'è qui dentro.'",
        "Rivet: 'Serratura saltata. Il bottino è nostro.'",
        "Rivet: 'Ecco fatto. Vediamo se ne è valsa la pena.'",
    ],

    "system_locked": [
        "Echo: 'Il terminale è bloccato ora. Dobbiamo aspettare'",
    ],

    "nothing_here": [
        "{char}: 'Solo spazzatura. Niente di utile.'",
        "{char}: 'Qui non c'è niente, andiamo avanti.'",
    ],
    "loot_corpses": [
        "Echo: 'Vediamo se questi disgraziati avevano qualcosa di utile.'",
        "Rivet: 'Frughiamo i cadaveri. A loro non serve più niente.'",
    ],

    "weapon_error": [
        "Rivet: 'Maledizione, quest'arma è un blocco di ruggine. Inutile.'",
        "Echo: 'Meccanismo di sparo compromesso. Impossibile recuperarla.'",
    ],

    "acid_damage": [
        "Rivet: 'Argh! L'acido mi sta corrodendo gli stivali!'",
        "Echo: 'Attenzione. Rilevati agenti chimici altamente corrosivi sotto i nostri piedi.'",
        "Rivet: 'Merda, brucia! Dobbiamo uscire da questa poltiglia!'",
    ],

    "coop_too_far": [
        "Rivet: 'Ehi Echo, dove diavolo sei finita? Restiamo uniti!'",
        "Echo: 'Rivet, sei fuori dal mio raggio visivo. Riavvicinati.'",
        "Rivet: 'Non dividiamoci, è un suicidio! Torna qui!'",
    ],

    "new_location": [
        "Rivet: 'Siamo arrivati. Occhi aperti.'",
        "Echo: 'Analisi topografica confermata. Siamo giunti a destinazione.'",
        "Rivet: 'Che posto inquietante. Teniamo le armi pronte.'",
    ],

    "low_hp_rivet": [
        "Rivet: 'Echo... sto perdendo troppo sangue. Mi serve un medikit, in fretta.'",
        "Rivet: '*Tosse* Non so quanto ancora potrò reggere in questo stato...'",
    ],
    "low_hp_echo": [
        "Echo: 'Avviso critico: integrità strutturale compromessa. Richiesta riparazione immediata.'",
        "Echo: 'Sistemi in avaria. Rischio di spegnimento alto.'",
    ],

    "raining": [
        "Rivet: 'Odio questa pioggia. Mi arrugginisce l'equipaggiamento.'",
        "Echo: 'Precipitazioni rilevate. Visibilità ridotta. Procediamo con cautela.'",
        "Rivet: 'Giornata perfetta per farsi sbranare, eh?'",
    ],

    "skill_unlocked": [
        "Rivet: 'Mi sento in forma. Credo di aver capito come muovermi meglio in combattimento.'",
        "Echo: 'Analisi dei dati in background completata. Nuove routine tattiche disponibili.'",
        "Rivet: 'Forse ho trovato un nuovo modo per usare questo equipaggiamento.'",
    ],

    "open_map": [
        "Echo: 'Avvio interfaccia topografica. Controlliamo la rotta.'",
        "Rivet: 'Vediamo dove diavolo siamo finiti...'",
    ],
    "map_locked_no_rael": [
        "Rivet: 'Non ho idea di dove siamo. Dobbiamo trovare qualcuno che conosca queste strade.'",
        "Echo: 'Nessuna cartografia disponibile. Trovate prima una fonte locale.'",
        "Rivet: 'La mappa non mi dice niente in questo caos. Serve qualcuno del posto.'",
    ],
    "map_locked_rael": [
        "Rivet: 'Ancora non posso usarla — prima consegniamo il fucile a Rael.'",
        "Echo: 'La mappa è inutile senza le chiavi di Rael. Prima teniamo fede al patto.'",
        "Rivet: 'Aspetta, il fucile. Dobbiamo portarlo a Rael prima di muoverci.'",
    ],
    "map_unlocked": [
        "Echo: 'Interfaccia topografica sbloccata. Mappa disponibile con tasto M.'",
        "Rivet: 'Finalmente — ora sappiamo dove andiamo. Tasto M per la mappa.'",
    ],
    "open_crafting": [
        "Rivet: 'Fammi vedere cosa riesco ad assemblare con questa roba.'",
        "Echo: 'Avvio protocolli di sintesi materiali. Vediamo cosa possiamo creare.'",
    ],
    "open_quests": [
        "Rivet: 'Facciamo il punto della situazione. Qual è il prossimo obiettivo?'",
        "Echo: 'Revisione dei parametri di missione in corso.'",
    ],

    "idle_waiting": [
        "Rivet: 'Allora? Piantiamo le tende qui o ci muoviamo?'",
        "Echo: 'L'inattività prolungata in campo aperto aumenta le probabilità di rilevamento ostile.'",
        "Rivet: 'Odio restare fermo. Mi fa salire il nervosismo.'",
        "Echo: 'Sistemi in attesa di input... Tutto tranquillo, per ora.'",
    ],

    "no_save": [
        "Echo: 'I banchi di memoria sono vuoti. Nessun punto di ripristino trovato.'",
    ],
    "ambush": [
        "Rivet: 'Attenzione! Ci saltano addosso!'",
        "Echo: 'Contatto ostile imminente. Prepariamoci.'",
    ],
    "trapped_in_explosion": [
        "Echo: 'Allarme critico! Cedimento strutturale! Siamo in trap—'",
        "Rivet: 'Merda, non ce l'abbiamo fatta a uscir—'",
    ],

    "found_loot_stash": [
    "Rivet: 'Ehi, diamo un'occhiata qui...'",
    "Echo: 'Rilevo materiali utili in questa zona.'",
    ],

    "no_terminal_nearby": [
    "Echo: 'Non vedo interfacce a cui collegarmi qui intorno.'",
    ],

    "auto_door_open": [
    "Echo: 'Comando di override accettato. La via è libera.'",
    "Rivet: 'Ottimo lavoro, Echo. Si è aperta.'",
    ],

    "quest_mine_place": [
        "Rivet: 'Mina piazzata sul portello. Indietro, esploderà a breve!'",
    ],
    "quest_panel_echo": [
        "Echo: 'Sistemi riavviati con successo. La Centrale è di nuovo online.'",
    ],
    "quest_panel_rivet": [
        "Rivet: 'Troppi cavi. Meglio che ci metta le mani Echo prima che io frigga tutto.'",
    ],
    "quest_door_factory": [
        "Rivet: 'SCHIANTO! Via libera. Ehi... sentite anche voi questa puzza chimica?'",
    ],

    "terminal_no_power": [
        "Echo: 'Nessun segnale. Manca l'alimentazione principale dalla Centrale.'",
    ],
    "terminal_already_hacked": [
        "Echo: 'Ci sono già entrata. Nessun nuovo dato da estrarre.'",
    ],
    "terminal_need_door": [
        "Echo: 'Non ho linea di vista. Rivet, devi sfondare la porta interna prima.'",
    ],
    "terminal_need_clear": [
        "Echo: 'Impossibile concentrarsi con quegli infetti in giro. Puliamo l'area.'",
    ],

    "inv_empty": [
        "{char}: 'Il mio zaino è completamente vuoto.'",
        "{char}: 'Non ho letteralmente niente da buttare.'",
    ],
    "no_consumables": [
        "Echo: 'Scorte mediche e consumabili esauriti.'",
        "Rivet: 'Non abbiamo più roba utile negli zaini.'",
    ],
    "keep_for_combat": [
        "{char}: 'Non sprechiamolo ora. Questo fa danni, ci servirà in battaglia.'",
    ],
    "use_material": [
        "Echo: 'Questo è un componente grezzo. Dobbiamo lavorarlo (Crafting).'",
    ],

    "mine_defuse_fail": [
        "Rivet: 'CAZZO! L'innesco era instabile! Copertura!'",
    ],
    "explosion_shockwave": [
        "{char}: 'Aargh! Attenti all'onda d'urto!'",
        "{char}: 'Merda, l'esplosione ci ha investiti!'",
    ],
    "explosion_door_open": [
        "Rivet: 'Botto perfetto. Il varco è aperto, andiamo!'",
    ],

    "quest_mine_hint": [
        "Rivet: 'Ci vuole roba pesante per quel portello. Forse all'Aeroporto Militare troviamo una carica.'",
    ],
    "terminal_dead": [
        "Echo: 'Terminale morto. Hardware completamente fritto, non posso farci nulla.'",
    ],

    "loot_enemies_post_battle": [
        "Rivet: 'Vediamo cos'è rimasto nelle tasche di questi stronzi.'",
        "Echo: 'Avvio scansione dei cadaveri per recupero risorse.'",
    ],

    "loot_weapon_rivet": [
        "Rivet: 'Un'arma. Speriamo non si inceppi.'",
        "Rivet: 'Guarda qui, Echo. Questo fa al caso nostro.'",
    ],
    "loot_weapon_echo": [
        "Echo: 'Specifiche interessanti. La prendo io.'",
        "Echo: 'Armamento recuperato. Meglio non farsi trovare disarmati.'",
    ],
    "loot_generic_rivet": [
        "Rivet: 'Trovato qualcosa di utile.'",
        "Rivet: 'Metto nello zaino, potrebbe servire.'",
    ],
    "loot_generic_echo": [
        "Echo: 'Risorse acquisite. Le aggiungo all'inventario.'",
        "Echo: 'Non è molto, ma non possiamo fare gli schizzinosi.'",
    ],
    "inv_full_rivet": [
        "Rivet: 'Zaino pieno. Non riesco a farci stare altro.'",
        "Rivet: 'Echo, sono al limite. O butto qualcosa o la lasciamo qui.'",
    ],
    "inv_full_echo": [
        "Echo: 'Capacità di carico superata. Devo riorganizzare l'equipaggiamento.'",
        "Echo: 'Negativo, non ho più spazio.'",
    ],
    "drop_item": [
        "{char}: 'Lascio questo a terra. Troppo peso inutile.'",
        "{char}: 'Non ci serve adesso. Lo mollo qui.'",
    ],

    "door_success": [
        "Rivet: 'Fatti indietro, Echo. CRACK! Fatto.'",
        "Rivet: 'La diplomazia non funzionava. I muscoli sì.'",
    ],
    "door_fail": [
        "Rivet: 'Maledizione. È troppo robusta anche per me.'",
        "Rivet: 'Niente da fare, non cede. Serve un altro modo.'",
    ],
    "door_needs_echo": [
        "Rivet: 'Serratura elettronica. Echo, tocca a te.'",
        "Rivet: 'Non c'è niente da sfondare qui, ci vuole un hacker.'",
    ],

    "terminal_rivet_fail": [
        "Rivet: 'Io e i computer non andiamo d'accordo. Pensaci tu.'",
        "Rivet: 'Che diavolo di tasti devo premere? Echo, aiuto.'",
    ],

    "mine_success": [
        "Rivet: 'Fatto. Disinnescata. Ho sudato freddo.'",
        "Rivet: 'Presa. Trattala con cura, Echo, o saltiamo in aria.'",
    ],
    "mine_fail": [
        "Rivet: 'CAZZO! Copriti!'",
    ],
    "mine_stepped": [
        "{char}: 'MERDA! Sotto il mio piede... KABOOM!'",
    ],

    "use_heal": [
        "{user}: 'Tieni, usa questo. Ti rimetterà in sesto.' ({target}: +{healed} HP)",
        "{user}: 'Non morire adesso. Cura in corso.' ({target}: +{healed} HP)",
    ],
    "heal_full": [
        "{char}: 'Siamo già al massimo delle forze. Non sprechiamolo.'",
    ],
}


ENEMY_BARKS = {
    "razziatori": {
        "attack": ["'Svuotate le tasche!'", "'Prendiamo tutto!'", "'Carne morta!'"],
        "flee": ["'Ritirata! Ci stanno massacrando!'", "'Non vale la pena morire per questo!'"],
        "summon": ["'A me! Circondateli!'", "'Rinforzi, muovetevi!'"],
    },
    "solidali": {
        "attack": ["'Fuoco di soppressione!'", "'Bersaglio acquisito!'", "'Per l'ordine!'"],
        "flee": ["'Ripiegamento tattico!'", "'Riorganizzarsi alla base!'"],
        "summon": ["'Squadra, convergere sulla mia posizione!'", "'Richiedo supporto!'"],
    },
    "dannati": {
        "attack": ["'Sangue per la terra!'", "'Purificatevi nel dolore!'", "'Siete già morti!'"],
        "flee": ["'La terra attenderà...'", "'Le ombre mi chiamano.'"],
        "summon": ["'Sorgete, fratelli!'", "'Il culto non muore!'"],
    },
    "erranti": {
        "attack": ["'Siamo disperati quanto voi!'", "'Lasciateci le vostre scorte!'"],
        "flee": ["'Scappiamo! Non voglio morire qui!'"],
        "summon": ["'Aiutatemi! Sono in troppi!'"],
    },
    "zombie": {
        "attack": ["*Rantolo gutturale*", "*Grugnito affamato*", "*Stridio agghiacciante*"],
        "flee": ["*Striscia via nell'oscurità*"],
        "summon": ["*Un urlo lacerante richiama l'orda!*"],
    }
}


BATTLE_PLAYER_BARKS = {
    "flee_success": [
        "Echo: 'Via, via, via! Sganciamoci!'",
        "Rivet: 'Ritirata strategica! Muoversi!'",
    ],
    "flee_fail": [
        "Rivet: 'Ci bloccano la strada! Dobbiamo combattere!'",
        "Echo: 'Vie di fuga tagliate. Prepararsi all'impatto.'",
    ],
    "no_ammo": [
        "{char}: 'Arma scarica! Devo passare al corpo a corpo!'",
    ],
    "combo_ready": [
        "Echo: 'Rivet, manovra combinata pronta. Andiamo!'",
    ],

    "attack_melee_rivet":  ["Rivet: 'Assaggia questo!'", "Rivet: 'Fatti sotto!'"],
    "attack_melee_echo":   ["Echo: 'Ingaggio ravvicinato.'", "Echo: 'Calcolo punto debole.'"],
    "attack_weapon_rivet": ["Rivet: 'Mangia piombo!'", "Rivet: 'Fuoco di copertura!'"],
    "attack_weapon_echo":  ["Echo: 'Arma pronta, faccio fuoco.'", "Echo: 'Traiettoria confermata.'"],
    "use_skill_rivet":     ["Rivet: 'Beccati questo trucchetto!'", "Rivet: 'Ora facciamo sul serio!'"],
    "use_skill_echo":      ["Echo: 'Esecuzione protocollo offensivo.'", "Echo: 'Attivazione sistemi tattici.'"],
    "use_item_rivet":      ["Rivet: 'Tiriamo un po' il fiato!'", "Rivet: 'Mi rimetto in sesto!'"],
    "use_item_echo":       ["Echo: 'Iniezione gel medico.'", "Echo: 'Ripristino integrità strutturale.'"],
    "combo_exec":          ["Rivet: 'Ora, Echo! Insieme!'", "Echo: 'Sincronizzazione perfetta. Colpiamo!'"],

    "combo_fail": [
        "Rivet: 'Non siamo coordinati! Devo riprendere fiato!'",
        "Echo: 'Sincronizzazione negata. Cooldown attivo.'",
        "Rivet: 'Non ora Echo, non ce la faccio!'",
    ],
    "item_empty": [
        "Rivet: 'Zaini vuoti! Niente cure, siamo a secco!'",
        "Echo: 'Avviso: scorte di consumabili terminate.'",
    ],
    "skill_fail_rivet": [
        "Rivet: 'Maledizione, ho mancato il bersaglio!'",
        "Rivet: 'Un colpo a vuoto! Cazzo!'"
    ],
    "skill_fail_echo": [
        "Echo: 'Errore di calcolo. Traiettoria inefficace.'",
        "Echo: 'Anomalia nell'esecuzione. Skill fallita.'"
    ],

    "take_damage_rivet": [
        "Rivet: 'Argh! Me la paghi!'",
        "Rivet: 'È tutto qui quello che sai fare?!'",
        "Rivet: '*Grugnito di dolore*'",
    ],
    "take_damage_echo": [
        "Echo: 'Danni strutturali rilevati. Scudi compromessi.'",
        "Echo: 'Sistemi di puntamento disturbati dall'impatto.'",
    ],
    "status_effect_hit": [
        "Rivet: 'Che schifo! Mi ha infettato!'",
        "Echo: 'Attenzione: parametri vitali alterati da agenti esterni.'",
    ],

    "battle_won_rivet": [
        "Rivet: 'Anche questa è fatta. Bel lavoro.'",
        "Rivet: 'Nessuno si mette sulla nostra strada.'",
    ],
    "battle_won_echo": [
        "Echo: 'Minaccia neutralizzata. Ritorno in modalità esplorazione.'",
        "Echo: 'Area sicura. Le probabilità di sopravvivenza sono in aumento.'",
    ],

    "evade_success_rivet": [
        "Rivet: 'Troppo lento!'",
        "Rivet: 'Mancato! Fai attenzione la prossima volta.'",
    ],
    "evade_success_echo": [
        "Echo: 'Traiettoria ostile calcolata ed evitata.'",
        "Echo: 'Schivata perfetta.'",
    ],
    "zero_damage_rivet": [
        "Rivet: 'Ha! Non ho sentito niente!'",
        "Rivet: 'La mia armatura regge bene.'",
    ],
    "zero_damage_echo": [
        "Echo: 'Impatto assorbito. Danni strutturali nulli.'",
        "Echo: 'Offensiva inefficace contro la mia corazza.'",
    ],
    "weapon_jam_rivet": [
        "Rivet: 'Maledizione, si è inceppata! *Click*'",
    ],
    "weapon_jam_echo": [
        "Echo: 'Errore: meccanismo di sparo bloccato.'",
    ],
}

HACK_BARKS = {
    "success": [
        "Echo: 'Bypass completato. Sono dentro.'",
        "Echo: 'Firewall disattivato. Troppo facile.'",
    ],
    "fail": [
        "Echo: 'Merda, ci hanno respinti. Riprovo.'",
        "Echo: 'Codice errato. Il sistema sta reagendo.'",
    ],
    "hack_story_safe": [
        "Echo: 'Sistema bucato. Il firewall ha ceduto — Rivet, la cassaforte è tua.'",
    ],
    "hack_story_radar": [
        "Echo: 'Torre Radar riallineata. Sto ricevendo letture termiche anomale... I Giganti di Carne sono sulla mappa.'",
    ],
    "system_locked": [
        "Echo: 'Accesso negato definitivamente. Terminale bloccato.'",
    ]
}

def get_bark(category: dict, key: str, **kwargs) -> str:
    """Restituisce una battuta casuale formattata dal dizionario."""
    lines = category.get(key, ["..."])
    chosen = random.choice(lines)
    if kwargs:
        return chosen.format(**kwargs)
    return chosen