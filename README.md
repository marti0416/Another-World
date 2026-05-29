# 🧟 Another World

> Gioco di ruolo post-apocalittico a turni sviluppato con metodologia **Scrum** nell'ambito del corso di Ingegneria del Software.

---

## 📖 Descrizione

**Survivors of the Impact** è un RPG testuale/grafico sviluppato con **Python + Pygame** ambientato in una città devastata dall'impatto di un meteorite alieno. Il meteorite ha rilasciato un virus mutageno che ha trasformato gran parte della popolazione in creature violente e prive di umanità.

Il giocatore controlla una coppia di fidanzati — **Lui** e **Lei** — con abilità complementari, che devono farsi strada attraverso quattro distretti pericolosi (Città, Aeroporto Militare, Zona Rurale, Fabbrica Chimica) con l'obiettivo di trovare una cura e sopravvivere all'apocalisse, senza perdere la propria umanità.

### 🌍 Lore in breve

| Atto | Evento |
|------|--------|
| I – L'Origine del Male | Un asteroide alieno è in rotta di collisione con la Terra |
| II – L'Infezione | Il meteorite si schianta e rilascia una mucillagine mutagena |
| III – Un Mondo a Pezzi | Le fazioni umane sopravvissute si scontrano per le risorse |
| IV – Destinazione Salvezza | I protagonisti cercano di combattere l'infezione e restare umani |

---

## 🎮 Funzionalità principali

- **Esplorazione** di una mappa 64×48 tile con distretti distinti e zone d'interesse
- **Sistema di combattimento a turni** con AP, comandi di attacco, abilità speciali e armi
- **Sistema di fazioni** con reputazione dinamica (Solidali, Erranti, Dannati, Razziatori, Zombie)
- **Sistema di crafting** per creare oggetti curativi, esplosivi e armi
- **Sistema di loot** con strategie specifiche per tipologia di edificio (farmacia, supermercato, laboratorio, ecc.)
- **Sistema quest** con missioni principali e secondarie
- **Sistema di hacking** con puzzle procedurali (Pipe Puzzle)
- **Sistema di dialoghi** con NPC di fazione e bark situazionali
- **Sistema di armi** completo: armi da fuoco, esplosivi, armi da mischia, armi speciali
- **Salvataggio/caricamento** partita su file JSON con slot multipli
- **Sistema audio** con gestione delle tracce di sottofondo e degli effetti
- **Cinematica introduttiva** narrativa con immagini e testo a scorrimento

---

## 🏗️ Architettura del progetto

Il progetto segue un'architettura **MVC (Model-View-Controller)** e fa uso di numerosi **design pattern GoF**:

```
game/
├── controller/         # Logica di controllo centrale
│   └── game_manager.py # GameManager (Singleton, Memento, State Machine)
├── model/              # Entità di dominio
│   ├── stats.py        # Statistiche e status effect
│   ├── enemy.py        # Nemici e EnemyFactory (Factory Method)
│   ├── weapon_system.py# Armi speciali (Strategy Pattern)
│   ├── faction_system.py# Gestione fazioni e reputazione (Observer)
│   ├── item.py / item_registry.py
│   ├── character_builder.py # Builder per i personaggi
│   ├── ai_behaviours.py     # Comportamenti AI nemici
│   └── skill_wheel.py       # Albero delle abilità
├── view/               # Rendering e UI
│   ├── renderer.py
│   ├── asset_loader.py
│   ├── map_loader.py
│   ├── sprite_sheet.py
│   ├── draw_utils.py
│   ├── ui_widgets.py
│   ├── speech_bubble.py
│   └── effects.py
├── screens/            # Schermate di gioco (State pattern)
│   ├── explore_screen.py    # Mappa di esplorazione
│   ├── battle_screen.py     # Combattimento a turni
│   ├── craft_screen.py      # Crafting
│   ├── hack_screen.py       # Mini-gioco hacking
│   ├── quest_screen.py      # Gestione missioni
│   ├── skill_screen.py      # Albero abilità
│   ├── worldmap_screen.py   # Mappa del mondo
│   ├── intro_screen.py      # Schermata introduttiva
│   ├── menu_screen.py       # Menu principale
│   ├── gameover_screen.py
│   └── victory_screen.py
├── systems/            # Sistemi di gioco (logica applicativa)
│   ├── battle_system.py     # Comandi battaglia (Command Pattern)
│   ├── crafting_system.py
│   ├── loot_system.py       # Loot per edificio (Strategy Pattern)
│   ├── hacking_system.py    # Puzzle hacking
│   ├── quest_system.py
│   ├── faction_system.py
│   ├── hud_system.py
│   ├── movement_system.py
│   ├── social_system.py
│   ├── world_rules.py       # Regole di mappa, aggro, pattuglie
│   └── *_dialogues.py       # Dialoghi per fazione
├── events/             # Sistema eventi pub/sub
│   ├── event_bus.py    # EventBus (Observer/Mediator)
│   └── event_types.py  # Enum di tutti gli EventType
├── audio/              # Gestione audio
│   └── audio_manager.py
├── dialogue/           # Motore dialoghi
│   ├── dialogue.py
│   └── dialogue_barks.py
├── effects/            # Effetti schermata
│   └── screen_effects.py
└── world/              # Dati statici e generazione mondo
    ├── world_data.py   # Costanti, fazioni, distretti, palette
    └── city_engine.py  # Generazione procedurale della città
```

