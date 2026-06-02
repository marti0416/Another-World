# Another World

Gioco di ruolo post-apocalittico cooperativo a turni sviluppato con architettura basata su pattern e con metodologia **Scrum**, con **Python + Pygame**.
Progetto per il corso di **Ingegneria del Software per IA** — Università degli Studi di Palermo, A.A. 2025/2026.

## Descrizione

**Another World** è un RPG in locale ambientato in una città devastata dall'impatto di un meteorite alieno, che ha rilasciato un virus mutageno, trasformando gran parte della popolazione in creature violente e prive di umanità.

I due giocatori controllano **Rivet** ed **Echo**, una coppia con abilità complementari e rigidamente asimmetriche, che devono farsi strada attraverso quattro distretti pericolosi (Città, Aeroporto Militare, Zona Rurale, Zona Industriale) con l'obiettivo di rimanere uniti e sopravvivere all'apocalisse, senza perdere la propria umanità. 

Rivet è il tank e specialista degli esplosivi: elevato ATK, forza bruta per sfondare porte, limite di carico di 80 kg. Echo è la specialista tattica e tecnologica: limitata ad armi leggere o da mischia, compensa con abilità di hacking, evasione e persuasione, con un limite di carico di 50 kg.

Ad aggiungere difficoltà non sono solo gli zombie ma anche le fazioni presenti, **Razziatori**, **Dannati**, **Erranti** e **Solidali**, che mettono in seria discussione la relazione tra i 2 protagonisti.

## Funzionalità principali

- **Esplorazione** di una mappa 64×48 tile con distretti distinti e zone d'interesse.
- **Sistema di combattimento a turni** con attacchi base, abilità speciali, uso di armi e oggetti, combo letale e tentativo di fuga.
- **Sistema di fazioni** con reputazione dinamica (Solidali, Erranti, Dannati, Razziatori, Zombie) e condizioni di ostilità permanente.
- **Etica di Coppia** su scala −10/+10 che influenza dialoghi, bonus XP ed epilogo finale.
- **Sistema di crafting** per creare oggetti curativi, esplosivi e armi improvvisate e speciali.
- **Sistema di loot** con strategie specifiche per tipologia di edificio (farmacia, supermercato, laboratorio, ecc.).
- **Skill Wheel** con otto nodi per personaggio (abilità attive e passive) sbloccabili con Tech Points.
- **Sistema quest** con missioni principali e secondarie.
- **Sistema di hacking** con tre minigiochi procedurali: Pipe Puzzle, Radar Puzzle, Node Puzzle.
- **Sistema di dialoghi** ramificato con NPC di fazione, stance iniziale e callback che aggiornano reputazione ed etica.
- **Sistema di armi** completo: armi leggere, da mischia, pesanti e speciali con meccanica di inceppamento probabilistico.
- **Effetti di stato**: Corrosione, Fuoco, Confusione, Shock, Mucillagine, Evasione, Soluzione Piranha, Termite.
- **Salvataggio/caricamento** partita su file JSON con slot multipli.
- **Sistema audio** con gestione delle tracce di sottofondo e degli effetti.
- **Finali multipli** calcolati dall'intersezione tra scelta finale e valore di Etica di Coppia accumulato.
- **Cinematica introduttiva** narrativa con immagini e testo a scorrimento.

## Architettura del progetto

Il progetto adotta un'architettura **MVC (Model-View-Controller)** estesa con un **Service Layer** e un'infrastruttura di comunicazione a eventi, per garantire basso accoppiamento e alta coesione. I quattro macro-livelli sono: **Model** (entità di dominio), **View** (rendering e UI), **Controller** (input e orchestrazione), **Systems** (logica applicativa disaccoppiata tramite EventBus).
 