### Design Pattern adottati

| Pattern | Dove |
|---------|------|
| **Singleton** | `GameManager` (controller centrale) |
| **Memento** | `GameMemento` + `SaveManager` (save/load partita) |
| **Observer / EventBus** | `EventBus` + `EventType` (comunicazione tra sistemi) |
| **Command** | `IBattleCommand`, `AttackCommand`, `WeaponCommand`, `SkillCommand` |
| **Strategy** | `IWeaponBehaviour` (armi speciali), `ILootStrategy` (loot per zona) |
| **Factory Method** | `EnemyFactory` (creazione nemici), factory dialoghi |
| **Builder** | `character_builder.py` (costruzione personaggi) |
| **State** | Gestione schermate in `GameManager` (state machine) |

---

## 🛠️ Tecnologie utilizzate

| Tecnologia | Versione consigliata | Uso |
|---|---|---|
| Python | 3.12+ | Linguaggio principale |
| Pygame | 2.x | Rendering, input, audio |
| json (stdlib) | — | Salvataggio partita |

---

## ⚙️ Installazione e avvio

### Prerequisiti

- Python 3.12 o superiore
- pip

### Setup

```bash
# Clona il repository
git clone <url-repo>
cd game

# (Opzionale) Crea un ambiente virtuale
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Installa le dipendenze
pip install pygame
```

### Avvio

```bash
python main.py
```

---

## 👥 Team di sviluppo

Il progetto è stato sviluppato da un team seguendo la metodologia **Scrum**, con sprint, backlog e task identificati dai codici `SCRUM-XXX` presenti nel codice sorgente.

| Membro | Area principale |
|--------|----------------|
| **Martina** | Sistema fazioni, reputazione, regole di mondo, AI nemici, enemy model |
| **Massimo** | Sistema armi (Strategy), HUD, dialoghi razziatori/dannati, loot system, crafting |
| Team | Schermata esplorazione, combattimento, dialoghi, quest, audio, UI |

---

## 🔖 Struttura Scrum

Il progetto è stato organizzato tramite **Scrum**, con:

- **Product Backlog**: lista prioritizzata di user story (es. sistema reputazione, crafting, armi speciali, hacking, ecc.)
- **Sprint Planning**: i task sono tracciati con identificatori `SCRUM-XXX` direttamente nei commenti del codice
- **Sprint Review e Retrospective**: cicli iterativi di refactoring (documentati come *Refactoring Fase 1–5* nei commenti)
- **Daily Scrum**: coordinazione su feature e integrazioni tra sistemi

Esempi di task tracciati nel codice:

```
SCRUM-121/122 — Sistema reputazione fazioni
SCRUM-127     — Missili incendiari con puntatore laser
SCRUM-175     — Rail Gun (spara attraverso ostacoli)
SCRUM-183     — Inceppamento armi recuperate
SCRUM-204/255 — Sfondamento porte
SCRUM-252     — Randomizzazione occupanti edifici
```

---

## 📁 File di salvataggio

La partita viene salvata automaticamente in `savegame.json` nella directory di avvio. Sono supportati più slot di salvataggio.

---

## 📄 Licenza

Progetto accademico — Corso di Ingegneria del Software.