```
game/
├── paths.py                    # Risoluzione path asset (dev e PyInstaller)
│
├── controller/                 # CONTROLLER — input e orchestrazione
│   ├── game_manager.py         # GameManager: Singleton, loop pygame, State machine schermate,
│   │                           # ciclo save/load, registrazione ISystem tramite GameSystemBuilder
│   └── event_chain.py          # Chain of Responsibility per eventi pygame:
│                               # QuitHandler → VideoResizeHandler → MouseScaleHandler
│                               #   → SaveMenuHandler → ScreenHandler
│
├── model/                      # MODEL — entità di dominio e regole core
│   ├── stats.py                # Stats, StatusEffect (Corrosione, Fuoco, Shock, Mucillagine…)
│   ├── character_builder.py    # Builder: Character, ICharacterBuilder, RivetBuilder, EchoBuilder,
│   │                           # CharacterDirector, GameSystemBuilder, FactionAssembler
│   ├── character_decorator.py  # Decorator: ICharacterComponent, StatsComponent,
│   │                           # CharacterDecorator → CorrosioneDecorator, FuocoDecorator,
│   │                           # ShockDecorator, ConfusioneDecorator, MucillagineDecorator,
│   │                           # SoluzionePiranhaDec
│   ├── enemy.py                # Enemy + EnemyFactory (Factory Method)
│   ├── faction_factory.py      # Abstract Factory: IFactionFactory → DannatiFactory,
│   │                           # RazziatoriFactory, ErrantiFactory, ZombieFactory, SolidaliFactory
│   ├── faction_system.py       # Faction, FactionID (Enum), ReputationSystem
│   ├── ai_behaviours.py        # Strategy AI: IBattleAI, BaseFazioneAI → DannatiAI,
│   │                           # RazziatoriAI, ErrantiAI, SolidaliAI, InfettoAI,
│   │                           # CorazzatoAI, OrdaAI, MeatGiantAI
│   ├── weapon_system.py        # Strategy armi: IWeaponBehaviour, JammableWeaponBehaviour,
│   │                           # WeaponCreator / WeaponRegistry (Factory Method), Weapon
│   ├── item.py                 # Item (Prototype — ICloneable), ItemType (Enum)
│   ├── item_registry.py        # Registry globale dei prototipi Item
│   ├── loot_protocols.py       # LootContext, LootEntry, ILootStrategy (Strategy)
│   └── skill_wheel.py          # SkillNode, SkillWheel, SkillWheelIterator (Iterator)
│
├── view/                       # VIEW — rendering pygame e UI
│   ├── asset_loader.py         # Flyweight: AssetCache (Surface condivise, tile cache)
│   ├── renderer.py             # BuildingSheet, HeartHUD, rendering mappa e personaggi
│   ├── map_loader.py           # Tileset, TiledMap (caricamento mappe JSON da Tiled)
│   ├── sprite_sheet.py         # SpriteSheet, Animation (gestione sprite animati)
│   ├── ui_widgets.py           # Composite: UIComponent (ABC), Button, Panel, HealthBar,
│   │                           # SelectMenu, LogBox, Tooltip, WidgetGroup
│   ├── speech_bubble.py        # SpeechBubble, SpeechBubbleManager (bark NPC)
│   ├── effects.py              # Effect, Particle (effetti particellari a schermo)
│   ├── draw_utils.py           # Utility di disegno pygame (rettangoli, testi, bordi)
│   └── compat.py               # Compatibilità pygame / pygame-ce
│
├── screens/                    # VIEW — schermate (State pattern, 15 stati concreti)
│   ├── base_screen.py          # Screen (ABC): handle_event / update / draw
│   ├── menu_screen.py          # Menu principale
│   ├── intro_screen.py         # Cinematica introduttiva
│   ├── select_screen.py        # Selezione personaggio
│   ├── explore_screen.py       # Esplorazione mappa in tempo reale
│   ├── battle_screen.py        # Combattimento a turni
│   ├── craft_screen.py         # Crafting
│   ├── hack_screen.py          # Minigiochi hacking (Pipe, Radar, Node Puzzle)
│   ├── quest_screen.py         # Quest log
│   ├── skill_screen.py         # Skill Wheel
│   ├── worldmap_screen.py      # Mappa del mondo con marker dinamici
│   ├── pause_screen.py         # Pausa
│   ├── help_screen.py          # Schermata di aiuto
│   ├── gameover_screen.py      # Game Over (variante per personaggio abbattuto)
│   ├── victory_screen.py       # Vittoria / epilogo
│   └── factory_finale_screen.py# Finale Fabbrica Chimica (calcolo epilogo)
│
├── systems/                    # SERVICE LAYER — logica applicativa (tutti implementano ISystem)
│   ├── isystem.py              # Re-export di ISystem da game.events.isystem
│   ├── battle_system.py        # Command: IBattleCommand → AttackCommand, WeaponCommand,
│   │                           # SkillCommand, ItemCommand, FleeCommand, ComboCommand
│   ├── crafting_system.py      # Command: ICraftCommand → WeaponCraftCommand, ItemCraftCommand
│   ├── hacking_system_fixed.py # IPuzzle → PipePuzzle, RadarPuzzle, NodePuzzle + HackingSystem
│   ├── loot_system.py          # LootSystem + tutte le ILootStrategy concrete (30+ strategie)
│   ├── quest_system.py         # QuestSystem, QuestDef / Objective (Prototype), QuestState
│   ├── hud_system.py           # HUDSystem: pannelli HUD co-op, debug render
│   ├── movement_system.py      # MovementSystem: collisioni pixel-perfect, wall sliding
│   ├── party_system.py         # PartySystem: gestione gruppo, etica di coppia
│   ├── social_system.py        # CoupleEthicsSystem, PreDialogueSystem
│   ├── world_rules.py          # WorldRulesSystem: aggro, pattuglie, rianimazione zombie
│   ├── save_ui.py              # SaveMenuSystem: UI salvataggio a tre slot
│   └── misc_systems.py         # Modulo vuoto di retrocompatibilità
│
├── events/                     # INFRASTRUCTURE — comunicazione asincrona
│   ├── event_bus.py            # EventBus (Observer Pub/Sub): subscribe / unsubscribe / publish
│   ├── event_types.py          # EventType (Enum, 50+ tipi di evento)
│   └── isystem.py              # ISystem (ABC): initialize(bus) / cleanup()
│
├── audio/                      # Facade audio
│   ├── audio_manager.py        # AudioManager: astrae pygame.mixer (play_music, play_sound,
│   │                           # stop_all, fade, volume, screen audio strategy)
│   └── mix_audio.py            # Utility di mixing
│
├── dialogue/                   # Motore dialoghi
│   ├── dialogue.py             # DialogueNode, DialogueTree, DialogueManager (ISystem)
│   └── dialogue_barks.py       # Bark contestuali NPC per fazione e situazione
│
├── effects/                    # Effetti visivi di schermata
│   └── screen_effects.py       # ScreenEffects: flash, fade, camera shake
│
└── world/                      # Dati statici e generazione procedurale
    ├── world_data.py            # Costanti globali, definizioni fazioni, distretti, palette tile
    ├── city_engine.py           # CityEngine: generazione procedurale delle 12 mappe,
    │                            # IconCollider, MapData
    └── encounters.py            # Tabelle incontri e trigger spawn nemici
```

## Design Pattern adottati
 
Il progetto implementa **19 design pattern GoF**, verificabili tramite test unitari dedicati.
 
| Categoria | Pattern | Dove |
|-----------|---------|------|
| **Creazionale** | Singleton | `GameManager` (stato globale e loop pygame) |
| **Creazionale** | Builder | `ICharacterBuilder` → `RivetBuilder`, `EchoBuilder`, `GameSystemBuilder` |
| **Creazionale** | Abstract Factory | `IFactionFactory` → `DannatiFactory`, `RazziatoriFactory`, `ErrantiFactory`, `ZombieFactory`, `SolidaliFactory` |
| **Creazionale** | Factory Method | `EnemyCreator` / `EnemyFactory`, `WeaponCreator` / `WeaponRegistry`, `FactionCreator` / `FactionFactory` |
| **Creazionale** | Prototype | `ICloneable` → `Item`, `QuestDef`, `Objective` |
| **Comportamentale** | Memento | `GameMemento` + `SaveManager` (save/load a tre slot) |
| **Comportamentale** | Observer / Pub-Sub | `EventBus` + `EventType` (13 sottosistemi disaccoppiati, 50+ tipi di evento) |
| **Comportamentale** | Strategy | `ILootStrategy` (loot per zona), `IBattleAI` (AI nemica), `IWeaponBehaviour` (armi speciali) |
| **Comportamentale** | Command | `IBattleCommand` (attacco, abilità, oggetto, combo, fuga), `ICraftCommand` |
| **Comportamentale** | Iterator | `SkillWheelIterator` su `SkillWheel` |
| **Comportamentale** | Chain of Responsibility | `EventHandler` → `QuitHandler`, `VideoResizeHandler`, `SaveMenuHandler`, `ScreenHandler` |
| **Comportamentale** | State | `Screen` ABC + 15 schermate concrete gestite da `GameManager` |
| **Comportamentale** | Template Method | `ISystem` (initialize/cleanup), `BaseFazioneAI` (check_reputation_flee) |
| **Strutturale** | Flyweight | `AssetCache` (Surface condivise per tileset e sprite) |
| **Strutturale** | Facade | `AudioManager` (astrae pygame.mixer) |
| **Strutturale** | Decorator | `CharacterDecorator` → Corrosione, Fuoco, Shock, Confusione, Mucillagine, SoluzionePiranha |
| **Strutturale** | Composite | `UIComponent` → `WidgetGroup`, `Panel`, `Button`, `HealthBar`, `SelectMenu`, `LogBox`, `Tooltip` |

## Tecnologie utilizzate

| Tecnologia / Strumento | Versione | Uso |
|---|---|---|
| Python | 3.12+ | Linguaggio principale; type hints, dataclasses |
| pygame-ce | 2.x | Rendering 2D, gestione eventi, audio, sprite |
| Jira Software | — | Gestione backlog Scrum, sprint planning, tracking user stories |
| Git / GitHub | — | Controllo versione, branching per feature isolate |
| Tiled / JSON | — | Editor mappe tile-based, esportazione in JSON |
| LPC Assets | — | Sprite sheet per personaggi e nemici animati |
| Visual Studio Code | — | IDE principale |

## Installazione e avvio

### Setup

```bash
# Clona il repository
git clone <url-repo>
cd Another-World
 
# (Opzionale) Crea un ambiente virtuale
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
 
# Installa le dipendenze
pip install pygame-ce
```
 
### Avvio
 
```bash
python main.py
```

## Team di sviluppo

Progetto sviluppato dal **Gruppo 12** seguendo la metodologia **Scrum** con 15 sprint su circa 30 settimane (Novembre 2025 — Maggio 2026).
 
| Membro | Area principale |
|--------|----------------|
| **Alessia** | Sistema di combattimento a turni, Battle Renderer |
| **Massimo** | Sistema armi (Strategy), layer sociale, dialoghi Razziatori/Dannati, loot system, crafting |
| **Martina** | Sistema fazioni, reputazione, regole di mondo, AI nemici, meccaniche di esplorazione |

## Struttura Scrum

Il progetto è stato organizzato tramite **Scrum** su board Jira, con **170 user stories** distribuite in **13 Epiche** e completate al 100%.
 
| Epic ID | Titolo |
|---------|--------|
| SCRUM-300 | Core Gameplay & Navigation |
| SCRUM-301 | Combat System |
| SCRUM-302 | Character Progression & Skills |
| SCRUM-303 | Crafting System |
| SCRUM-304 | Hacking System |
| SCRUM-305 | Faction & Reputation System |
| SCRUM-306 | Quest System |
| SCRUM-307 | Dialogue & Social Interaction |
| SCRUM-308 | World, Audio & Visual |
| SCRUM-309 | Save / Load System |
| SCRUM-310 | Inventory & Item Management |
| SCRUM-311 | Narrative & Screen Flow |
| SCRUM-312 | XP, Levelling & Progression Rewards |

## File di salvataggio

La partita viene salvata in `savegame.json` nella directory di avvio. Sono supportati tre slot di salvataggio. Il salvataggio serializza l'intero stato del gioco: statistiche e inventari dei personaggi, coordinate sulla mappa, stato di porte e ostacoli, reputazione delle cinque fazioni, etica di coppia, flag di dialogo e progressione delle quest.
