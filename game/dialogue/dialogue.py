from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from game.events.event_bus import EventBus
from game.events.event_types import EventType
from game.events.isystem import ISystem



@dataclass
class DialogueNode:
    """
    Nodo di un albero di dialogo.
    UML: entità di dominio per la gestione delle conversazioni ramificate.

    effects possibili:
      {'ethics': int, 'reputation': {faction_id: int},
       'trade': bool, 'end': bool, 'heal_player': bool,
       'start_combat': bool, 'flee_attempt': bool, 'cost': {item_id: qty}}
    """
    node_id:  str
    speaker:  str
    text:     str
    choices:  list[tuple]
    effects:  dict = field(default_factory=dict)

    @staticmethod
    def from_string(node_id: str, speaker: str, text: str,
                    choices_text: list[str],
                    next_ids: list[str] | None = None,
                    effects: dict | None = None) -> "DialogueNode":
        """
        Factory per dialoghi semplici basati su stringhe .
        Crea un DialogueNode senza dover costruire tuple manualmente.

        Esempio:
            node = DialogueNode.from_string(
                "root", "Marco", "Ciao viaggiatore!",
                choices_text=["Saluta", "Ignora"],
                next_ids=["greet", "ignore"]
            )
        """
        ids = next_ids or [f"{node_id}_opt{i}" for i in range(len(choices_text))]
        choices = list(zip(choices_text, ids))
        return DialogueNode(
            node_id=node_id,
            speaker=speaker,
            text=text,
            choices=choices,
            effects=effects or {},
        )



class DialogueTree:
    """
    Struttura ad albero navigabile per scelta del giocatore.
    Mantiene lo stato della conversazione corrente (nodo attivo).
    """

    def __init__(self, npc_name: str) -> None:
        self.npc_name = npc_name
        self._nodes: dict[str, DialogueNode] = {}
        self._current_id: str | None = None

    def add_node(self, node: DialogueNode) -> None:
        self._nodes[node.node_id] = node

    def start(self, root_id: str = "root") -> DialogueNode | None:
        """Avvia il dialogo dal nodo radice indicato."""
        self._current_id = root_id
        return self._nodes.get(root_id)

    def choose(self, choice_index: int) -> tuple[DialogueNode | None, dict]:
        """
        Naviga al nodo corrispondente alla scelta.
        Restituisce (nodo_successivo, effetti_combinati).
        """
        current = self._nodes.get(self._current_id)
        if current is None or choice_index >= len(current.choices):
            return None, {}

        choice_tuple = current.choices[choice_index]
        next_id = choice_tuple[1]

        choice_effects = choice_tuple[2] if len(choice_tuple) > 2 else {}

        next_node = self._nodes.get(next_id)

        effects = choice_effects.copy()
        if next_node:
            for k, v in next_node.effects.items():
                if isinstance(v, dict) and k in effects and isinstance(effects[k], dict):
                    effects[k].update(v)
                else:
                    effects[k] = v

        self._current_id = next_id
        return next_node, effects

    @property
    def current_node(self) -> DialogueNode | None:
        return self._nodes.get(self._current_id)

    def is_ended(self) -> bool:
        node = self.current_node
        return node is None or node.effects.get("end", False)

    @classmethod
    def from_lines(cls, npc_name: str,
                   lines: list[tuple[str, str, list[str]]]) -> "DialogueTree":
        """
        Factory per dialoghi lineari semplici .
        Ogni elemento è (speaker, text, [scelte_testo]).
        I nodi vengono collegati in sequenza automaticamente.

        Esempio:
            tree = DialogueTree.from_lines("NPC", [
                ("NPC",    "Ciao!", ["Ciao anche a te", "Vai via"]),
                ("Player", "Come stai?", ["Bene", "Male"]),
            ])
        """
        tree = cls(npc_name=npc_name)
        for i, (speaker, text, choices_text) in enumerate(lines):
            node_id = f"node_{i}"
            next_ids = [f"node_{i + 1}"] * len(choices_text)
            if i == len(lines) - 1:
                next_ids = [f"end_{j}" for j in range(len(choices_text))]
            node = DialogueNode.from_string(
                node_id, speaker, text, choices_text, next_ids
            )
            tree.add_node(node)
        tree.add_node(DialogueNode(
            node_id=f"end_0", speaker="", text="", choices=[],
            effects={"end": True}
        ))
        if not tree._nodes.get("root"):
            first = tree._nodes.get("node_0")
            if first:
                tree._nodes["root"] = first
        return tree

class DannatiDialogues:

    @staticmethod
    def build_tomas() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Tomas")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        munizioni_possedute = count_item("ammo_01")
        esplosivi_posseduti = count_item("battle_explosive")

        ha_i_requisiti = munizioni_possedute >= 30 and esplosivi_posseduti >= 1

        q_prag  = gs.flags.get("tomas_prag_quest_active", False)
        q_diplo = gs.flags.get("tomas_diplo_quest_active", False)
        q_aggro = gs.flags.get("tomas_aggro_quest_active", False)
        q_emp   = gs.flags.get("tomas_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("tomas_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Tomas",
                    text="Mi hai pagato, ma non mi piaci. Continua a camminare e non farti più vedere da queste parti.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "L'affare era di 30 munizioni e un esplosivo per scordarmi della vostra faccia. Li avete?"
            elif q_diplo:
                greeting = "La nostra 'tregua' ha un costo. Avete portato le 30 munizioni e l'esplosivo che mi servono?"
            elif q_aggro:
                greeting = "[Stringe l'arma] Hai ancora tutti i denti, vedo. Sputa quelle 30 munizioni e l'esplosivo, prima che perda la pazienza."
            elif q_emp:
                greeting = "[Ghigna] Ehi, 'amico'. Hai trovato quelle armi o facevi solo finta di preoccuparti per me?"
            else:
                greeting = "30 munizioni e un esplosivo da combattimento per la vostra vita. Consegnate."

            if ha_i_requisiti:
                scelte_ritorno = [("«Ecco le 30 munizioni e l'esplosivo. Ora siamo pari.»", "tomas_standby_pay")]
            else:
                scelte_ritorno = [("«Non abbiamo ancora l'arsenale. Ti chiediamo tempo.»", "tomas_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Tomas", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="tomas_standby_wait", speaker="Tomas",
                text="Il tempo è scaduto da un pezzo in questo posto. Spostati, o ti faccio un buco nello stomaco.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="tomas_standby_pay", speaker="Tomas",
                text="[Carica il caricatore e intasca l'esplosivo] Buona roba. Potete andare. Per ora.",
                choices=[], effects={
                    "cost": {"ammo_01": 30, "battle_explosive": 1},
                    "set_flag": {"tomas_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"dannati": +3}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Posso darti 30 munizioni e un esplosivo ma voglio una garanzia. Assicurami che i tuoi non ci spareranno alle spalle.»", "tomas_prag_n2_pay", {"ethics": +2, "reputation": {"dannati": +1}}))
            scelte_diplo_fase_2.append(("«Siamo disposti a pagare il tributo di 30 munizioni e un esplosivo per dimostrare le nostre buone intenzioni.»", "tomas_diplo_n2_pay", {"ethics": +1, "reputation": {"dannati": +1}}))
            scelte_aggro_fase_2.append(("«Prendi questo arsenale e toglietevi di mezzo prima che cambi idea e vi faccia saltare in aria.»", "tomas_aggro_n2_pay", {"ethics": -1, "reputation": {"dannati": -1}}))
            scelte_emp_fase_2.append(("«Se siete a corto di difese, ecco le munizioni e l'esplosivo. Non te li do come tassa, ma come aiuto.»", "tomas_emp_n2_pay", {"ethics": -2, "reputation": {"dannati": +1}}))
        else:
            scelte_prag_fase_2.append(("«Posso procurare questo arsenale, ma voglio una garanzia. Se vi consegniamo la merce, mi assicuri un passaggio sicuro?»", "tomas_prag_n2_fetch", {"ethics": +1}))
            scelte_diplo_fase_2.append(("«Non abbiamo armi a sufficienza, ma vi diamo la nostra parola che le cercheremo. Lasciateci passare in tregua.»", "tomas_diplo_n2_fetch", {"ethics": +2, "reputation": {"dannati": +1}}))
            scelte_aggro_fase_2.append(("«Non andiamo in giro armati fino ai denti per fare beneficenza. Vado a prenderle, ma tieni i tuoi cani al guinzaglio.»", "tomas_aggro_n2_fetch", {"ethics": -1, "reputation": {"dannati": -2}}))
            scelte_emp_fase_2.append(("«Se siete in pericolo andrò a cercare queste armi per voi. Non te le darò come una tassa, ma come un aiuto.»", "tomas_emp_n2_fetch", {"ethics": -2, "reputation": {"dannati": +1}}))

        scelte_prag_fase_2.extend([
            ("«Le armi scarseggiano per tutti. Al posto dell'arsenale, posso darvi le coordinate di un deposito abbandonato. Vale molto di più.»", "tomas_prag_n2_info", {"ethics": -3, "reputation": {"dannati": +3, "solidali": -5}}),
            ("«Trenta munizioni e un esplosivo sono un prezzo esorbitante. Facciamo venti e nessuna bomba, e nessuno si fa male.»", "tomas_prag_n2_negotiate", {"reputation": {"dannati": -2}}),
            ("«[Ignora e allontanati]»", "tomas_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Potremmo stabilire una rotta commerciale. Lasciateci passare ora e vi assicuro che la nostra futura collaborazione porterà di più.»", "tomas_diplo_n2_trade", {"ethics": +3, "reputation": {"dannati": +3}}),
            ("«Anche in questo caos deve esserci un codice. Permetteteci di passare indenni, dimostrerà la vostra forza senza inutili crudeltà.»", "tomas_diplo_n2_honor", {"ethics": -2, "reputation": {"dannati": +1}}),
            ("«[Ignora e allontanati]»", "tomas_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Se vuoi le mie armi, te le faccio assaggiare una per una. E vediamo quanti ne riesci a digerire prima di saltare in aria.»", "tomas_aggro_n2_intimidate", {"ethics": -3, "reputation": {"dannati": +1}}),
            ("«[Guardando gli uomini di Tomas] Chi di voi idioti vuole morire per primo? Fate un passo avanti e vi faccio esplodere.»", "tomas_aggro_n2_force", {"ethics": -2, "reputation": {"dannati": -1}}),
            ("«[Ignora e allontanati]»", "tomas_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Chi ti ha ferito così tanto? Chi ti ha tradito per spingerti a odiare a tal punto chiunque cerchi di aiutarti?»", "tomas_emp_n2_care", {"ethics": -1, "reputation": {"dannati": -1}}),
            ("«Sotto quella maschera di violenza c'è un uomo ferito. Ma c'è ancora speranza, non devi per forza essere un mostro per sopravvivere.»", "tomas_emp_n2_hope", {"ethics": -1, "reputation": {"dannati": +1}}),
            ("«[Ignora e allontanati]»", "tomas_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Tieni i tuoi uomini tranquilli, andrò a cercare questo arsenale.»", "tomas_prag_n3_deal", {"ethics": +1, "reputation": {"dannati": +1}}),
            ("«Ho capito come funziona. Vado a prendere la merce, non muovetevi da qui.»", "tomas_prag_n3_deal", {"ethics": +2, "reputation": {"dannati": +2}}),
            ("«Le condizioni sono chiare. Torno con la roba, niente scherzi nel frattempo.»", "tomas_prag_n3_deal", {"ethics": -1, "reputation": {"dannati": -1}}),
        ]

        scelte_diplo_fase_3 = [
            ("«Comprendo le vostre condizioni. Eviteremo lo scontro e cercheremo le armi per il pedaggio.»", "tomas_diplo_n3_thanks", {"ethics": -1, "reputation": {"dannati": +1}}),
            ("«Rispettiamo le regole del vostro territorio. Vi procureremo il pagamento richiesto, mantenete la tregua.»", "tomas_diplo_n3_thanks", {"ethics": -1, "reputation": {"dannati": +1}}),
            ("«Tregua accettata. Andiamo a raccogliere il pedaggio, non fate mosse avventate mentre siamo via.»", "tomas_diplo_n3_thanks", {"ethics": +2, "reputation": {"dannati": +1}}),
        ]

        scelte_aggro_fase_3 = [
            ("«Ti porto la tua roba. Ma guardati le spalle, Tomas. La mia pazienza è agli sgoccioli.»", "tomas_aggro_n3_leave", {"ethics": +1, "reputation": {"dannati": +3}}),
            ("«Vado a cercarle. Tieni al guinzaglio i tuoi cani rabbiosi finché non torno.»", "tomas_aggro_n3_leave", {"ethics": -1, "reputation": {"dannati": +1}}),
            ("«Avrai le armi. Ma fai un solo passo falso quando torno, e ti taglio la gola.»", "tomas_aggro_n3_leave", {"ethics": -3, "reputation": {"dannati": -1}})
        ]

        scelte_emp_fase_3 = [
            ("«Andremo a cercare le armi. Cerca di stare tranquillo, non ti faremo alcun male.»", "tomas_emp_n3_care", {"ethics": -1, "reputation": {"dannati": +1}}),
            ("«Mantieni la calma e sopravvivi fino al nostro ritorno. Torneremo con quello che ti serve.»", "tomas_emp_n3_care", {"ethics": +1, "reputation": {"dannati": +2}}),
            ("«Non sei solo in questo incubo, Tomas. Ti aiuteremo. Aspettaci qui.»", "tomas_emp_n3_care", {"ethics": -1, "reputation": {"dannati": +1}})
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Risparmiamo le sceneggiate e le intimidazioni. Siete qui per fare cassa, non per sparare a vista. Qual è il pedaggio per attraversare questo incrocio?»", "tomas_prag_n1_direct", {"ethics": -1, "reputation": {"dannati": +1}}),
                     ("«Possiamo iniziare uno scontro a fuoco, ma costerà munizioni e uomini a entrambi. Tagliamo corto: fai il tuo prezzo e vediamo se conviene.»", "tomas_prag_n1_direct", {"ethics": -1, "reputation": {"dannati": -1}}),
                     ("«Voi controllate la strada, noi dobbiamo passare. Non ho intenzione di fare l'eroe oggi. Quant'è la tassa per il transito?»", "tomas_prag_n1_direct", {"ethics": +1, "reputation": {"dannati": +1}})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«Siamo viaggiatori pacifici. Non cerchiamo guai, chiediamo solo il permesso di transitare per questo incrocio senza recare alcun disturbo.»", "tomas_diplo_n1_civic", {"ethics": -1, "reputation": {"dannati": -1}}),
                     ("«Non abbiamo intenzioni ostili. Sono certo che possiamo trovare un accordo pacifico che permetta a entrambi di evitare inutili spargimenti di sangue.»", "tomas_diplo_n1_civic", {"ethics": +1, "reputation": {"dannati": -1}}),
                     ("«Ci sono fin troppe minacce là fuori per dover combattere tra noi. Vi proponiamo una tregua temporanea per lasciarci attraversare il vostro territorio.»", "tomas_diplo_n1_civic", {"ethics": +1, "reputation": {"dannati": +1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Puntando l'arma direttamente al volto di Tomas] Toglietevi immediatamente di mezzo. Se mi fate perdere altro tempo, questa fottuta barricata la dipingo col vostro sangue.»", "tomas_aggro_n1_head", {"ethics": -3, "reputation": {"dannati": -2}}),
                     ("«[Avanzando con rabbia, le armi spianate] Fate un passo indietro e abbassate quei ferri vecchi. Sgombrate la strada o giuro che vi ammazzo tutti prima che possiate battere ciglio.»", "tomas_aggro_n1_head", {"ethics": -2, "reputation": {"dannati": -1}}),
                     ("«[Sputando a terra, con un ringhio] Ascoltami bene, faccia da cane. Dì ai tuoi scagnozzi di levarsi dai coglioni, o la tua stupida banda finirà in pasto ai morti.»", "tomas_aggro_n1_head", {"reputation": {"dannati": +1}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«Abbassiamo le armi, ti prego. C'è già fin troppa morte là fuori, non dobbiamo per forza farci del male a vicenda in questa strada.»", "tomas_emp_n1_care", {"ethics": -2, "reputation": {"dannati": -2}}),
                     ("«Hai gli occhi carichi di rabbia e tensione. Se c'è un modo per aiutarti senza ricorrere alla violenza, noi siamo disposti ad ascoltare.»", "tomas_emp_n1_care", {"reputation": {"dannati": -1}}),
                     ("«Mi dispiace davvero che il mondo ci abbia ridotti così, a puntarci i fucili addosso per sopravvivere. Troviamo una soluzione pacifica, nessuno deve morire oggi.»", "tomas_emp_n1_care", {"ethics": +1, "reputation": {"dannati": -3}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Tomas", text="[Sbarra la strada con un fucile a pompa] Voi due non andate da nessuna parte. Siete la mia assicurazione sulla vita per oggi.",
            choices=[
                ("«[Rivet] Dimmi il tuo prezzo e facciamola finita.»", "tomas_prag_n1_direct", {"reputation": {"dannati": +1}}),
                ("«[Rivet] Spostati ora, o sarai il primo a cadere.»", "tomas_aggro_n1_head", {"reputation": {"dannati": -1}}),
                ("«[Echo] Non vogliamo attriti, chiediamo un accordo.»", "tomas_diplo_n1_civic"),
                ("«[Echo] Calmiamoci. Non c'è bisogno di arrivare alle armi.»", "tomas_emp_n1_care")
            ]))

        tree.add_node(DialogueNode(node_id="tomas_prag_n1_direct", speaker="Tomas", text="[Sputa a terra, facendo un mezzo sorriso sghembo mentre si appoggia alla canna del suo fucile] Niente eroi, eh? Bene. Odio i turisti che fanno i gradassi e mi costringono a pulire il sangue dall'asfalto. Mi piace chi va dritto al sodo. Volete passare senza che i miei ragazzi vi trasformino in un colabrodo? La tassa per la vostra assicurazione sulla vita è di 30 Munizioni e 1 Esplosivo da Combattimento. Sganciate la merce e chiudiamo un occhio.", choices=scelte_prag_fase_2))

        tree.add_node(DialogueNode(node_id="tomas_diplo_n1_civic", speaker="Tomas", text="[Sputa a terra divertito, scambiando un'occhiata beffarda con i suoi scagnozzi prima di scoppiare a ridere] 'Viaggiatori pacifici'? 'Permesso di transitare'? Ahah! Ascoltami bene, diplomatico del cazzo: l'unica 'pace' che rispetto si misura in potenza di fuoco. Volete passare senza farvi bucare la pancia? Vi costerà 30 Munizioni e 1 Esplosivo. Pagate il pedaggio o vi facciamo a pezzi.", choices=scelte_diplo_fase_2,  effects={"combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_aggro_n1_head", speaker="Tomas", text="[Mostra i denti marci in un ghigno, visibilmente eccitato mentre i suoi uomini ridacchiano nervosamente] Oh, mi piacciono quelli che abbaiano forte! Ma l'acciaio e le chiacchiere non ti fanno passare vivo da qui. Ti do una possibilità: pagate il tributo di 30 Munizioni [ammo_01] e 1 Esplosivo [battle_explosive] e vi lascio la pelle attaccata alle ossa. Altrimenti, finisce in un bagno di sangue.", choices=scelte_aggro_fase_2))

        tree.add_node(DialogueNode(node_id="tomas_emp_n1_care", speaker="Tomas", text="[Spinge l'arma in avanti con un movimento brusco, i muscoli del collo tesi e lo sguardo feroce] Chiudi quella cazzo di bocca! Siete solo dei deboli, e i deboli qui diventano concime. Volete dimostrare quanto tenete alla vostra preziosa vita? Consegnate 30 Munizioni e 1 Esplosivo e forse non vi faccio saltare la testa. Muovetevi!", choices=scelte_emp_fase_2,  effects={"combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_prag_n2_pay", speaker="Tomas", text="[Ispeziona l'arsenale] Così si ragiona. Nessun morto, per oggi. Non vogliamo sprecare proiettili su chi ha già pagato la tassa.", choices=[],
            effects={"cost": {"ammo_01": 30, "battle_explosive": 1}, "reputation": {"dannati": +3}, "set_flag": {"tomas_prag_quest_active": True, "tomas_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="tomas_prag_n2_fetch", speaker="Tomas", text="[Lo fissa negli occhi, indurendo l'espressione] La garanzia è che se pagate, vi lascio respirare altri cinque minuti. Le regole restano le stesse: andate a prendere quelle 30 Munizioni e l'esplosivo o non passate.", choices=[],
            effects={"set_flag": {"tomas_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="tomas_diplo_n2_pay", speaker="Tomas", text="[Prende l'equipaggiamento con un ghigno scettico] La diplomazia che esplode... questo mi piace. Nessun massacro, per oggi. Andate prima che cambi idea.", choices=[],
            effects={"cost": {"ammo_01": 30, "battle_explosive": 1}, "reputation": {"dannati": +3}, "set_flag": {"tomas_diplo_quest_active": True, "tomas_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="tomas_diplo_n2_fetch", speaker="Tomas", text="[Sbuffa rumorosamente] Le belle parole di un morto di fame non valgono niente. Andate a cercare questo arsenale se volete sopravvivere.", choices=[],
            effects={"set_flag": {"tomas_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="tomas_aggro_n2_pay", speaker="Tomas", text="[Afferra le armi ridendo sonoramente] Ah! Fai il duro ma alla fine paghi il tuo arsenale come tutti gli altri. Sparite dalla mia vista.", choices=[],
            effects={"cost": {"ammo_01": 30, "battle_explosive": 1}, "reputation": {"dannati": +4}, "set_flag": {"tomas_aggro_quest_active": True, "tomas_paid": True}, "end": True,  "combat_risk": 0.02}))
        tree.add_node(DialogueNode(node_id="tomas_aggro_n2_fetch", speaker="Tomas", text="[Alza la canna del fucile all'altezza del tuo viso] Abbaia quanto ti pare, ma se non vai a prendere la mia roba ti stacco la testa. Muovi il culo.", choices=[],
            effects={"set_flag": {"tomas_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="tomas_emp_n2_pay", speaker="Tomas", text="[Strappa l'equipaggiamento dalle tue mani con rabbia mascherata] Me li regali? Pensi che abbia bisogno della carità? Li prendo solo perché mi spettano.", choices=[],
            effects={"ethics": +1, "reputation": {"dannati": +1}, "cost": {"ammo_01": 30, "battle_explosive": 1}, "set_flag": {"tomas_emp_quest_active": True, "tomas_paid": True}, "end": True, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="tomas_emp_n2_fetch", speaker="Tomas", text="[Urla con voce rotta dalla rabbia] Smettila di scavare dove non ti riguarda e vai a prendere le armi che ho chiesto, o ti ammazzo qui e ora!", choices=[],
            effects={"set_flag": {"tomas_emp_quest_active": True}, "ethics": -1, "end": True, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_prag_n2_info", speaker="Tomas", text="[Scuote la testa con finta compassione] Le tue coordinate potrebbero essere una miniera d'oro o una fossa comune, ma a me non frega un cazzo. Qui l'unica valuta che ha corso legale è quella che spara. O mi portate quelle 30 Munizioni e l'esplosivo, o vi girate.", choices=scelte_prag_fase_3,
            effects={"info_shared": "solidali_armory", "set_flag": {"tomas_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="tomas_prag_n2_negotiate", speaker="Tomas", text="[Ride sguaiatamente] Hai scambiato questo posto di blocco per un fottuto mercatino delle pulci? Il prezzo lo faccio io. Le tariffe non si discutono: portatemi 30 Munizioni e l'esplosivo, o la strada resta chiusa.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"tomas_prag_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_diplo_n2_trade", speaker="Tomas", text="[Ignora le parole e carica l'arma] 'Futura collaborazione'? Le promesse non uccidono i morti che camminano e non fanno esplodere le barricate. Siete solo chiacchiere. O mi metti in mano l'arsenale adesso, o cominci a pregare il tuo dio.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"tomas_diplo_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="tomas_diplo_n2_honor", speaker="Tomas", text="[Ride sguaiatamente] Un codice di condotta? La mia forza la dimostro spaccandoti i denti se non paghi. Niente più stronzate: 30 Munizioni e l'esplosivo o vi lascio a sanguinare sull'asfalto.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"tomas_diplo_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_aggro_n2_intimidate", speaker="Tomas", text="[Fa scattare il percussore del fucile] Che bella immagine! Magari mi strozzo, ma prima i miei ragazzi ti apriranno in due come un maiale. Hai tre secondi per decidere: andate a prendermi le armi o vi faccio assaggiare il nostro di piombo.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"tomas_aggro_quest_active": True}, "combat_risk": 0.02}))
        tree.add_node(DialogueNode(node_id="tomas_aggro_n2_force", speaker="Tomas", text="[Ride sguaiatamente] Sei un fottuto pazzo! I miei ragazzi non vedono l'ora di farti a pezzi. Scegli ora, hai tre secondi: portami 30 Munizioni e un esplosivo o vi crivelliamo di colpi dove state.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"tomas_aggro_quest_active": True}, "combat_risk": 0.02}))

        tree.add_node(DialogueNode(node_id="tomas_emp_n2_care", speaker="Tomas", text="[Sbatte il calcio del fucile contro un bidone] Io non sto soffrendo! E non voglio la tua fottuta carità! Questa è un'estorsione, non una donazione. Vai a prendere quelle armi e portale qui, altrimenti sarai tu a soffrire.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"tomas_emp_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="tomas_emp_n2_hope", speaker="Tomas", text="[Gli punta la canna dell'arma dritto al petto] La speranza è per i cadaveri! I mostri sopravvivono. Voi no. Portami l'arsenale richiesto e smettila di fare il predicatore, o ti giuro che ti faccio a pezzi.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"tomas_emp_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="tomas_prag_n3_deal", speaker="Tomas", text="[Fa un cenno ai suoi uomini di abbassare leggermente le armi] Non giochiamo mai quando si tratta di affari. Muovetevi a cercare quella roba. Se tornate a mani vuote vi usiamo come bersagli mobili per ammazzare il tempo.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"tomas_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="tomas_diplo_n3_thanks", speaker="Tomas", text="[Sbuffa una risata sprezzante, senza togliere il dito dal grilletto] 'Tregua accettata'... fate ridere i polli. Andate a cercare la mia artiglieria, conigli. E muovetevi, prima che decida che preferisco usare i vostri teschi come bersagli.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"tomas_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="tomas_aggro_n3_leave", speaker="Tomas", text="[Abbassa lentamente l'arma, scoppiando in una cruda risata catartica] *Ahah! Così mi piaci! Va' a prendere il mio arsenale, cagnaccio. Ti aspettiamo qui. Ma sbrigati... il mio grilletto prude.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"tomas_aggro_quest_active": True}, "combat_risk": 0.40}))

        tree.add_node(DialogueNode(node_id="tomas_emp_n3_care", speaker="Tomas", text="[Sputa a terra con disprezzo] Mi fate venire il voltastomaco. Non voglio le vostre rassicurazioni e non ho bisogno di nessuno! Sparite dalla mia vista prima che perda del tutto la testa. E non osate farvi rivedere senza il mio fottuto pagamento.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"tomas_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="tomas_eval_walk_away", speaker="Tomas", text="Credete di potermi voltare le spalle? FUOCO!", choices=[],
            effects={"start_combat": True, "reputation": {"dannati": -10}}))

        return tree

    @staticmethod
    def build_griss() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Griss")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        molotov_possedute = count_item("molotov_cocktail")
        piranha_posseduta = count_item("piranha_solution")

        ha_i_requisiti = molotov_possedute >= 2 and piranha_posseduta >= 1

        q_prag  = gs.flags.get("griss_prag_quest_active", False)
        q_diplo = gs.flags.get("griss_diplo_quest_active", False)
        q_aggro = gs.flags.get("griss_aggro_quest_active", False)
        q_emp   = gs.flags.get("griss_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("griss_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Griss",
                    text="Il dazio è pagato. Nessuno dei miei vi toccherà... per oggi. Filate.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "Siamo ancora in attesa del dazio. 2 Molotov e una Soluzione Piranha. Le avete o no?"
            elif q_diplo:
                greeting = "[Sghignazza] Eccovi qui. Il vostro accordo formale vale solo se avete l'acido e le bombe."
            elif q_aggro:
                greeting = "[Vi fissa con odio] Hai fegato a tornare. Sputa le molotov e la soluzione piranha, prima che decida di prendermi le tue armi."
            elif q_emp:
                greeting = "Ancora voi? La pietà non riempie i nostri forzieri. Avete gli esplosivi e l'acido?"
            else:
                greeting = "Nessuno passa senza pagare il dazio. Avete le molotov e la soluzione piranha?"

            if ha_i_requisiti:
                scelte_ritorno = [("«Sì, ecco le 2 molotov e l'acido. Ora facci passare.»", "griss_standby_pay")]
            else:
                scelte_ritorno = [("«Li sto ancora cercando. Tornerò.»", "griss_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Griss", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="griss_standby_wait", speaker="Griss",
                text="Allora levatevi dalle palle. Se fate un passo oltre questa linea vi sventro.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="griss_standby_pay", speaker="Griss",
                text="[Prende gli esplosivi e l'acido con cautela] Roba che scotta. Accettabile. Potete attraversare il nostro territorio. Ma non fermatevi.",
                choices=[], effects={
                    "cost": {"molotov_cocktail": 2, "piranha_solution": 1},
                    "set_flag": {"griss_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"dannati": +3}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Ho 2 molotov e la soluzione piranha. Prendili e lasciaci in pace.»", "griss_prag_n2_pay", {"ethics": +1, "reputation": {"dannati": +1}}))
            scelte_diplo_fase_2.append(("«Siamo disposti a pagare il pedaggio per garantire un transito pacifico. Ecco l'arsenale.»", "griss_diplo_n2_pay", {"ethics": +2, "reputation": {"dannati": +2}}))
            scelte_aggro_fase_2.append(("«Prendi questa roba esplosiva e levati di mezzo prima che te la accenda in faccia.»", "griss_aggro_n2_pay", {"ethics": -2, "reputation": {"dannati": -1}}))
            scelte_emp_fase_2.append(("«Abbiamo gli esplosivi e l'acido che vi servono. Prendeteli, ma fate attenzione a come li usate.»", "griss_emp_n2_pay", {"ethics": +2, "reputation": {"dannati": +1}}))
        else:
            scelte_prag_fase_2.append(("«Non andiamo in giro carichi di bombe e acidi. Dacci il tempo di setacciare la zona o craftarli, e te li porteremo.»", "griss_prag_n2_fetch", {"ethics": +1}))
            scelte_diplo_fase_2.append(("«Non abbiamo questa quantità con noi, ma vi diamo la parola che la cercheremo. Attendete il nostro ritorno.»", "griss_diplo_n2_fetch", {"ethics": +2}))
            scelte_aggro_fase_2.append(("«Non siamo i vostri fattorini. Vado a prenderli, ma tieni a bada i tuoi cani o tornerò sparando.»", "griss_aggro_n2_fetch", {"ethics": -2, "reputation": {"dannati": -1}}))
            scelte_emp_fase_2.append(("«Andremo a cercare queste armi per voi, ma non ve le daremo come una tassa estorta. Sarà per aiutarvi a difendervi.»", "griss_emp_n2_fetch", {"ethics": +1}))

        scelte_prag_fase_2.extend([
            ("«Bombe e acidi si trovano, ma l'informazione è potere. Posso darvi le rotte esatte delle pattuglie dei Solidali. È uno scambio alla pari.»", "griss_prag_n2_info", {"ethics": -2, "reputation": {"dannati": +3, "solidali": -5}}),
            ("«Due molotov e una soluzione piranha sono un prezzo altissimo per due sole persone a piedi. Facciamo una molotov e basta.»", "griss_prag_n2_trade", {"reputation": {"dannati": -1}}),
            ("«[Ignora e allontanati]»", "griss_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Se ci permettete di passare oggi, vi garantisco che stabiliremo una rotta commerciale. Vi porteremo merci molto più pregiate in futuro.»", "griss_diplo_n2_trade", {"ethics": +2, "reputation": {"dannati": +2}}),
            ("«Ragioniamo con logica: uno scontro a fuoco vi costerebbe feriti e proiettili. Lasciarci passare è oggettivamente la mossa più vantaggiosa per entrambi.»", "griss_diplo_n2_logic", {"reputation": {"dannati": +1}}),
            ("«[Ignora e allontanati]»", "griss_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Ti farò ingoiare queste molotov intere se continui a bloccarmi. Noi non paghiamo pedaggi a nessuno, tantomeno a te.»", "griss_aggro_n2_intimidate", {"ethics": -2, "reputation": {"dannati": +1}}),
            ("«[Togliendo la sicura con un clic metallico] Il mio pedaggio è nel caricatore. Fatti sotto se hai il coraggio di prenderlo, pezzo di merda.»", "griss_aggro_n2_force", {"ethics": -3, "reputation": {"dannati": -1}}),
            ("«[Ignora e allontanati]»", "griss_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Siamo tutti esseri umani, Griss. Cerchiamo tutti di sopravvivere alla stessa apocalisse. Aiutarci a vicenda è l'unico modo per non perdere del tutto la nostra umanità.»", "griss_emp_n2_care", {"ethics": +2, "reputation": {"dannati": -1}}),
            ("«Perché scegliete una vita fatta solo di rabbia e brutalità? C'è ancora spazio per la speranza e per la ricostruzione là fuori, se solo vi fidaste degli altri.»", "griss_emp_n2_past", {"ethics": +1, "reputation": {"dannati": -2}}),
            ("«[Ignora e allontanati]»", "griss_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Restate calmi, andiamo a cercare o costruire la vostra merce.»", "griss_prag_n3_deal", {"ethics": +1, "reputation": {"dannati": +1}}),
            ("«Torno con la roba. Tenete giù le armi finché non abbiamo concluso lo scambio.»", "griss_prag_n3_deal", {"ethics": 0, "reputation": {"dannati": +1}}),
            ("«Accettiamo la tariffa. Procureremo l'arsenale, ma al ritorno esigo un lasciapassare immediato.»", "griss_prag_n3_deal", {"ethics": -1, "reputation": {"dannati": -1}}),
        ]

        scelte_diplo_fase_3 = [
            ("«Rispetteremo le regole del vostro territorio. Cercheremo gli oggetti richiesti per il pedaggio.»", "griss_diplo_n3_thanks", {"ethics": +1, "reputation": {"dannati": +1}}),
            ("«Tregua accettata. Vi procureremo il pagamento, mantenete i vostri uomini a bada fino al nostro ritorno.»", "griss_diplo_n3_thanks", {"ethics": +1, "reputation": {"dannati": +1}}),
            ("«Apprezzo la franchezza delle vostre condizioni. Aspettateci qui, andremo a recuperare il carico.»", "griss_diplo_n3_thanks", {"ethics": +2, "reputation": {"dannati": +2}}),
        ]

        scelte_aggro_fase_3 = [
            ("«Ti porterò queste fottute bombe. Ma fai un passo indietro e tieni al guinzaglio i tuoi uomini, o vi scortico vivi.»", "griss_aggro_n3_leave", {"ethics": -1, "reputation": {"dannati": +2}}),
            ("«Vado a cercarle. Ma se scopro che ci state seguendo, torno e vi ammazzo tutti uno per uno.»", "griss_aggro_n3_leave", {"ethics": -2, "reputation": {"dannati": +1}}),
            ("«Avrai le tue molotov. Levatevi dai piedi e non fate mosse avventate finché non torno.»", "griss_aggro_n3_leave", {"ethics": -1, "reputation": {"dannati": -1}}),
        ]

        scelte_emp_fase_3 = [
            ("«Sopravvivi, Griss. Non vogliamo combattere. Cercheremo la merce e torneremo senza armi spianate.»", "griss_emp_n3_care", {"ethics": +1, "reputation": {"dannati": +1}}),
            ("«Vi porteremo ciò che vi serve. Spero solo che questo basti a mantenere la pace tra noi.»", "griss_emp_n3_care", {"ethics": +2, "reputation": {"dannati": +1}}),
            ("«Andiamo a cercare tutto. Spero che un giorno possiate trovare un po' di serenità in questo inferno.»", "griss_emp_n3_care", {"ethics": +2, "reputation": {"dannati": -1}}),
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Tagliamo corto. Voi controllate il passaggio, noi dobbiamo attraversarlo. Non ho intenzione di perdere tempo o proiettili. Qual è la tassa di transito?»", "griss_prag_n1_direct", {"ethics": -1, "reputation": {"dannati": +1}}),
                     ("«Niente eroismi e niente minacce, andiamo dritti al punto. Siamo qui per fare affari. Dicci cosa ti serve per farci passare senza creare problemi.»", "griss_prag_n1_direct", {"ethics": +1, "reputation": {"dannati": +1}}),
                     ("«Il tempo è prezioso per entrambi. Fissa un dazio ragionevole per questo posto di blocco e ognuno andrà per la sua strada.»", "griss_prag_n1_direct", {"ethics": 0, "reputation": {"dannati": -1}})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«Riconosciamo il vostro controllo su questo territorio. Ci presentiamo pacificamente per chiedere il permesso di transitare senza causare problemi.»", "griss_diplo_n1_civic", {"ethics": +1, "reputation": {"dannati": -1}}),
                     ("«Non abbiamo intenzioni ostili e non vogliamo sprecare risorse in uno scontro. Vi proponiamo una tregua temporanea per attraversare l'avamposto.»", "griss_diplo_n1_civic", {"ethics": +1, "reputation": {"dannati": +1}}),
                     ("«Saluti. Siamo viaggiatori di passaggio. Vorremmo discutere con voi i termini per un accordo civile che ci garantisca un transito sicuro.»", "griss_diplo_n1_civic", {"ethics": +2, "reputation": {"dannati": -1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Avanzando a testa alta, con la mano sull'arma] Sgombrate la strada o vi ci passo sopra. Non ho tempo da perdere con dei cialtroni da posto di blocco.»", "griss_aggro_n1_head", {"ethics": -2, "reputation": {"dannati": -1}}),
                     ("«[Puntando l'arma direttamente alla testa di Griss] Ordina ai tuoi cani di fare la cuccia e togliti di mezzo, o stasera non sarai in grado di contare i tuoi morti.»", "griss_aggro_n1_head", {"ethics": -3, "reputation": {"dannati": -2}}),
                     ("«[Sputando a terra, a un palmo dagli stivali di Griss] Chi cazzo ti credi di essere, bestione? Fatti da parte subito, o questa barricata la dipingo col tuo sangue.»", "griss_aggro_n1_head", {"ethics": -2, "reputation": {"dannati": +1}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«[Abbassando le mani e parlando con tono calmo] I tuoi uomini hanno ferite infette. Non c'è bisogno di farci la guerra, possiamo offrirvi delle bende se ci lasciate passare in pace.»", "griss_emp_n1_care", {"ethics": +2, "reputation": {"dannati": -1}}),
                     ("«[Guardandosi attorno con genuina tristezza] C'è già troppa morte là fuori. Non dobbiamo essere nemici. Abbassiamo le armi e troviamo una soluzione pacifica.»", "griss_emp_n1_care", {"ethics": +2, "reputation": {"dannati": -2}}),
                     ("«[Con voce compassionevole] Mi dispiace vedervi costretti a vivere così, nel fango e sempre sulla difensiva. Vogliamo solo passare, senza causare altro dolore a nessuno.»", "griss_emp_n1_care", {"ethics": +3, "reputation": {"dannati": -3}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Griss", text="Fermi lì, insetti. Siete nel territorio dei Dannati. O pagate la tassa sul sangue o versate il vostro.",
            choices=[
                ("«[Rivet] Quanto vuoi per farci passare?»", "griss_prag_n1_direct", {"reputation": {"dannati": +1}}),
                ("«[Rivet] Levati dai piedi prima che ti faccia un buco in testa.»", "griss_aggro_n1_head", {"ethics": -1, "reputation": {"dannati": -1}}),
                ("«[Echo] Non vogliamo combattere, chiediamo il passaggio.»", "griss_diplo_n1_civic", {"ethics": +1}),
                ("«[Echo] Questa terra è un inferno, non peggioriamo le cose.»", "griss_emp_n1_care", {"ethics": +1})
            ]))

        tree.add_node(DialogueNode(node_id="griss_prag_n1_direct", speaker="Griss", text="[Sorride con sufficienza, abbassando di qualche centimetro la canna del suo fucile] Ah! Finalmente qualcuno che non piagnucola o fa finta di essere un duro. Mi piace chi va dritto al sodo, fa risparmiare tempo a me e sangue a voi. Le chiacchiere sono per i deboli, e qui da noi i deboli diventano concime. Il pedaggio per calpestare il mio asfalto è semplice: 2 Molotov [molotov_cocktail] e 1 Soluzione Piranha [piranha_solution]. Pagate il dazio e la strada è vostra.", choices=scelte_prag_fase_2))

        tree.add_node(DialogueNode(node_id="griss_diplo_n1_civic", speaker="Griss", text="[Sputa a terra, scoppiando a ridere sguaiatamente, subito imitato dai suoi sgherri] Sentite questo damerino! 'Transito pacifico', 'accordo civile'... Cazzo, sembra che tu stia leggendo un manuale del vecchio mondo! Ascoltami bene, faccia di bronzo: la pace è una cazzata per i deboli, e qui i deboli pagano i forti per continuare a respirare. Il biglietto per non farsi tagliare la gola è fissato a 2 Molotov e 1 Soluzione Piranha. Tirate fuori la roba o preparatevi a sanguinare.", choices=scelte_diplo_fase_2, effects={"combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="griss_aggro_n1_head", speaker="Griss", text="[Ride di gusto, mostrando una chiostra di denti d'oro e scheggiati, per nulla intimorito] Ah! Finalmente qualcuno con un po' di fegato e non la solita pecora piagnucolante! Mi piaci, hai il fuoco dentro. Ma qui da noi il rispetto si paga col botto, non solo con le belle minacce. Se volete passare senza scatenare un fottuto massacro, il tributo per chi ha le palle è di 2 Molotov e 1 Soluzione Piranha. Tirate fuori la roba e vi lascio la pelle intatta.", choices=scelte_aggro_fase_2))

        tree.add_node(DialogueNode(node_id="griss_emp_n1_care", speaker="Griss", text="[Sputa con disgusto, guardando Echo come se avesse appena calpestato una carcassa] Mi fai venire il voltastomaco. Tutta questa fottuta 'compassione' è la stessa malattia che ha reso il vecchio mondo debole e lo ha fatto crollare. Noi non siamo vittime da compatire, siamo i lupi che si nutrono di pecore patetiche come te. Vuoi sopravvivere e non farti sgozzare qui su due piedi per la tua debolezza? Allora pagherai la tassa sulla tua stupidità: portami 2 Molotov e 1 Soluzione Piranha e forse vi lascio vivere.", choices=scelte_emp_fase_2, effects={"combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="griss_prag_n2_pay", speaker="Griss", text="[Prende gli esplosivi con un ghigno] Saggio. Molto saggio. Il passaggio è vostro.", choices=[],
            effects={"cost": {"molotov_cocktail": 2, "piranha_solution": 1}, "reputation": {"dannati": +3}, "set_flag": {"griss_prag_quest_active": True, "griss_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="griss_prag_n2_fetch", speaker="Griss", text="[Fa spallucce, ridacchiando con un suo sgherro al fianco] Non mi frega un cazzo di dove li trovate o craftate. Avete il mio permesso di cercare nei dintorni, ma non fateci aspettare troppo. Il cancello si aprirà solo quando mi metterete in mano esattamente 2 Molotov e 1 Soluzione Piranha. Fino ad allora, restate fuori.", choices=[],
            effects={"set_flag": {"griss_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="griss_diplo_n2_pay", speaker="Griss", text="[Studia l'acido e le bombe] Non me ne frega niente dei vostri trattati di pace, ma questi esplosivi mi piacciono. Andate, e veloci.", choices=[],
            effects={"cost": {"molotov_cocktail": 2, "piranha_solution": 1}, "reputation": {"dannati": +3}, "set_flag": {"griss_diplo_quest_active": True, "griss_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="griss_diplo_n2_fetch", speaker="Griss", text="[Sbuffa rumorosamente] Le parole sono vento, e il vento non fa esplodere i miei nemici. Andate a cercare l'arsenale. Non ci sposteremo di un millimetro.", choices=[],
            effects={"set_flag": {"griss_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="griss_aggro_n2_pay", speaker="Griss", text="[Incrocia le braccia, ghignando mentre prende gli esplosivi] Alla fine tutti pagano. Sparite dalla mia vista prima che decida di prendermi anche i vostri stivali.", choices=[],
            effects={"cost": {"molotov_cocktail": 2, "piranha_solution": 1}, "reputation": {"dannati": +4}, "set_flag": {"griss_aggro_quest_active": True, "griss_paid": True}, "end": True, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="griss_aggro_n2_fetch", speaker="Griss", text="[Battersi il pugno aperto sul petto] Vai a cercare la mia roba, o la prossima volta che ci incrociamo ti sparo a vista. Muoviti.", choices=[],
            effects={"set_flag": {"griss_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="griss_emp_n2_pay", speaker="Griss", text="[Afferra le molotov bruscamente] Se volete giocare alla crocerossina con la vostra roba, non sarò certo io a fermarvi. Siete stupidi, ma utili. Ora andate.", choices=[],
            effects={"ethics": +1, "reputation": {"dannati": +1}, "cost": {"molotov_cocktail": 2, "piranha_solution": 1}, "set_flag": {"griss_emp_quest_active": True, "griss_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="griss_emp_n2_fetch", speaker="Griss", text="[Stringe gli occhi, digrignando i denti infastidito] Un dono? Siete davvero così irrimediabilmente decerebrati? Sbrigati a portarmi gli esplosivi prima che vi ammazzi per pura pietà.", choices=[],
            effects={"set_flag": {"griss_emp_quest_active": True}, "ethics": -1, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="griss_prag_n2_info", speaker="Griss", text="[Soppesa un'arma, riflettendo per un secondo prima di scuotere la testa] Le informazioni su quei rammolliti sono merce gradita, te lo concedo. Ma non ci distruggo i nemici con le parole. Tieniti i tuoi segreti militari per adesso. Se volete passare, l'unica valuta che ha corso legale qui oggi sono 2 Molotov e 1 Soluzione Piranha. Procurateli.", choices=scelte_prag_fase_3,
            effects={"info_shared": "solidali_patrol", "set_flag": {"griss_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="griss_prag_n2_trade", speaker="Griss", text="[Fa un passo avanti, torreggiando e indurendo lo sguardo] Non hai capito come funziona il mercato libero, vero? Io fisso il prezzo, tu paghi. Questa non è una fottuta asta di beneficenza. O li trovate tutti e tre, o vi girate e ve ne andate.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"griss_prag_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="griss_diplo_n2_trade", speaker="Griss", text="[Sbadiglia platealmente, grattandosi il collo sudicio] Il futuro? Amico, qui fuori non sappiamo nemmeno se domattina saremo ancora vivi, e tu mi parli di affari a lungo termine? Le tue belle promesse non mi servono stasera. Quindi risparmia il fiato: o mi porti il mio arsenale adesso, o la tua strada finisce in questo vicolo.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"griss_diplo_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="griss_diplo_n2_logic", speaker="Griss", text="[Scuote la testa, facendo un cenno ai suoi uomini che stringono i fucili] La tua logica fa schifo, 'professore'. A noi PIACE combattere. Usare qualche proiettile per bucarti la pancia non è uno spreco, è un ottimo passatempo per i miei ragazzi. Se non vuoi farci divertire, cè un solo fottuto modo: paga la tassa. Portami le bombe e l'acido o chiudiamo la conversazione nel sangue.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"griss_diplo_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="griss_aggro_n2_intimidate", speaker="Griss", text="[Si batte il petto massiccio con una mano, ridacchiando sadicamente] Prova a mettermi le mani in gola e vediamo se non ti stacco le braccia a morsi! Sarebbe uno scontro glorioso, te lo concedo. Ma gli affari vengono prima del divertimento. Hai due sole opzioni, belva: o vai a cercarmi le mie armi chimiche, o facciamo tingere l'asfalto di rosso adesso. Scegli.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"griss_aggro_quest_active": True}, "combat_risk": 0.02}))
        tree.add_node(DialogueNode(node_id="griss_aggro_n2_force", speaker="Griss", text="[Impugna l'arma con entusiasmo, facendo scrocchiare il collo muscoloso] Un caricatore pieno? Ottimo, lo prenderò dal tuo cadavere fumante! Ma ascoltami bene, testa calda: sparare diverte me, ma non mi aiuta a far esplodere le barricate dei Solidali. Quindi metti via quel ferro e accendi il cervello: o mi porti le molotov e l'acido, o vi maciulliamo qui e ora.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"griss_aggro_quest_active": True}, "combat_risk": 0.02}))

        tree.add_node(DialogueNode(node_id="griss_emp_n2_care", speaker="Griss", text="[Scuote la testa incredulo, ridendo con cattiveria] Aiutarci? L'apocalisse non è una fottuta tragedia, è stata una selezione naturale! E io non mi mischio con gli scarti destinati a estinguersi. Chiudi quella fogna e sbrigati a portarmi quelle molotov e quell'acido, prima che decida di aprirti la gola solo per ammazzare la noia.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"griss_emp_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="griss_emp_n2_past", speaker="Griss", text="[Avanza minacciosamente, la vena sul collo pulsante] Scelgo la violenza perché è l'unica cosa vera che sia mai esistita. La tua preziosa 'speranza' è solo un'illusione per i codardi che non hanno le palle di premere un grilletto. Smettila di farmi la paternale, mi stai facendo venire l'orticaria. Portami gli esplosivi, o ti faccio vedere subito quanto è reale la mia brutalità.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"griss_emp_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="griss_prag_n3_deal", speaker="Griss", text="[Fa un cenno di assenso ai suoi per farvi allontanare, mantenendo un'espressione dura] Ottimo. Andate a scavare e craftare. Ma tenete d'occhio l'orologio. La mia pazienza è sottile quanto la vostra speranza di vita. Tornate con l'arsenale o vi conviene non farvi più vedere in questo settore. Muovetevi.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"griss_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="griss_diplo_n3_thanks", speaker="Griss", text="[Sogghigna con disprezzo, abbassando la canna del fucile ma mantenendo un tono minaccioso] Bravi cagnolini. Avete finalmente capito come gira il mondo da queste parti. Muovete il culo e andate a cercare la mia roba. E vedete di fare in fretta: se tornate a mani vuote vi usiamo come carne da macello.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"griss_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="griss_aggro_n3_leave", speaker="Griss", text="[Sputa a terra, facendo un cenno ai suoi sgherri di aprire un varco parziale senza però abbassare del tutto le armi] Va bene, cagnaccio. Va' a cercare le mie bombe. Ti aspetto proprio qui. E vedi di non deludermi... sarebbe un vero peccato dover sprecare proiettili su qualcuno di così divertente. Muovi il culo!", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"griss_aggro_quest_active": True}, "combat_risk": 0.20}))

        tree.add_node(DialogueNode(node_id="griss_emp_n3_care", speaker="Griss", text="[Guarda i suoi uomini facendo una smorfia di puro ribrezzo, alzando gli occhi al cielo] Serenità... pace... siete la cosa più patetica che i miei stivali abbiano mai calpestato. Sparite dalla mia vista prima che vi spari per pura pietà, e non azzardatevi a rimettere piede qui senza la mia fottuta merce.", choices=[],
            effects={"end": True, "combat_avoided": True, "set_flag": {"griss_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="griss_eval_walk_away", speaker="Griss", text="Se scappate vi do la caccia come topi!", choices=[],
            effects={"end": True, "combat_avoided": True, "reputation": {"dannati": -5}}))

        return tree

class ErrantiDialogues:

    @staticmethod
    def build_sybil() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Sybil")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        hardware_posseduto = count_item("electronics_01")
        chip_posseduti = count_item("data_chip")
        badge_posseduti = count_item("key_card_01")

        ha_i_requisiti = hardware_posseduto >= 3 and chip_posseduti >= 1 and badge_posseduti >= 1

        q_prag  = gs.flags.get("sybil_prag_quest_active", False)
        q_diplo = gs.flags.get("sybil_diplo_quest_active", False)
        q_aggro = gs.flags.get("sybil_aggro_quest_active", False)
        q_emp   = gs.flags.get("sybil_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("sybil_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Sybil",
                    text="I server girano bene grazie al tuo hardware e ho bypassato la sicurezza col badge e il chip. Siete online. Andate.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "I dati hanno un prezzo. Hai i 3 componenti, il chip dati e il badge di accesso?"
            elif q_diplo:
                greeting = "Rete in attesa di connessione... Avete il materiale tecnologico per noi?"
            elif q_aggro:
                greeting = "[Senza guardarti dallo schermo] Siete tornati a fare la voce grossa o avete i 3 componenti, il chip e il badge che esigo?"
            elif q_emp:
                greeting = "[Si toglie le cuffie] Siete voi. Siete riusciti a trovare quel materiale per me?"
            else:
                greeting = "Senza i 3 componenti, il chip e il badge i miei archivi restano chiusi."

            if ha_i_requisiti:
                scelte_ritorno = [("«Ecco i componenti, il chip e il badge. Dammi l'accesso.»", "sybil_standby_pay")]
            else:
                scelte_ritorno = [("«Non abbiamo ancora tutto, ma lo troveremo.»", "sybil_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Sybil", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="sybil_standby_wait", speaker="Sybil",
                text="Il sistema va in standby. Non disturbate la rete se non avete la merce.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="sybil_standby_pay", speaker="Sybil",
                text="[Esamina il materiale e striscia il badge] Perfetto. Trasferimento dati autorizzato. Siete online.",
                choices=[], effects={
                    "cost": {"electronics_01": 3, "data_chip": 1, "key_card_01": 1},
                    "set_flag": {"sybil_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"indipendenti": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Ecco i tuoi pezzi, il chip e il badge, ma mettiamo in chiaro i termini: voglio priorità di banda assoluta.»", "sybil_prag_n2_pay", {"ethics": 0, "reputation": {"indipendenti": +1}}))
            scelte_diplo_fase_2.append(("«Rispettiamo l'accordo. Ecco tutto il materiale richiesto. Speriamo sia l'inizio di una fruttuosa collaborazione.»", "sybil_diplo_n2_pay", {"ethics": +2, "reputation": {"indipendenti": +2}}))
            scelte_aggro_fase_2.append(("«Prendi questi rottami, il chip e il fottuto badge, e sbloccami i dati subito, prima che inizi a strappare i fili.»", "sybil_aggro_n2_pay", {"ethics": -2, "reputation": {"indipendenti": -1}}))
            scelte_emp_fase_2.append(("«Ecco tutto il materiale tecnologico. Spero davvero che ti aiuti a tenere viva questa rete e a riposare un po'.»", "sybil_emp_n2_pay", {"ethics": +2, "reputation": {"indipendenti": +2}}))
        else:
            scelte_prag_fase_2.append(("«Andrò a recuperare tutto questo materiale, ma mettiamo in chiaro i termini: al mio ritorno voglio priorità assoluta.»", "sybil_prag_n2_fetch", {"ethics": 0}))
            scelte_diplo_fase_2.append(("«Siamo sprovvisti di questi oggetti al momento, ma vi diamo la nostra parola che li cercheremo. Rimanete in attesa.»", "sybil_diplo_n2_fetch", {"ethics": +1}))
            scelte_aggro_fase_2.append(("«Vado a prenderteli, ma vedi di non fare giochetti e preparare i miei dati intanto. Ci siamo capiti?»", "sybil_aggro_n2_fetch", {"ethics": -1, "reputation": {"indipendenti": -1}}))
            scelte_emp_fase_2.append(("«Lascia che siamo noi le tue mani là fuori. Cercheremo chip e componenti per te, così potrai chiudere gli occhi e riposare.»", "sybil_emp_n2_fetch", {"ethics": +2, "reputation": {"indipendenti": +1}}))

        scelte_prag_fase_2.extend([
            ("«Prima di farti da corriere per tutta questa roba, voglio assicurarmi che la tua rete funzioni. Dammi un pacchetto dati di prova.»", "sybil_prag_n2_info", {"ethics": -1, "reputation": {"indipendenti": -1}}),
            ("«Posso offrirti le chiavi di crittografia radio dei Razziatori. Dati per dati. Molto più facile che cercare chip e badge nei vicoli.»", "sybil_prag_n2_alternative", {"reputation": {"indipendenti": +1}}),
            ("«[Ignora e allontanati]»", "sybil_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Capisco la criticità. In attesa dei componenti, potremmo caricare sui vostri server i nostri ultimi dati di ricognizione come acconto.»", "sybil_diplo_n2_trade", {"ethics": +1, "reputation": {"indipendenti": +1}}),
            ("«Possiamo nel frattempo stabilire un canale di comunicazione criptato? Ci permetterebbe di coordinarci meglio durante la ricerca.»", "sybil_diplo_n2_crypto", {"ethics": +1}),
            ("«[Ignora e allontanati]»", "sybil_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Pensi che le tue macchine ti salveranno quando ti starò spezzando le dita una per una? Le macchine non sentono il dolore, Sybil. Tu sì.»", "sybil_aggro_n2_intimidate", {"ethics": -3, "reputation": {"indipendenti": -2}}),
            ("«[Afferrando un tastiera e scagliandola a terra] Ecco cosa ne faccio dei tuoi giocattoli! Vuoi vedere cos'altro posso sfasciare?»", "sybil_aggro_n2_force", {"ethics": -3, "reputation": {"indipendenti": -3}}),
            ("«[Ignora e allontanati]»", "sybil_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Vegli su tutti noi attraverso queste telecamere, Sybil. Ma chi veglia su di te? Non puoi sopravvivere circondata solo da schermi.»", "sybil_emp_n2_care", {"ethics": +2, "reputation": {"indipendenti": +1}}),
            ("«Hai costruito un faro in mezzo all'oscurità. È meraviglioso. Non lasceremo che il lavoro della tua vita si spenga, te lo prometto.»", "sybil_emp_n2_work", {"ethics": +1, "reputation": {"indipendenti": +2}}),
            ("«[Ignora e allontanati]»", "sybil_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Contratto accettato. Lascia la query aperta, torneremo con la tecnologia richiesta.»", "sybil_prag_n3_deal", {"ethics": 0}),
            ("«Affare fatto. Mantieni la connessione in standby, andiamo a cercare la roba.»", "sybil_prag_n3_deal", {"ethics": 0}),
            ("«Eseguo. Tieni le mani lontane dai nostri dati finché non torno con i componenti.»", "sybil_prag_n3_deal", {"ethics": -1}),
        ]

        scelte_diplo_fase_3 = [
            ("«I termini sono chiari e ragionevoli. Andremo a recuperare l'hardware e il badge. Rimanete in attesa del nostro ritorno.»", "sybil_diplo_n3_thanks", {"ethics": +1}),
            ("«Accordo siglato, Sybil. Considerateci i vostri tecnici esterni. Torneremo con i pezzi il prima possibile.»", "sybil_diplo_n3_thanks", {"ethics": +1}),
            ("«Ricevuto. Chiudiamo il canale per ora. Riapriremo la sessione non appena avremo i componenti richiesti.»", "sybil_diplo_n3_thanks", {"ethics": 0})
        ]

        scelte_aggro_fase_3 = [
            ("«Ti porto la tua dannata tecnologia, Sybil. Ma quando avrò quei codici, faremo i conti senza schermi a proteggerti.»", "sybil_aggro_n3_leave", {"ethics": -1, "reputation": {"indipendenti": -1}}),
            ("«Andiamo a cercarli. Ma vedi di non giocare sporco con i dati, o tornerò qui a finire il lavoro.»", "sybil_aggro_n3_leave", {"ethics": -2}),
            ("«Vado, ma non pensare di aver vinto. Consideralo solo un rinvio della tua esecuzione.»", "sybil_aggro_n3_leave", {"ethics": -2, "reputation": {"indipendenti": -1}})
        ]

        scelte_emp_fase_3 = [
            ("«Riposa un po' gli occhi nel frattempo. Penseremo noi ai tuoi server, non sei più sola.»", "sybil_emp_n3_care", {"ethics": +2}),
            ("«I tuoi server non cadranno stanotte. Te lo prometto, Sybil.»", "sybil_emp_n3_care", {"ethics": +1}),
            ("«Siamo in rete adesso. Tieni duro, torneremo prestissimo con quello che ti serve.»", "sybil_emp_n3_care", {"ethics": +1}),
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Ci servono mappe aggiornate e le credenziali di accesso per il settore nord. Dicci qual è la tua tariffa e chiudiamo la transazione.»", "sybil_prag_n1_direct", {"ethics": 0}),
                     ("«Risparmiamo tempo. Noi abbiamo bisogno di intel, tu hai bisogno di risorse per far girare questi rottami. Proponi uno scambio.»", "sybil_prag_n1_direct", {"ethics": -1, "reputation": {"indipendenti": +1}}),
                     ("«Vado dritto al punto: voglio estrarre dei dati dal tuo server. Qual è la valuta di scambio oggi?»", "sybil_prag_n1_direct", {"ethics": 0})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«[Con un cenno di rispetto e voce ferma] Salve, Sybil. Siamo qui per proporre una collaborazione ufficiale. Cerchiamo l'accesso ai database e siamo pronti a negoziare.»", "sybil_diplo_n1_civic", {"ethics": +2, "reputation": {"indipendenti": +1}}),
                     ("«[Tenendo le mani visibili, tono professionale] Sappiamo che la vostra rete è l'unica rimasta stabile. Vorremmo presentarci come partner per uno scambio di info.»", "sybil_diplo_n1_civic", {"ethics": +1, "reputation": {"indipendenti": +2}}),
                     ("«[Osservando i monitor con interesse] È ammirevole ciò che siete riuscita a mantenere attivo qui. Siamo alla ricerca di una rotta sicura, collaboriamo.»", "sybil_diplo_n1_civic", {"ethics": +1, "reputation": {"indipendenti": +1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Sbattendo il pugno sulla scrivania] Alza la testa da quegli schermi, topo di fogna! Sgancia i codici di accesso ora, o riduco questo posto a un ammasso di plastica bruciata!»", "sybil_aggro_n1_head", {"ethics": -3, "reputation": {"indipendenti": -2}}),
                     ("«[Puntando la canna della pistola contro il monitor] Non ho tempo per i tuoi giochetti da nerd. Dammi i file o il tuo prezioso computer sarà il primo a morire.»", "sybil_aggro_n1_head", {"ethics": -2, "reputation": {"indipendenti": -2}}),
                     ("«[Urlando per sovrastare il ronzio] Pensi di essere al sicuro dietro questi vetri? Apri quei database immediatamente o giuro che ti trascino fuori per i capelli!»", "sybil_aggro_n1_head", {"ethics": -3, "reputation": {"indipendenti": -1}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«[Mani in vista, voce dolce e rassicurante] Sybil, sei pallidissima. Da quanto tempo non dormi? Stai portando il peso dell'intera città sulle tue spalle.»", "sybil_emp_n1_care", {"ethics": +3, "reputation": {"indipendenti": +1}}),
                     ("«[Con sincera ammirazione e preoccupazione] Tenere accesa tutta questa rete da sola... è titanico. Ma stai collassando. Come possiamo aiutarti?»", "sybil_emp_n1_care", {"ethics": +2, "reputation": {"indipendenti": +2}}),
                     ("«[Avvicinandosi lentamente, tono protettivo] Eravamo venuti per dei dati, ma guardandoti... sembra che tu abbia bisogno di aiuto. Non devi fare tutto da sola.»", "sybil_emp_n1_care", {"ethics": +3, "reputation": {"indipendenti": +2}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Sybil", text="[Digita veloce] Siete sui miei sensori da tre isolati. Entrate veloce, cosa vi serve dalla rete?",
            choices=[
                ("«[Rivet] Dati. Dimmi cosa costa l'accesso.»", "sybil_prag_n1_direct"),
                ("«[Rivet] Dacci i codici prima che ti sfasci i monitor.»", "sybil_aggro_n1_head"),
                ("«[Echo] Vorremmo stabilire una collaborazione.»", "sybil_diplo_n1_civic"),
                ("«[Echo] È pazzesco che tu gestisca tutto da sola...»", "sybil_emp_n1_care")
            ]))

        tree.add_node(DialogueNode(node_id="sybil_prag_n1_direct", speaker="Sybil", text="[Senza staccare gli occhi dallo schermo, le dita che volano su una tastiera meccanica] Sintassi pulita. Nessun pacchetto di dati sprecato in inutili convenevoli. Il mio firewall per voi è semplice: ho bisogno di riparazioni e di credenziali esterne. Mi servono 3 Componenti Hardware, 1 Chip Dati e 1 Badge di Accesso [key_card_01]. Portatemi il pacchetto completo e vi apro le porte di root. Altrimenti, l'accesso è negato.", choices=scelte_prag_fase_2, effects={"reputation": {"indipendenti": +1}}))

        tree.add_node(DialogueNode(node_id="sybil_diplo_n1_civic", speaker="Sybil", text="[Annuisce senza staccare gli occhi dal monitor, il riflesso verde del codice illumina il suo volto pallido] Handshake accettato. È rinfrescante ricevere un segnale pulito. La vostra proposta di collaborazione è stata archiviata, ma c'è un errore critico a livello hardware e di permessi. Prima di avviare il download, il sistema richiede un input materiale: portatemi 3 Componenti Hardware, 1 Chip Dati per lo storage, e 1 Badge di Accesso per bypassare i protocolli di sicurezza militari.", choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="sybil_aggro_n1_head", speaker="Sybil", text="[Continua a digitare ignorando l'arma, il volto illuminato solo dal riverbero verde dei codici] Rilevato picco di decibel inutile. Analisi del rischio: trascurabile. Se vuoi bypassare il mio disprezzo e ottenere i codici, devi riparare i miei nodi e fornirmi i bypass. Portami 3 Componenti Hardware, 1 Chip Dati e 1 Badge di Accesso. È l'unico comando che accetto.", choices=scelte_aggro_fase_2, effects={"ethics": -1, "reputation": {"indipendenti": -4}}))

        tree.add_node(DialogueNode(node_id="sybil_emp_n1_care", speaker="Sybil", text="[Smette improvvisamente di digitare. Le mani restano sospese a mezz'aria, tremanti. Ti fissa, confusa] Input non riconosciuto... questa è un'anomalia di sistema. Nessuno mi chiede mai del mio uptime personale. [Si schiarisce la voce e abbassa lo sguardo] I miei server principali stanno fondendo e non riesco a penetrare la rete del distretto sud. Se volete davvero aiutarmi, ho un disperato bisogno di 3 Componenti Hardware, 1 Chip Dati e 1 Badge di Accesso.", choices=scelte_emp_fase_2, effects={"ethics": +2, "reputation": {"indipendenti": +2}}))

        tree.add_node(DialogueNode(node_id="sybil_prag_n2_pay", speaker="Sybil", text="[Formatta l'hardware e passa il badge sul lettore] Eseguiti. Siete nel sistema.", choices=[],
            effects={"cost": {"electronics_01": 3, "data_chip": 1, "key_card_01": 1}, "reputation": {"indipendenti": +3}, "set_flag": {"sybil_prag_quest_active": True, "sybil_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="sybil_prag_n2_fetch", speaker="Sybil", text="[Digitando una rapida sequenza di comandi, il tono atono] Parametri accettabili. Ma i privilegi di admin non si sbloccano con le promesse a vuoto. Il gateway rimane chiuso finché lo scanner non rileva i pezzi. Torna con i 3 Componenti Hardware, il Chip e il Badge, e avrai la tua banda larga.", choices=[],
            effects={"set_flag": {"sybil_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="sybil_diplo_n2_pay", speaker="Sybil", text="[Collega i componenti con cura, lo sguardo si distende] Scansione positiva. Credenziali accettate. Dati sbloccati, benvenuti sulla mia rete.", choices=[],
            effects={"cost": {"electronics_01": 3, "data_chip": 1, "key_card_01": 1}, "reputation": {"indipendenti": +4}, "set_flag": {"sybil_diplo_quest_active": True, "sybil_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="sybil_diplo_n2_fetch", speaker="Sybil", text="[Annuisce senza distrarsi] I dati logici non bypassano il problema fisico. Trovate il materiale e i permessi, e potremo procedere. Riavvio sessione in corso.", choices=[],
            effects={"set_flag": {"sybil_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="sybil_aggro_n2_pay", speaker="Sybil", text="[Prende l'hardware senza smettere di digitare con l'altra mano] Materiale ricevuto. Dati trasferiti. E ora fuori dal mio bunker.", choices=[],
            effects={"cost": {"electronics_01": 3, "data_chip": 1, "key_card_01": 1}, "reputation": {"indipendenti": -2}, "set_flag": {"sybil_aggro_quest_active": True, "sybil_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="sybil_aggro_n2_fetch", speaker="Sybil", text="[Sbuffa] La tua bava non raffredda i server. Torna con l'hardware e i permessi, o sparisci.", choices=[],
            effects={"set_flag": {"sybil_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="sybil_emp_n2_pay", speaker="Sybil", text="[Sorride, quasi un po' imbarazzata] Grazie... davvero. Li installo subito. Avrete priorità di banda.", choices=[],
            effects={"ethics": +4, "reputation": {"indipendenti": +10}, "cost": {"electronics_01": 3, "data_chip": 1, "key_card_01": 1}, "set_flag": {"sybil_emp_quest_active": True, "sybil_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="sybil_emp_n2_fetch", speaker="Sybil", text="[Si strofina gli occhi stanchi sotto le lenti] Riposare... il mio sistema va in kernel panic se provo a chiudere gli occhi. Temo sempre che, al riavvio, non ci sia più nulla. Trovate i 3 Componenti, il Chip e il Badge e portatemeli. È l'unico workaround valido.", choices=[],
            effects={"set_flag": {"sybil_emp_quest_active": True}, "ethics": +2, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="sybil_prag_n2_info", speaker="Sybil", text="[Sbuffando leggermente] Nessuna versione trial. La mia larghezza di banda non è in prova gratuita per i passanti. Fai l'upload fisico sulla mia scrivania di quei componenti e del badge, poi avrai il tuo ping di conferma.", choices=scelte_prag_fase_3,
            effects={"info_shared": "dannati_codes", "set_flag": {"sybil_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="sybil_prag_n2_alternative", speaker="Sybil", text="[Il riflesso verde del codice sui suoi occhiali] Dati corrotti in partenza. I tuoi codici hanno un ottimo valore di mercato, ma non sostituiscono una scheda madre bruciata. La richiesta di sistema non ammette override: portami i 3 Componenti Hardware, il Chip e il Badge, o la transazione viene annullata.", choices=scelte_prag_fase_3,
            effects={"info_shared": "dannati_codes", "set_flag": {"sybil_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_diplo_n2_trade", speaker="Sybil", text="[Apre un terminale di log] I dati di ricognizione sarebbero un'ottima integrazione, ma non ho slot di memoria. Senza i Componenti Hardware e il Chip Dati, non posso espandere i nodi. Risolvete il collo di bottiglia hardware e accetterò i vostri dati.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"sybil_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="sybil_diplo_n2_crypto", speaker="Sybil", text="[Mostra un messaggio d'errore in rosso] La creazione di nuovi canali sicuri richiede cicli di calcolo che i miei processori attuali non possono sostenere senza fondersi. Trovate i 3 Componenti, il Chip e il Badge. Solo allora potrò allocare le risorse necessarie.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"sybil_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_aggro_n2_intimidate", speaker="Sybil", text="[Sbadigliando leggermente] Algoritmo di minaccia obsoleto. Prima di riuscire a toccarmi, avrei già cancellato la tua esistenza digitale. Sei solo un bug nel sistema. O mi consegni l'hardware, il chip e il badge, o la tua sessione scade qui.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"sybil_aggro_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="sybil_aggro_n2_force", speaker="Sybil", text="[Digitando furiosamente] Hardware secondario distrutto. Calcolo del danno: irrilevante. Stai solo aumentando il tuo debito nei miei confronti. Portami 3 Componenti Hardware, il Chip e il Badge, oppure vattene prima che decida di attivare la pulizia del vicolo.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"sybil_aggro_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_emp_n2_care", speaker="Sybil", text="[La voce le trema per un istante] Le macchine... non mi tradiscono. Non hanno secondi fini. Ma se i server si spengono, io... resto al buio. Da sola. [Chiude gli occhi con forza] L'empatia non raffredda i miei circuiti logici! Se volete salvarmi, procuratemi quei Componenti, il Chip e il Badge.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"sybil_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="sybil_emp_n2_work", speaker="Sybil", text="[Le dita che accarezzano la scocca calda di un server] Questa rete è l'unica prova che esisto ancora. Se cade il segnale, io sparisco. [Deglutisce a fatica] Il mio hardware sta registrando danni termici critici. Ho bisogno di un intervento fisico. Portatemi i Componenti, il Chip e il Badge, o andremo comunque offline.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"sybil_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_prag_n3_deal", speaker="Sybil", text="[Premendo il tasto Invio con un colpo secco, lo sguardo fisso sui monitor] Query in standby. Sessione messa in pausa per timeout in attesa di input fisico esterno. Il server aspetta la tua consegna, non metterci troppo o il sistema andrà in ibernazione. Log out.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"sybil_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_diplo_n3_thanks", speaker="Sybil", text="[Digita un comando finale, bloccando la schermata sulla dashboard principale] Protocollo di intesa registrato. I vostri permessi di accesso resteranno nello stato 'In attesa di convalida' fino al rilevamento dei materiali. Non deludete le aspettative del sistema: la vostra priorità è la consegna. Buona ricerca.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"sybil_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_aggro_n3_leave", speaker="Sybil", text="[Torna a fissare i monitor, il rumore dei tasti riprende come una mitragliatrice] Sessione in standby. Vi terrò monitorati tramite ogni singola telecamera di sorvallo finché non sarete di ritorno. Non tentate di bypassare il protocollo: senza i Componenti Hardware e il Badge, non c'è salvezza. Disconnessione in corso.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"sybil_aggro_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_emp_n3_care", speaker="Sybil", text="[Un piccolo, esitante sorriso le ammorbidisce per una frazione di secondo le occhiaie profonde. Sussurra a bassa voce] Io... grazie. Fate attenzione là fuori, non voglio perdere la mia unica... [Si interrompe bruscamente, tornando a fissare lo schermo con fare professionale] E-ehm. Connessione in standby. Il sistema vi attende.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"sybil_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="sybil_eval_walk_away", speaker="Sybil", text="Connessione abortita.", choices=[], effects={"end": True, "combat_avoided": True}))

        return tree

    @staticmethod
    def build_rael() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Rael")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        fucile_posseduto = count_item("heavy_rifle_01")

        q_prag  = gs.flags.get("rael_prag_quest_active", False)
        q_diplo = gs.flags.get("rael_diplo_quest_active", False)
        q_aggro = gs.flags.get("rael_aggro_quest_active", False)
        q_emp   = gs.flags.get("rael_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("rael_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Rael",
                    text="Mi hai pagato in pieno. La via nei vicoli a est è libera da trappole, muovetevi sicuri.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "L'affare era di un fucile per le chiavi dei cancelli. Ce l'hai?"
            elif q_diplo:
                greeting = "Aspettavo di rivedervi. La strada è pronta ma mi serve il fucile che avevamo pattuito."
            elif q_aggro:
                greeting = "[Trasalice] Siete voi... Ho preparato la strada, vi darò le chiavi. Ma mi serve l'arma, vi prego."
            elif q_emp:
                greeting = "[Si illumina] Ehi, siete tornati per davvero. Avete trovato il fucile per aiutarmi?"
            else:
                greeting = "Senza il fucile, non vi aprirò la via."

            if fucile_posseduto >= 1:
                scelte_ritorno = [("«Ecco l'arma. Mostraci la via.»", "rael_standby_pay")]
            else:
                scelte_ritorno = [("«Lo sto cercando. Tornerò a prendere le chiavi.»", "rael_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Rael", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="rael_standby_wait", speaker="Rael",
                text="Vi aspetterò... ma non metteteci troppo, i Razziatori pattugliano spesso qui.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="rael_standby_pay", speaker="Rael",
                text="[Prende il fucile con avidità] Bellissimo! Grazie. Prendete questa mappa, i vicoli ovest sono puliti.",
                choices=[], effects={
                    "cost": {"heavy_rifle_01": 1},
                    "set_flag": {"rael_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"indipendenti": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if fucile_posseduto >= 1:
            scelte_prag_fase_2.append(("«Consideralo un contratto a senso unico. Noi ora ti diamo l'arma, tu fornisci un percorso aggiornato. Esigo l'assoluta qualità.»", "rael_prag_n2_pay", {"ethics": 0, "reputation": {"indipendenti": +1}}))
            scelte_diplo_fase_2.append(("«Rispettiamo i patti. Abbiamo l'arma, usala per sbloccarci la via sicura come promesso.»", "rael_diplo_n2_pay", {"ethics": +1, "reputation": {"indipendenti": +2}}))
            scelte_aggro_fase_2.append(("«Ecco il tuo fucile. Ora non hai più scuse, tiraci fuori da questa fogna immediatamente.»", "rael_aggro_n2_pay", {"ethics": -2, "reputation": {"indipendenti": -1}}))
            scelte_emp_fase_2.append(("«Prendi questo fucile. Usalo per proteggerti e aprici la strada. Non devi più avere paura.»", "rael_emp_n2_pay", {"ethics": +2, "reputation": {"indipendenti": +3}}))
        else:
            scelte_prag_fase_2.append(("«Consideralo un contratto a senso unico. Noi ti forniremo l'arma, tu fornisci un percorso aggiornato. Esigo l'assoluta qualità.»", "rael_prag_n2_fetch", {"ethics": 0}))
            scelte_diplo_fase_2.append(("«Non abbiamo quest'arma con noi, ma vi diamo la parola che la cercheremo per aiutarvi.»", "rael_diplo_n2_fetch", {"ethics": +1, "reputation": {"indipendenti": +1}}))
            scelte_aggro_fase_2.append(("«Vado a prendertelo, ma se scopro che mi hai mentito ti stacco le braccia.»", "rael_aggro_n2_fetch", {"ethics": -2, "reputation": {"indipendenti": -2}}))
            scelte_emp_fase_2.append(("«Faremo noi il lavoro sporco. Tu rimani qui nascosto al sicuro, ci penseremo noi a cercare questo fucile.»", "rael_emp_n2_fetch", {"ethics": +2, "reputation": {"indipendenti": +2}}))

        scelte_prag_fase_2.extend([
            ("«Ti porteremo il fucile. Ma vedi di non fare scherzi con quella mappa, o torneremo a chiederti il rimborso con gli interessi.»", "rael_prag_n2_quality", {"ethics": -1}),
            ("«Le armi scarseggiano. Ti offro un'alternativa: le coordinate precise di un rifugio non ancora saccheggiato. Vale molto di più di un fucile.»", "rael_prag_n2_alternative", {"reputation": {"indipendenti": -1}}),
            ("«[Ignora e allontanati]»", "rael_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Se il problema sono gli ostacoli, potremmo semplicemente prendere una via più esposta facendoti da scorta armata e proteggendoti.»", "rael_diplo_n2_trade", {"ethics": +1, "reputation": {"indipendenti": +1}}),
            ("«Aiutaci a passare ora, e ti offriremo molto di più di un baratto. Ti garantiamo l'accesso al nostro rifugio sicuro e una quota fissa di scorte.»", "rael_diplo_n2_ally", {"ethics": +2, "reputation": {"indipendenti": +2}}),
            ("«[Ignora e allontanati]»", "rael_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Sei solo un rammollito. Se c'è una grata, la sfondo a calci o ci penso io a spaccarla. Tu cammina e tieni la bocca chiusa.»", "rael_aggro_n2_intimidate", {"ethics": -3, "reputation": {"indipendenti": -3}}),
            ("«[Premendo la canna dell'arma contro la sua fronte] Le tue scuse patetiche non mi interessano. Trova un modo di aprirla o il tuo cervello farà un disegno sul muro.»", "rael_aggro_n2_weapon", {"ethics": -4, "reputation": {"indipendenti": -4}, "combat_risk": 0.05}),
            ("«[Ignora e allontanati]»", "rael_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Rael, come hai fatto a resistere da solo in questo inferno per tutto questo tempo? Non devi portare un fardello così pesante tutto da solo.»", "rael_emp_n2_past", {"ethics": +2, "reputation": {"indipendenti": +2}}),
            ("«Se è troppo pericoloso per te o non ti senti in forze, non sforzarti. Troveremo un'altra strada, non vogliamo assolutamente che tu rischi la vita.»", "rael_emp_n2_rass", {"ethics": +3, "reputation": {"indipendenti": +3}}),
            ("«[Ignora e allontanati]»", "rael_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Resta nascosto e aspettaci esattamente qui, andiamo a cercare la tua roba.»", "rael_prag_n3_deal", {"ethics": 0}),
            ("«Nessun trucco, torniamo presto. Tieni pronta quella mappa per quando avremo il fucile.»", "rael_prag_n3_deal", {"ethics": -1}),
            ("«Accettiamo lo scambio. Non sparire, andiamo a recuperare il pagamento.»", "rael_prag_n3_deal", {"ethics": 0}),
        ]

        scelte_diplo_fase_3 = [
            ("«La tua logica è ineccepibile. Rispettiamo i termini del contratto: cercheremo il fucile e te lo porteremo.»", "rael_diplo_n3_thanks", {"ethics": +1}),
            ("«Abbiamo un accordo, Rael. Aspettaci al sicuro in questa zona, noi andiamo a procurare il materiale necessario.»", "rael_diplo_n3_truce", {"ethics": +1}),
            ("«Affare fatto. Consideraci i tuoi fornitori di fiducia per oggi. Torneremo con il fucile il prima possibile.»", "rael_diplo_n3_thanks", {"ethics": +1})
        ]

        scelte_aggro_fase_3 = [
            ("«Resta esattamente dove sei. Vado a cercare questa roba, ma se provi a scappare, ti trovo e ti spacco le gambe.»", "rael_aggro_n3_leave", {"ethics": -2, "reputation": {"indipendenti": -2}}),
            ("«Vado a prendere questo fucile. Se scopro che è una trappola per farci sbranare, tornerò solo per farti saltare il cranio.»", "rael_aggro_n3_leave", {"ethics": -2, "reputation": {"indipendenti": -2}}),
            ("«Piantala di frignare e resta giù. Torno subito. Muovi un solo muscolo e sei un uomo morto.»", "rael_aggro_n3_leave", {"ethics": -3, "reputation": {"indipendenti": -2}})
        ]

        scelte_emp_fase_3 = [
            ("«Nasconditi bene e riposati, Rael. Torneremo noi con il fucile, te lo prometto.»", "rael_emp_n3_care", {"ethics": +2}),
            ("«Non ti succederà nulla finché ci siamo noi. Aspettaci esattamente qui, non ti abbandoniamo.»", "rael_emp_n3_care", {"ethics": +2}),
            ("«Sei al sicuro con noi adesso. Raccogli le forze, andiamo a cercare quella roba e poi ce ne andiamo tutti insieme.»", "rael_emp_n3_care", {"ethics": +3}),
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Conosci queste strade. A noi serve una via d'uscita sicura, a te servono risorse per sopravvivere. Fai il tuo prezzo e chiudiamola qui.»", "rael_prag_n1_direct", {"ethics": 0, "reputation": {"indipendenti": +1}}),
                     ("«Il tempo è vitale e non voglio sprecarlo a girare a vuoto. Voglio comprare un percorso pulito per attraversare questo settore. Qual è la tariffa?»", "rael_prag_n1_direct", {"ethics": -1, "reputation": {"indipendenti": +1}}),
                     ("«Risparmiati i convenevoli e i nascondigli. Cerchiamo una mappa affidabile. Dicci subito cosa vuoi in cambio e facciamo affari.»", "rael_prag_n1_direct", {"ethics": 0})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«[Mani in vista, voce calma] Salve. Sappiamo che conosci questi vicoli. Non vogliamo guai, cerchiamo solo una guida esperta e pagheremo per i tuoi servizi.»", "rael_diplo_n1_civic", {"ethics": +2, "reputation": {"indipendenti": +2}}),
                     ("«[Annuendo con rispetto] Deve essere dura sopravvivere da soli qui fuori. Noi abbiamo bisogno di una rotta sicura, tu di risorse. Proponiamo un accordo.", "rael_diplo_n1_civic", {"ethics": +1, "reputation": {"indipendenti": +1}}),
                     ("«[Tono professionale e rilassato] Abbiamo sentito parlare della tua abilità nel muoverti non visto. Quali sono i tuoi termini per farci da guida?»", "rael_diplo_n1_civic", {"ethics": +1, "reputation": {"indipendenti": +1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Afferrandolo per il bavero, sbattendolo contro il muro] Smettila di strisciare, parassita! Portaci fuori da questo labirinto senza farci saltare in aria o ti stacco la testa.»", "rael_aggro_n1_head", {"ethics": -3, "reputation": {"indipendenti": -3}}),
                     ("«[Puntandogli l'arma in faccia a bruciapelo] Niente chiacchiere, topo di fogna. Fai strada verso l'uscita, e se incrociamo brutte sorprese il primo a prendersi una pallottola sei tu.»", "rael_aggro_n1_head", {"ethics": -4, "reputation": {"indipendenti": -4}}),
                     ("«[Spingendolo a terra con uno stivale sul petto] Sputa il rospo su come attraversare il settore in sicurezza. Se c'è una fottuta trappola, ti ci butto dentro a calci.»", "rael_aggro_n1_head", {"ethics": -4, "reputation": {"indipendenti": -3}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«[Mani bene in vista, voce calda e rassicurante] Ehi, tranquillo... non vogliamo farti del male. Sembri affamato ed esausto, c'è qualcosa che possiamo fare per aiutarti?»", "rael_emp_n1_care", {"ethics": +3, "reputation": {"indipendenti": +3}}),
                     ("«[Facendo un passo indietro per non spaventarlo, tono dolce] Respira a fondo, sei al sicuro con noi. Deve volerci un coraggio immenso per sopravvivere da soli. Stai bene?", "rael_emp_n1_care", {"ethics": +2, "reputation": {"indipendenti": +2}}),
                     ("«[Accucciandosi per essere al suo stesso livello, voce protettiva] Nessuno ti farà più del male oggi, te lo prometto. Come ti chiami? Siediti un momento e riposati.»", "rael_emp_n1_care", {"ethics": +3, "reputation": {"indipendenti": +2}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Rael", text="[Balza fuori da un cumulo di macerie] Ehi! Ehi, non sparate! Sono solo uno scavenger... ma conosco queste strade meglio di chiunque altro.",
            choices=[
                ("«[Rivet] Una guida? Dimmi quanto vuoi.»", "rael_prag_n1_direct"),
                ("«[Rivet] Sputa fuori le info, randagio, o ti pesto.»", "rael_aggro_n1_head"),
                ("«[Echo] Cerchiamo una via sicura, ci serve una mano.»", "rael_diplo_n1_civic"),
                ("«[Echo] Sembri spaventato. Non ti faremo del male.»", "rael_emp_n1_care")
            ]))

        tree.add_node(DialogueNode(node_id="rael_prag_n1_direct", speaker="Rael", text="[Sbuca da dietro un cassonetto arrugginito, guardandosi freneticamente a destra e a sinistra] Occhi vispi, eh? Sì, sì... ho una mappa. Vie pulite, zero azzannatori, zero pattuglie grosse. Ma le mie informazioni non sono gratis. Ho adocchiato il grattacielo nel centro città ma non posso arrivarci. Portatemi il fucile all'interno della cassaforte e la mappa è vostra. Baratto secco, niente sconti.", choices=scelte_prag_fase_2, effects={"reputation": {"indipendenti": +1}}))

        tree.add_node(DialogueNode(node_id="rael_diplo_n1_civic", speaker="Rael", text="[Emerge lentamente dall'ombra, sorpreso. Abbassa le spalle tese e si schiarisce la voce, assumendo un'aria quasi professionale] Nessuno mi parla mai in questo modo... di solito mi puntano un ferro in faccia e basta. Apprezzo i modi civili, davvero. E sì, avete trovato l'uomo giusto. Ho mappato una via sicura, zero infetti e zero pattuglie. Ma c'è un ostacolo logistico per cui mi serve il vostro aiuto: la via passa per i vecchi tunnel di manutenzione, sbarrati da grate arrugginite. Per darvi la mappa ho bisogno del fucile all'interno della cassaforte nel Grattacielo. Questo è il prezzo per il biglietto.", choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="rael_aggro_n1_head", speaker="Rael", text="[Si rannicchia terrorizzato, alzando le mani tremanti per coprirsi il viso e balbettando] Non sparate! Non fatemi male, vi prego, vi supplico! V-vi faccio strada, conosco i vicoli ciechi, conosco tutto! Ma... ma c'è un problema, non è colpa mia! La via sicura è sbarrata da grate di ferro e lucchetti arrugginiti! A mani nude non le apre nessuno, nemmeno voi! Voglio il fucile nel grattacielo per smontarvi i cardini, o saremo solo carne morta in un vicolo cieco!", choices=scelte_aggro_fase_2, effects={"ethics": -3, "reputation": {"indipendenti": -5}}))

        tree.add_node(DialogueNode(node_id="rael_emp_n1_care", speaker="Rael", text="[Sgrana gli occhi, arretrando per abitudine prima di bloccarsi. Si guarda attorno, sbalordito, e la sua voce trema] Voi... non volete derubarmi? Non mi avete chiamato parassita... io... mi chiamo Rael. G-grazie, grazie mille. Siete anime buone in un mondo cattivo. Vorrei tanto aiutarvi! Conosco una via sicura per uscire da qui, lontana dai morti e dai banditi. Vorrei farvi da guida per sdebitarmi della vostra gentilezza, davvero! Ma... [abbassa lo sguardo, profondamente dispiaciuto] la strada passa per i vecchi condotti. Ci sono delle grate bloccate, e io potrei pure apriverle ma per sopravvivere ho bisogno di un'arma di cui ho sentito parlare. La cassaforte in centro città, all'interno del Grattacielo, portatemelo", choices=scelte_emp_fase_2, effects={"ethics": +2, "reputation": {"indipendenti": +3}}))

        tree.add_node(DialogueNode(node_id="rael_prag_n2_pay", speaker="Rael", text="[Prende il fucile] Contratto, eh? Parlate come i tizi in giacca e cravatta di prima del crollo. La mappa è perfetta, aggiornata a stamattina. Eccola.", choices=[],
            effects={"cost": {"heavy_rifle_01": 1}, "reputation": {"indipendenti": +3}, "set_flag": {"rael_prag_quest_active": True, "rael_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="rael_prag_n2_fetch", speaker="Rael", text="[Sogghigna mostrando denti ingialliti, stringendosi nelle spalle] Contratto, eh? Parlate come i tizi in giacca e cravatta di prima del crollo. La mappa è perfetta, aggiornata a stamattina. Ma i contratti si chiudono con la merce giusta in mano. Risparmia i discorsi e portatemi quel fottuto fucile. Solo quelli aprono la grata, e solo quelli vi daranno il lasciapassare.", choices=[],
            effects={"set_flag": {"rael_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="rael_diplo_n2_pay", speaker="Rael", text="[Afferra l'arma con deferenza] Rispettate i patti, siete persone perbene. Ecco la via sicura che vi avevo promesso, la mappa è chiara.", choices=[],
            effects={"cost": {"heavy_rifle_01": 1}, "reputation": {"indipendenti": +4}, "set_flag": {"rael_diplo_quest_active": True, "rael_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="rael_diplo_n2_fetch", speaker="Rael", text="[Annuisce mestamente] Non dubito di voi, ma senza fucile le grate restano chiuse. Cercatelo. Vi aspetterò.", choices=[],
            effects={"set_flag": {"rael_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="rael_aggro_n2_pay", speaker="Rael", text="[Prende l'arma tremando] V-va bene! Tieni, ecco la mappa! Potete usarla per uscire da qui, vi giuro che è pulita!", choices=[],
            effects={"cost": {"heavy_rifle_01": 1}, "reputation": {"indipendenti": -2}, "set_flag": {"rael_aggro_quest_active": True, "rael_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="rael_aggro_n2_fetch", speaker="Rael", text="[Indietreggia coprendosi la testa] Vi prego, non fatemi male! Ma senza quell'arma siamo tutti morti, non posso farci niente!", choices=[],
            effects={"set_flag": {"rael_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="rael_emp_n2_pay", speaker="Rael", text="[Piange stringendo il fucile] Nessuno è mai stato così gentile con me nella Zona. Siete... eroi. Vi guiderò ovunque con questa mappa.", choices=[],
            effects={"ethics": +5, "reputation": {"indipendenti": +15}, "cost": {"heavy_rifle_01": 1}, "set_flag": {"rael_emp_quest_active": True, "rael_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="rael_emp_n2_fetch", speaker="Rael", text="[Si porta le mani al petto, visibilmente commosso da tanta premura] Voi fareste questo... per me? Per uno scarto come me? [Una lacrima gli riga il viso incrostato di polvere] Ho sempre tanta paura quando esco... ma se restate qui fuori troppo a lungo, vi faranno del male. Voglio portarvi al sicuro nel tunnel, ma la triste verità è che la porta resterà sbarrata finché non avrò quel fucile. È l'unico modo per salvarci tutti.", choices=[],
            effects={"set_flag": {"rael_emp_quest_active": True}, "ethics": +2, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="rael_prag_n2_quality", speaker="Rael", text="[Scatta nervosamente indietro di mezzo passo, alzando le mani callose] Ehi, niente minacce! Rael vende solo roba buona, le fregature fanno male alla salute. Ma le garanzie si danno dopo il pagamento. Niente fucile, niente vie sicure. Volete la mia mappa? Trovate quel fucile, fine della storia. È l'unica via.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"rael_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="rael_prag_n2_alternative", speaker="Rael", text="[Sputa a terra, scuotendo la testa con urgenza] Coordinate? Chiacchiere! Le coordinate sono solo un invito a farsi sbranare se non hai gli strumenti per aprire le porte bloccate! Devo spaccare del metallo oggi, non ascoltare le tue storie. L'offerta non cambia: un fucile in cambio della mappa. Prendere o lasciare, altrimenti me ne vado.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"rael_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_diplo_n2_trade", speaker="Rael", text="[Scuote la testa con un sorriso gentile ma fermo] Non dubito delle vostre capacità in combattimento, amici. Ma una sparatoria attira le orde, e i proiettili finiscono sempre prima dei mostri. La via sicura è l'unica opzione logica per restare vivi. Purtroppo, la buona volontà non fa sparire l'acciaio: se non mi procurate quel fucile, i tunnel restano chiusi.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"rael_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="rael_diplo_n2_ally", speaker="Rael", text="[Gli brillano gli occhi, visibilmente commosso dalla proposta, ma poi si stringe nelle spalle] Un rifugio sicuro... è l'offerta migliore che abbia ricevuto in anni. Siete brave persone. Ma un bellissimo futuro non ci aiuta a superare un muro nel presente. Anche se ora siamo alleati, io non posso attraversare il metallo solido. Per iniziare questa nostra collaborazione, mi serve comunque quel fucile oggi.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"rael_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_aggro_n2_intimidate", speaker="Rael", text="[Piagnucolando e scuotendo la testa freneticamente, sudando freddo] No, no, siete pazzi! È acciaio massiccio rinforzato! Fareste un baccano infernale, attirereste ogni singolo morto o razziatore nel raggio di un chilometro! Vi supplico, non uccideteci tutti! Lasciate fare a me, sono l'unico che sa aprirle in silenzio, ma vi prego... cercatemi quel maledetto fucile!", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"rael_aggro_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="rael_aggro_n2_weapon", speaker="Rael", text="[Tremando in modo incontrollabile, stridendo con un filo di voce] A-allora premete il grilletto! Perché non p-piegherò il ferro con le mani! Anche se mi ammazzate qui come un cane, la via resterà bloccata per sempre! S-sono l'unica speranza che avete di passare in silenzio... risparmiatemi, vi imploro! Trovate questo dannato fucile e vi tiro fuori di qui vivi, è l'unico modo!", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"rael_aggro_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_emp_n2_past", speaker="Rael", text="[Sorride timidamente per la prima volta, accarezzandosi un braccio pieno di lividi] Io... mi nascondo. Cerco di farmi piccolo, di diventare invisibile. Ma la solitudine ti divora da dentro, sapete? A volte speravo di non svegliarmi più. Voi siete la cosa più bella che mi sia successa da anni e... non voglio che moriate per colpa mia! Vorrei aprirvi quella via s-subito, ma ho le mani deboli e la ruggine è spessa. Lasciatemi riposare mentre mi portate quel maledetto fucile. Vi prego, dovete aiutarmi a trovarli.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"rael_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="rael_emp_n2_rass", speaker="Rael", text="[Scuote la testa con foga, con gli occhi lucidi e la voce rotta] No, no! Le altre strade sono trappole mortali, vi farebbero a pezzi! Per una volta che trovo qualcuno gentile... non voglio vedervi morire. Guidarvi non mi fa paura, ma... ma sono un debole. Senza il fucile non aprirò mai quelle inferriate. Vi prego, fatemi essere utile, datemi il modo di farvi passare.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"rael_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_prag_n3_deal", speaker="Rael", text="[Annuisce rapidamente, arretrando fino a fondersi di nuovo con le ombre del vicolo] Rael non sparisce mai se c'è un affare in sospeso. Occhi aperti là fuori, la città morde. E fate in fretta... o vendo la rotta al prossimo disperato che passa di qui.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"rael_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_diplo_n3_thanks", speaker="Rael", text="[Annuisce con un sorriso sollevato, facendo un piccolo e formale cenno del capo prima di arretrare nell'ombra] Un piacere fare affari con voi. Mi nasconderò qui vicino, terremo un basso profilo finché non tornate. Fate attenzione là fuori... e buona ricerca. Vi aspetto.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"rael_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_aggro_n3_leave", speaker="Rael", text="[Rannicchiandosi in posizione fetale contro dei bidoni incrostati, annuendo compulsivamente con le mani sulla testa] Non mi muovo! Non respiro neanche! Sono un sasso, un'ombra, non mi vede nessuno! Vi aspetto qui, non scappo, lo giuro sulla mia stessa vita! Fate in fretta, per pietà, fate in fretta!", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"rael_aggro_quest_active": True}, "combat_risk": 0.15}))

        tree.add_node(DialogueNode(node_id="rael_emp_n3_care", speaker="Rael", text="[Annuisce asciugandosi velocemente il viso con la manica consunta, guardando i giocatori con un misto di immensa speranza e adorazione] Io... io non mi muovo di un millimetro, lo giuro! Mi rintano qui, sarò silenzioso come un topo. Fate molta attenzione là fuori, vi prego. Vi aspetterò... non vi abbandono, è una promessa.", choices=[], effects={"end": True, "combat_avoided": True, "set_flag": {"rael_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="rael_eval_walk_away", speaker="Rael", text="[Si nasconde di nuovo] Meglio così...", choices=[], effects={"end": True, "combat_avoided": True}))

        return tree

class RazziatorDialogues:

    @staticmethod
    def build_scar() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Scar")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        razioni_possedute = count_item("food_01")
        scatole_possedute = count_item("food_02")

        ha_i_requisiti = razioni_possedute >= 20 and scatole_possedute >= 10

        q_prag  = gs.flags.get("scar_prag_quest_active", False)
        q_diplo = gs.flags.get("scar_diplo_quest_active", False)
        q_aggro = gs.flags.get("scar_aggro_quest_active", False)
        q_emp   = gs.flags.get("scar_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("scar_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Scar",
                    text="Il pedaggio è pagato e i miei uomini hanno la pancia piena. Godetevi il passaggio finché dura.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "Il nostro accordo commerciale è ancora aperto. Hai portato le 20 razioni e le 10 scatolette?"
            elif q_diplo:
                greeting = "La nostra tregua temporanea regge. Ma ho bisogno di quelle 20 razioni e 10 scatolette. Le hai?"
            elif q_aggro:
                greeting = "Avete fegato a tornare qui. Spero per voi che abbiate tutto quel cibo, prima che i miei perdano la pazienza."
            elif q_emp:
                greeting = "I miei uomini hanno fame e io mi sono fidato di voi. Avete trovato le razioni e le scatolette?"
            else:
                greeting = "Non ho tempo da perdere. Hai portato il cibo che ho chiesto?"

            if ha_i_requisiti:
                scelte_ritorno = [("«Sì, ecco le 20 razioni e le 10 scatolette. Prendile.»", "scar_standby_pay")]
            else:
                scelte_ritorno = [("«Non ancora. Le sto cercando, dammi tempo.»", "scar_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Scar", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="scar_standby_wait", speaker="Scar",
                text="Allora sparisci dalla mia vista prima che ti spari. Torna solo quando avrai il cibo.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="scar_standby_pay", speaker="Scar",
                text="[Ispeziona il cibo e lo intasca] Affare concluso. La strada è libera.",
                choices=[], effects={
                    "cost": {"food_01": 20, "food_02": 10},
                    "set_flag": {"scar_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"razziatori": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«È un investimento pesante ma possiamo darvi le 20 razioni e le 10 scatolette subito.»", "scar_prag_n2_pay", {"ethics": +1, "reputation": {"razziatori": +2}}))
            scelte_diplo_fase_2.append(("«Siamo disposti a versare queste provviste per mantenere la tregua. Ecco il cibo.»", "scar_diplo_n2_pay", {"ethics": +2, "reputation": {"razziatori": +2}}))
            scelte_aggro_fase_2.append(("«Prendi il tuo maledetto cibo e ordina ai tuoi di abbassare le armi, subito.»", "scar_aggro_n2_pay", {"ethics": -2, "reputation": {"razziatori": +1}}))
            scelte_emp_fase_2.append(("«I tuoi ragazzi sono feriti e affamati. Lascia che vi aiuti per il semplice fatto che ne avete bisogno.»", "scar_emp_n2_pay", {"ethics": +3, "reputation": {"razziatori": +3}}))
        else:
            scelte_prag_fase_2.append(("«Tutto questo cibo è un dazio pesante e non l'abbiamo. Possiamo andare a cercarlo.»", "scar_prag_n2_fetch", {"ethics": 0}))
            scelte_diplo_fase_2.append(("«Non abbiamo così tanto cibo, ma vi diamo la nostra parola che lo cercheremo.»", "scar_diplo_n2_fetch", {"ethics": +1}))
            scelte_aggro_fase_2.append(("«Non ho 30 fottuti pezzi di cibo con me. Vado a prenderli, ma tieni buoni i tuoi cani intanto.»", "scar_aggro_n2_fetch", {"ethics": -1, "reputation": {"razziatori": -1}}))
            scelte_emp_fase_2.append(("«Non andrò a cercare tutto questo per pagarti un pedaggio, lo farò perché i tuoi ragazzi hanno fame.»", "scar_emp_n2_fetch", {"ethics": +2}))

        scelte_prag_fase_2.extend([
            ("«Ho visto i movimenti dei Solidali due isolati a est. Un'informazione del genere vale bene uno sconto sulla tariffa, no?»", "scar_prag_n2_info", {"ethics": -2, "reputation": {"razziatori": +2, "solidali": -3}}),
            ("«Siamo solo l'avanguardia di un gruppo numeroso. Se non ci lasciate passare, lo considereremo un atto ostile.»", "scar_prag_n2_bluff", {"reputation": {"razziatori": -1}}),
            ("«[Ignora e allontanati]»", "scar_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Siamo persone di parola. Se ci lasciate passare ora, potremmo stabilire una rotta commerciale molto redditizia.»", "scar_diplo_n2_med", {"ethics": +1, "reputation": {"razziatori": +1}}),
            ("«Uno scontro qui danneggerebbe entrambi. Voi perdereste uomini e munizioni. Non ha più senso un accordo?»", "scar_diplo_n2_trade", {"ethics": +1}),
            ("«[Ignora e allontanati]»", "scar_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Posso ucciderti prima che i tuoi ragazzi capiscano. Vuoi davvero morire per della carne in scatola?»", "scar_aggro_n2_intimidate", {"ethics": -2, "reputation": {"razziatori": -1}}),
            ("«[Estrae una granata] Scommettiamo che se salto in aria io, saltate tutti voi? Facci passare o facciamo il botto.»", "scar_aggro_n2_grenade", {"ethics": -3, "reputation": {"razziatori": +1}}),
            ("«[Ignora e allontanati]»", "scar_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Insegnavi? Deve essere devastante aver visto bruciare il mondo che conoscevi, e i tuoi studenti armati.»", "scar_emp_n2_past", {"ethics": +2, "reputation": {"razziatori": +2}}),
            ("«Guardaci. Siamo tutti sopravvissuti. Abbassiamo le armi, ti prego. Nessuno di noi deve morire oggi.»", "scar_emp_n2_trust", {"ethics": +2, "reputation": {"razziatori": +1}}),
            ("«[Ignora e allontanati]»", "scar_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Le cercheremo e torneremo qui con il carico.»", "scar_prag_n3_deal", {"ethics": 0}),
            ("«Le troveremo, ma vedi di tenere i tuoi uomini pronti ad aprire il cancello al nostro arrivo.»", "scar_prag_n3_deal", {"ethics": -1}),
            ("«Tutto questo cibo per la nostra pelle. È un prezzo accettabile per ora. Aspettateci.»", "scar_prag_n3_deal", {"ethics": 0})
        ]

        scelte_diplo_fase_3 = [
            ("«Rispettiamo le vostre regole e la vostra posizione. Cercheremo il cibo e torneremo per lo scambio.»", "scar_diplo_n3_thanks", {"ethics": +1}),
            ("«È un prezzo alto, ma equo per la sicurezza che offrite. Troveremo le scorte, mantenete la tregua.»", "scar_diplo_n3_thanks", {"ethics": +1}),
            ("«Accettiamo i termini. Considerateci partner commerciali temporanei.»", "scar_diplo_n3_thanks", {"ethics": +1})
        ]

        scelte_aggro_fase_3 = [
            ("«Andiamo a prendere il tuo maledetto cibo. Ma non voltare le spalle quando torniamo, professore.»", "scar_aggro_n3_leave", {"ethics": -1, "reputation": {"razziatori": +1}}),
            ("«D'accordo, tregua armata. Avrai le razioni, ma solo perché oggi non ho voglia di sporcarmi gli stivali.»", "scar_aggro_n3_leave", {"ethics": -2}),
            ("«Consideralo un investimento. Ti porterò le razioni, ma la prossima volta non sarò così paziente.»", "scar_aggro_n3_leave", {"ethics": -1})
        ]

        scelte_emp_fase_3 = [
            ("«Resistete ancora un po'. Non vi lasceremo qui a morire. Troveremo quello di cui avete bisogno.»", "scar_emp_n3_care", {"ethics": +2}),
            ("«Abbi cura della tua gente, professore. Ti do la mia parola: torneremo con il cibo.»", "scar_emp_n3_care", {"ethics": +1}),
            ("«Non devi fidarti di me o credere nei miracoli. Sopravvivete fino al nostro ritorno. È una promessa.»", "scar_emp_n3_care", {"ethics": +2})
        ]

        tree.add_node(DialogueNode(
            node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[
                ("«Siamo qui per passare. Andiamo dritti al punto: qual è il prezzo del pedaggio?»", "scar_prag_n1_direct", {"ethics": -1, "reputation": {"razziatori": +1}}),
                ("«Inutile sprecare proiettili per due viandanti. Diteci cosa volete per lasciarci la strada libera.»", "scar_prag_n1_direct", {"ethics": 0, "reputation": {"razziatori": +1}}),
                ("«Bel posto di blocco, Scar. Immagino che la gestione di questo confine abbia dei costi. Parliamo d'affari.»", "scar_prag_n1_direct", {"ethics": 0}),
            ]
        ))

        tree.add_node(DialogueNode(
            node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[
                ("«Non siamo qui per cercare guai. Vorremmo parlare con chi comanda per trovare una soluzione che benefici entrambi.»", "scar_diplo_n1_civic", {"ethics": +1, "reputation": {"razziatori": -1}}),
                ("«Complimenti per l'organizzazione di questo avamposto. Possiamo discutere i termini per un passaggio sicuro?»", "scar_diplo_n1_civic", {"ethics": +1, "reputation": {"razziatori": +1}}),
                ("«C'è già fin troppa morte là fuori. Preferiremmo negoziare un accordo civile piuttosto che sprecare risorse.»", "scar_diplo_n1_civic", {"ethics": +2, "reputation": {"razziatori": -1}}),
            ]
        ))

        tree.add_node(DialogueNode(
            node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[
                ("«Sposta quel ferro dalla mia vista, Scar, o ti faccio ingoiare ogni singolo dente.»", "scar_aggro_n1_head", {"ethics": -2, "reputation": {"razziatori": +1}}),
                ("«Non abbiamo tempo per i tuoi giochetti da casello. Apri quel cancello o lo sfondo usando la tua testa.»", "scar_aggro_n1_head", {"ethics": -3, "reputation": {"razziatori": +2}}),
                ("«[Mano sulla fondina] Hai troppa confidenza per uno che ha già un mirino puntato sul petto. Facci passare, ora.»", "scar_aggro_n1_head", {"ethics": -2, "reputation": {"razziatori": +1}}),
            ]
        ))

        tree.add_node(DialogueNode(
            node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[
                ("«Siete stanchi, lo vedo dai vostri occhi. Non vogliamo combattere contro chi sta solo cercando di non sparire.»", "scar_emp_n1_pain", {"ethics": +2, "reputation": {"razziatori": -1}}),
                ("«È evidente quanto tieni ai tuoi ragazzi. Parliamone da esseri umani, non deve farsi male nessuno oggi.»", "scar_emp_n1_pain", {"ethics": +2, "reputation": {"razziatori": -2}}),
                ("«Questo mondo ci sta togliendo tutto, e tu porti un peso enorme sulle spalle. Come possiamo aiutarci a vicenda?", "scar_emp_n1_pain", {"ethics": +3, "reputation": {"razziatori": -2}}),
            ]
        ))

        tree.add_node(DialogueNode(
            node_id="root_intercept", speaker="Scar",
            text="Fermi! [Fischia ai suoi] Copertura! Alzate le mani e non fate gesti stupidi. Vi do dieci secondi.",
            choices=[
                ("«[Rivet] Inutile sprecare proiettili per due viandanti. Diteci cosa volete per lasciarci la strada libera.»", "scar_prag_n1_direct"),
                ("«[Rivet] Sposta quel ferro dalla mia vista, Scar, o ti faccio ingoiare ogni singolo dente.»", "scar_aggro_n1_head"),
                ("«[Echo] Non siamo qui per cercare guai. Vorremmo parlare per trovare una soluzione che benefici entrambi.»", "scar_diplo_n1_civic"),
                ("«[Echo] Siete stanchi, lo vedo dai vostri occhi. Non vogliamo combattere contro chi sta solo cercando di non sparire.»", "scar_emp_n1_pain"),
                ("«[Continua a camminare in silenzio]»", "scar_ignore_n2")
            ]
        ))

        tree.add_node(DialogueNode(node_id="scar_prag_n1_direct", speaker="Scar",
            text="La cortesia è un lusso che il vecchio mondo ha portato nella tomba con sé. Qui vige la legge della domanda e dell'offerta. Io offro la vostra sopravvivenza, voi pagate l'affitto della strada. Il prezzo è esploso, abbiamo bisogno di riempire i magazzini: 20 Razioni e 10 Scatole di cibo. Portatemele e le sbarre si alzeranno.",
            choices=scelte_prag_fase_2, effects={"reputation": {"razziatori": +1}}))

        tree.add_node(DialogueNode(node_id="scar_diplo_n1_civic", speaker="Scar",
            text="Un tono misurato... quasi rinfrescante. Ma la cortesia, per quanto apprezzabile, non è una valuta che i miei uomini possono mangiare. La 'tassa di transito' per mantenere questa pace oggi è molto alta: 20 Razioni di cibo e 10 Scatole. Pagate l'obolo e la strada sarà vostra.",
            choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="scar_aggro_n1_head", speaker="Scar",
            text="Ah, l'iperbole. Puoi ringhiare quanto vuoi, ragazzino, ma il rumore non sazia i miei uomini. Se volete passare senza trasformare questo asfalto in un mattatoio, il prezzo per i duri di comprendonio è 20 Razioni e 10 Scatole di cibo. Consideralo un 'contributo' per la vostra sopravvivenza.",
            choices=scelte_aggro_fase_2, effects={"ethics": -1, "reputation": {"razziatori": -2}}))

        tree.add_node(DialogueNode(node_id="scar_emp_n1_pain", speaker="Scar",
            text="Un peso... già. [Sospira, stropicciandosi gli occhi]. Un tempo la cosa più pesante che portavo era una borsa piena di verifiche da correggere. Ma la nostalgia è un lusso. Vuoi aiutare? Dimostralo. I miei ragazzi stanno morendo di fame. Il pedaggio per la strada è dolorosamente alto: 20 Razioni e 10 Scatole di cibo. Niente carità, solo sopravvivenza.",
            choices=scelte_emp_fase_2, effects={"ethics": +2}))

        tree.add_node(DialogueNode(node_id="scar_prag_n2_pay", speaker="Scar",
            text="[Intasca le razioni] Saggio. Molto saggio. Le vostre vite sono salve.",
            choices=[], effects={"cost": {"food_01": 20, "food_02": 10}, "reputation": {"razziatori": +5}, "set_flag": {"scar_prag_quest_active": True, "scar_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="scar_prag_n2_fetch", speaker="Scar",
            text="Non faccio credito. La fame dei miei uomini non aspetta il vostro ritorno. Niente cibo, niente passaggio. Portatemi quelle 20 razioni e le 10 scatole.",
            choices=[], effects={"set_flag": {"scar_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_diplo_n2_pay", speaker="Scar",
            text="[Prende il cibo massiccio] I vostri gesti parlano più forte delle vostre parole, fortunatamente. Via libera.",
            choices=[], effects={"cost": {"food_01": 20, "food_02": 10}, "reputation": {"razziatori": +4}, "set_flag": {"scar_diplo_quest_active": True, "scar_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="scar_diplo_n2_fetch", speaker="Scar",
            text="La parola non sazia lo stomaco di nessuno, 'diplomatico'. Tornate quando avrete l'intero carico.",
            choices=[], effects={"set_flag": {"scar_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_aggro_n2_pay", speaker="Scar",
            text="[Stringe i pugni sulle razioni] Fortunati che ho fame. Sparite prima che i miei fucili si ricordino della vostra arroganza.",
            choices=[], effects={"cost": {"food_01": 20, "food_02": 10}, "reputation": {"razziatori": +3}, "set_flag": {"scar_aggro_quest_active": True, "scar_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="scar_aggro_n2_fetch", speaker="Scar",
            text="[Ride] Andate a cercarle. E non inciampate sui vostri stessi stivali, cani sciolti.",
            choices=[], effects={"set_flag": {"scar_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_emp_n2_pay", speaker="Scar",
            text="[Prende l'imponente carico di cibo, incredulo] Non riceviamo veri regali da anni. Siete pazzi... o siete angeli.",
            choices=[], effects={"cost": {"food_01": 20, "food_02": 10}, "reputation": {"razziatori": +10}, "set_flag": {"scar_emp_quest_active": True, "scar_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="scar_emp_n2_fetch", speaker="Scar",
            text="Vuoi aiutarci per la bontà del tuo cuore? [Risata amara]. Non sentivo una bugia così dolce da anni. Trovate tutto quel cibo e portatelo qui. Forse ricomincerò a credere nei miracoli.",
            choices=[], effects={"set_flag": {"scar_emp_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_prag_n2_info", speaker="Scar",
            text="Un'informazione interessante, ma non si può mangiare la paura dei nemici. Apprezzo l'occhio clinico, ma il mio stomaco resta vuoto. La tariffa non cambia.",
            choices=scelte_prag_fase_3, effects={"info_shared": "solidali_depot", "set_flag": {"scar_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="scar_prag_n2_bluff", speaker="Scar",
            text="Le minacce sono l'ultima risorsa di chi ha esaurito la logica. Se il tuo gruppo è così potente, non avrà problemi a recuperare il carico. La mia offerta resta sul tavolo.",
            choices=scelte_prag_fase_3, effects={"set_flag": {"scar_prag_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="scar_diplo_n2_med", speaker="Scar",
            text="Le promesse a lungo termine sono come i classici della letteratura: nobili, ma non sfamano nessuno nel presente. L'unica clausola che mi interessa sono le scorte di cibo.",
            choices=scelte_diplo_fase_3, effects={"set_flag": {"scar_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="scar_diplo_n2_trade", speaker="Scar",
            text="La logica è corretta, ma incompleta. Uno scontro ci costerebbe proiettili, ma la fame ci costerebbe l'intero avamposto. Portatemi il cibo.",
            choices=scelte_diplo_fase_3, effects={"set_flag": {"scar_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="scar_aggro_n2_intimidate", speaker="Scar",
            text="Ho visto gole tagliate sussurrare preghiere migliori delle tue minacce. Torna con il cibo o l'unico buco che aprirai sarà quello nella tua fortuna.",
            choices=scelte_aggro_fase_3, effects={"set_flag": {"scar_aggro_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="scar_aggro_n2_grenade", speaker="Scar",
            text="Un finale drammatico, quasi shakespeariano. Metti via quel giocattolo e portami le scorte. È l'unico modo per non vederlo esplodere qui, ora.",
            choices=scelte_aggro_fase_3, effects={"set_flag": {"scar_aggro_quest_active": True}, "combat_risk": 0.02}))

        tree.add_node(DialogueNode(node_id="scar_emp_n2_past", speaker="Scar",
            text="Insegnavo letteratura, sì. Spiegavo la bellezza della poesia, ora spiego come sgozzare un uomo in silenzio. I poeti sono marciti tutti. Vuoi onorare il passato? Portami il presente. Cibo.",
            choices=scelte_emp_fase_3, effects={"set_flag": {"scar_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="scar_emp_n2_trust", speaker="Scar",
            text="Morire oggi è la parte facile. Sopravvivere fino a domani è la vera tortura. Le tue parole gentili non mettono carne sulle loro ossa. Se non vuoi che diventiamo mostri, portami da mangiare.",
            choices=scelte_emp_fase_3, effects={"set_flag": {"scar_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="scar_prag_n3_deal", speaker="Scar", text="Saggio. Come dicevano i classici, 'la necessità non conosce legge', ma conosce molto bene la disciplina. Avete la mia parola: portatemi il cibo e sarete i benvenuti in questo settore. Ma non ripresentatevi a mani vuote.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_diplo_n3_thanks", speaker="Scar", text="Un saggio disse che la guerra è la continuazione della politica con altri mezzi. Avete scelto la politica del ventre pieno. Ora sparite dalla mia vista. Tornate solo quando avrete le borse pesanti.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_aggro_n3_leave", speaker="Scar", text="Eccellente. Apprezzo quando la pragmatica trionfa sull'orgoglio. Vi congedo, ma ricordate: la mia pazienza ha un'autonomia limitata, proprio come le nostre scorte. Tornate con il dovuto o non avvicinatevi.", choices=[],
            effects={"end": True, "combat_avoided": True, "combat_risk": 0.30}))

        tree.add_node(DialogueNode(node_id="scar_emp_n3_care", speaker="Scar", text="[Abbassa impercettibilmente l'arma, la voce perde per un secondo la sua ruvidezza]. Le promesse sono cose estremamente fragili di questi tempi. Ma... dirò ai ragazzi di tenere acceso il fuoco. Non farmi sembrare uno stupido. Andate.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="scar_ignore_n2", speaker="Scar", text="A morte!", choices=[],
            effects={"start_combat": True, "reputation": {"razziatori": -15}}))
        tree.add_node(DialogueNode(node_id="scar_eval_walk_away", speaker="Scar", text="Te ne vai proprio ora? Fateli a pezzi!", choices=[],
            effects={"start_combat": True, "reputation": {"razziatori": -10}}))

        return tree

    @staticmethod
    def build_vex() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Vex")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        medkit_adv_posseduti = count_item("medkit_advanced")
        bende_possedute = count_item("bandage_01")
        antibiotici_posseduti = count_item("antibiotics_01")

        ha_i_requisiti = medkit_adv_posseduti >= 1 and bende_possedute >= 3 and antibiotici_posseduti >= 5

        q_prag  = gs.flags.get("vex_prag_quest_active", False)
        q_diplo = gs.flags.get("vex_diplo_quest_active", False)
        q_aggro = gs.flags.get("vex_aggro_quest_active", False)
        q_emp   = gs.flags.get("vex_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("vex_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Vex",
                    text="Il mio fianco sta meglio grazie a te. Non farmi pentire di averti lasciato passare, muoviti.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "L'affare è ancora in piedi. Hai portato il kit medico avanzato, le bende e gli antibiotici?"
            elif q_diplo:
                greeting = "Spero tu sia di parola. La ferita peggiora. Hai le mie cure?"
            elif q_aggro:
                greeting = "Non tirare troppo la corda... Hai quelle maledette scorte mediche o devo iniziare a sparare?"
            elif q_emp:
                greeting = "[Respira a fatica] Sapevo che saresti tornato. Hai trovato il kit avanzato e i farmaci?"
            else:
                greeting = "Il mio dito è sul grilletto. Hai portato quello che mi serve?"

            if ha_i_requisiti:
                scelte_ritorno = [("«Sì, ho tutto. Kit, bende e farmaci. Ora abbassa quel fucile.»", "vex_standby_pay")]
            else:
                scelte_ritorno = [("«Lo sto ancora cercando, dammi tempo.»", "vex_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Vex", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="vex_standby_wait", speaker="Vex",
                text="Allora sparisci dalla mia ottica finché non trovi tutto.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="vex_standby_pay", speaker="Vex",
                text="[Prende i rifornimenti medici al volo] Ah... Finalmente. Affare fatto. Passate in fretta.",
                choices=[], effects={
                    "cost": {"medkit_advanced": 1, "bandage_01": 3, "antibiotics_01": 5},
                    "set_flag": {"vex_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"razziatori": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Eccoti le cure. 1 kit avanzato, bende e antibiotici. Lasciaci via libera totale.»", "vex_prag_n2_pay", {"ethics": 0, "reputation": {"razziatori": +1}}))
            scelte_diplo_fase_2.append(("«Abbiamo il materiale medico richiesto. Te lo consegniamo per onorare il nostro accordo.»", "vex_diplo_n2_pay", {"ethics": +2, "reputation": {"razziatori": +1}}))
            scelte_aggro_fase_2.append(("«Prendi questa fottuta scorta medica e toglimi il laser dalla fronte prima che perda la pazienza.»", "vex_aggro_n2_pay", {"ethics": -2, "reputation": {"razziatori": +2}}))
            scelte_emp_fase_2.append(("«Abbiamo il kit avanzato e i farmaci. Curalo, la tua vita è al sicuro ora.»", "vex_emp_n2_pay", {"ethics": +3, "reputation": {"razziatori": +2}}))
        else:
            scelte_prag_fase_2.append(("«Posso procurarti le cure, ma non ho tutto questo materiale con me. Lasciaci via libera totale.»", "vex_prag_n2_fetch", {"ethics": 0}))
            scelte_diplo_fase_2.append(("«Non abbiamo un kit avanzato e tutte quelle bende, ma cercheremo le cure nei paraggi.»", "vex_diplo_n2_fetch", {"ethics": +1}))
            scelte_aggro_fase_2.append(("«Vado a prenderti il kit e il resto, ma non stuzzicarmi. Tieniti alla larga dal grilletto.»", "vex_aggro_n2_fetch", {"ethics": -1, "reputation": {"razziatori": +1}}))
            scelte_emp_fase_2.append(("«Lascia che cerchiamo queste cure specifiche per te. Sappiamo come bendare una ferita.»", "vex_emp_n2_fetch", {"ethics": +2}))

        scelte_prag_fase_2.extend([
            ("«Le cure le teniamo noi. In cambio, ti offro le coordinate esatte di un convoglio militare qui vicino.»", "vex_prag_n2_info", {"ethics": -2, "reputation": {"razziatori": -1, "solidali": -3}}),
            ("«Tutta questa roba medica è rara. Che ne dici di scambiare il passaggio per munizioni?»", "vex_prag_n2_ammo", {"reputation": {"razziatori": +2}}),
            ("«[Tenta la fuga ai ripari]»", "vex_eval_flee")
        ])

        scelte_diplo_fase_2.extend([
            ("«Scendi, uniamo le forze e cerchiamo in sicurezza un ospedale nei paraggi. Ti copriamo le spalle.»", "vex_diplo_n2_trade", {"ethics": +1, "reputation": {"razziatori": +1}}),
            ("«Considera le tue condizioni. Se spari, il rinculo aggraverà l'emorragia. Lasciaci passare per il tuo bene.»", "vex_diplo_n2_honor", {"ethics": +1}),
            ("«[Tenta la fuga ai ripari]»", "vex_eval_flee")
        ])

        scelte_aggro_fase_2.extend([
            ("«[Minaccia di assalto] Ti diamo tre secondi prima di sfondare la porta ed espugnare quel tetto!»", "vex_aggro_n2_intimidate", {"ethics": -2, "reputation": {"razziatori": -1}}),
            ("«[Spara una raffica verso il cornicione] Metti giù l'arma e arrenditi! O ti svuoto il caricatore addosso!»", "vex_aggro_n2_suppress", {"ethics": -3, "reputation": {"razziatori": +1}}),
            ("«[Tenta la fuga ai ripari]»", "vex_eval_flee")
        ])

        scelte_emp_fase_2.extend([
            ("«[Echo, con sincera compassione] Come ti sei fatto quello squarcio? Siamo tutti sulla stessa barca, parlane.»", "vex_emp_n2_past", {"ethics": +2, "reputation": {"razziatori": -1}}),
            ("«[Echo, alzando la voce] Ascoltami bene, non ti lasceremo morire lassù! Respira e resta con noi.»", "vex_emp_n2_trust", {"ethics": +2}),
            ("«[Tenta la fuga ai ripari]»", "vex_eval_flee")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Cerca di non morire dissanguato prima che torniamo.»", "vex_prag_n3_deal", {"ethics": -1}),
            ("«Andiamo a cercare questo kit. Tieni il dito lontano dal grilletto e la zona pulita.»", "vex_prag_n3_deal", {"ethics": 0}),
            ("«Accettiamo i termini. Resta lì, risparmia le forze e aspettaci.»", "vex_prag_n3_deal", {"ethics": +1})
        ]

        scelte_diplo_fase_3 = [
            ("«Abbiamo un'intesa. Evita rumori inutili, cercheremo le cure e te le porteremo.»", "vex_diplo_n3_thanks", {"ethics": +1}),
            ("«Tregua accettata. Mantieni la posizione e non sparare a vista.»", "vex_diplo_n3_thanks", {"ethics": +1}),
            ("«La logica vince. Resta coperto lassù, andiamo a cercare questo materiale.»", "vex_diplo_n3_thanks", {"ethics": 0})
        ]

        scelte_aggro_fase_3 = [
            ("«Vado a prenderti i medicinali, ma tieni giù quell'arma o torno a dare fuoco all'edificio.»", "vex_aggro_n3_leave", {"ethics": -2}),
            ("«Affare fatto. Ma guardati le spalle, idraulico. Non accetterò scherzi.»", "vex_aggro_n3_leave", {"ethics": -1}),
            ("«Ti terremo in vita, per ora. Resta lì a sanguinare e non azzardarti a premere il grilletto.»", "vex_aggro_n3_leave", {"ethics": -2, "reputation": {"razziatori": +1}})
        ]

        scelte_emp_fase_3 = [
            ("«Tieni duro. Torneremo con le cure. Cerca di concentrarti sul respiro.»", "vex_emp_n3_care", {"ethics": +2}),
            ("«Non morire prima del nostro ritorno. È una promessa, ti tireremo fuori di lì.»", "vex_emp_n3_care", {"ethics": +2}),
            ("«Resisti. Prometto che ti aiuteremo. Abbassa l'arma e aspettaci.»", "vex_emp_n3_care", {"ethics": +1})
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«[Urlando] Spararci ti costa proiettili, lasciarci passare zero. Qual è il pedaggio?»", "vex_prag_n1_direct", {"ethics": -1, "reputation": {"razziatori": +1}}),
                     ("«Sei su un tetto, noi qui sotto. Hai il vantaggio tattico. Cosa vuoi per togliere il disturbo?»", "vex_prag_n1_direct", {"ethics": 0, "reputation": {"razziatori": +1}}),
                     ("«Hai il dito sul grilletto ma non hai sparato. Hai un problema, noi siamo la soluzione. Facciamo affari.»", "vex_prag_n1_direct", {"ethics": 0})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«[Alzando le mani in pace] Siamo bloccati, ma se spari attirerai gli infetti. Parliamone, offro una tregua.»", "vex_diplo_n1_civic", {"ethics": +1, "reputation": {"razziatori": -1}}),
                     ("«[A voce alta ma pacata] Hai il vantaggio tattico. Ma un colpo rimbomberà. Cosa ti serve per lasciarci passare?»", "vex_diplo_n1_civic", {"ethics": +1, "reputation": {"razziatori": +1}}),
                     ("«[Mani in vista] Se sei da solo lassù potresti aver bisogno di assistenza. Negoziamo un mutuo soccorso.»", "vex_diplo_n1_civic", {"ethics": +2, "reputation": {"razziatori": -1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Armi in pugno] Hai il dito pesante o stai tremando? Spara se hai fegato! Se mi manchi ti stacco la testa!»", "vex_aggro_n1_head", {"ethics": -2, "reputation": {"razziatori": +1}}),
                     ("«[Puntando verso l'alto] Scendi e affrontaci! O preferisci morire lassù quando faremo saltare il palazzo?»", "vex_aggro_n1_head", {"ethics": -3, "reputation": {"razziatori": +2}}),
                     ("«[Sfidando il mirino] Pensi di spaventarmi con un fucile? Fai la mossa o togliti dai piedi!»", "vex_aggro_n1_head", {"ethics": -2, "reputation": {"razziatori": +1}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«[Verso il tetto] Ehi! Vediamo del sangue colare dal cornicione! Non puntarci l'arma, vogliamo darti una mano!»", "vex_emp_n1_pain", {"ethics": +2, "reputation": {"razziatori": -1}}),
                     ("«[Mani in vista] Sembra che tu stia soffrendo! Metti giù il fucile. Lascia che ti aiutiamo, non sei solo!»", "vex_emp_n1_pain", {"ethics": +2, "reputation": {"razziatori": -2}}),
                     ("«[Tono rassicurante] Ascoltami! Sembri ferito e sfinito. Non siamo nemici oggi. Dimmi di cosa hai bisogno!»", "vex_emp_n1_pain", {"ethics": +3, "reputation": {"razziatori": -2}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Vex", text="Fermi. Ho il mirino su quello più alto, poi su quello più basso. Cosa volete prima che io spari?",
            choices=[
                ("«[Rivet] [Urlando verso il tetto] Spararci ti costa proiettili, lasciarci passare ti costa zero. Qual è il pedaggio?»", "vex_prag_n1_direct"),
                ("«[Rivet] [Puntando l'arma verso l'alto] Scendi di lì e affrontaci faccia a faccia! Oppure preferisci saltare in aria?»", "vex_aggro_n1_head"),
                ("«[Echo] [Alzando le mani] Siamo bloccati e hai il fucile. Ma se spari attiri gli infetti. Offro una tregua.»", "vex_diplo_n1_civic"),
                ("«[Echo] [Gridando] Ehi, lassù! Vediamo del sangue colare dal cornicione! Non puntarci l'arma, vogliamo aiutarti!»", "vex_emp_n1_pain"),
                ("«[Tenta la fuga ai ripari]»", "vex_eval_flee")
            ]))

        tree.add_node(DialogueNode(node_id="vex_prag_n1_direct", speaker="Vex", text="[La voce metallica e graffiata arriva da un megafono] Acuto, laggiù. Una volta stringevo tubature, ora cerco di tappare un buco nel mio fianco. Ho beccato una scheggia e sto sanguinando. L'accordo è semplice: 1 Kit Medico Avanzato, 3 Bende e 5 Antibiotici. Niente cure, niente strada.", choices=scelte_prag_fase_2, effects={"reputation": {"razziatori": +1}}))

        tree.add_node(DialogueNode(node_id="vex_diplo_n1_civic", speaker="Vex", text="[La voce scende dal tetto, velata di fatica] Niente panico... apprezzo il sangue freddo. E hai ragione sul rumore: uno sparo attira guai. Ma ho un problema. C'è lamiera nel mio fianco e perdo liquidi. Volete passare? L'accordo è ragionevole: portatemi 1 Kit Medico Avanzato, 3 Bende e 5 Antibiotici e la strada è vostra.", choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="vex_aggro_n1_head", speaker="Vex", text="[Si sente il crepitio di un fucile e un proiettile scheggia l'asfalto] Non sto tremando, sbruffone. Ho una scheggia nel fianco e questo mi rende irritabile. Volete vivere? Perché se volete uscire da questo vicolo dovrete portarmi 1 Kit Medico Avanzato, 3 Bende e 5 Antibiotici. Altrimenti il prossimo colpo vi rifà la faccia.", choices=scelte_aggro_fase_2, effects={"ethics": -1, "reputation": {"razziatori": -2}}))

        tree.add_node(DialogueNode(node_id="vex_emp_n1_pain", speaker="Vex", text="[Voce esitante cala dal tetto, priva della solita spavalderia] Voi... riuscite a vedere il sangue fin laggiù? [Sospira] Maledizione. Io non voglio sparare a nessuno oggi, ma sono messo male. Un pezzo di lamiera nel fianco. Se volete davvero aiutarmi... vi prego, ho disperato bisogno di 1 Kit Medico Avanzato, 3 Bende e 5 Antibiotici. Aiutatemi.", choices=scelte_emp_fase_2, effects={"ethics": +2}))

        tree.add_node(DialogueNode(node_id="vex_prag_n2_pay", speaker="Vex", text="Chiamalo affare, baratto, estorsione. Non mi frega dei titoli, mi frega di non crepare. Datemi questi medicinali.", choices=[],
            effects={"cost": {"medkit_advanced": 1, "bandage_01": 3, "antibiotics_01": 5}, "reputation": {"razziatori": +5}, "set_flag": {"vex_prag_quest_active": True, "vex_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vex_prag_n2_fetch", speaker="Vex", text="Chiamalo affare o baratto. Non mi frega dei titoli, mi frega di non crepare. Trovate il kit avanzato, le bende e i farmaci, portateli qui e l'affare è concluso.", choices=[],
            effects={"set_flag": {"vex_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_diplo_n2_pay", speaker="Vex", text="[Recupera i medicinali calando una corda] Eccellente diplomazia. Ora passate velocemente.", choices=[],
            effects={"cost": {"medkit_advanced": 1, "bandage_01": 3, "antibiotics_01": 5}, "reputation": {"razziatori": +4}, "set_flag": {"vex_diplo_quest_active": True, "vex_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vex_diplo_n2_fetch", speaker="Vex", text="Una tregua è utile solo se restate vivi per portare le scorte mediche. Andate.", choices=[],
            effects={"set_flag": {"vex_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_aggro_n2_pay", speaker="Vex", text="[Sbuffa mentre prende il materiale al volo] E voi fate i gradassi mentre mi curate. Andate al diavolo e passate.", choices=[],
            effects={"cost": {"medkit_advanced": 1, "bandage_01": 3, "antibiotics_01": 5}, "reputation": {"razziatori": +3}, "set_flag": {"vex_aggro_quest_active": True, "vex_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vex_aggro_n2_fetch", speaker="Vex", text="Non m'importa della tua frustrazione. Se non torni con tutto l'occorrente medico, il prossimo colpo è alla gola.", choices=[],
            effects={"set_flag": {"vex_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_emp_n2_pay", speaker="Vex", text="[Prende i medicinali con mani tremanti] Non me lo aspettavo. Grazie.", choices=[],
            effects={"ethics": +4, "reputation": {"razziatori": +10}, "cost": {"medkit_advanced": 1, "bandage_01": 3, "antibiotics_01": 5}, "set_flag": {"vex_emp_quest_active": True, "vex_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vex_emp_n2_fetch", speaker="Vex", text="[Urla in preda alla paranoia] No! Fermatevi! Le scale sono bloccate e non so se riuscirei a non spararvi per lo spavento! Rimanete giù! Vi prego, portatemi le scorte mediche!", choices=[],
            effects={"set_flag": {"vex_emp_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_prag_n2_info", speaker="Vex", text="[Voce tesa dal dolore] Sai cosa me ne faccio di una mappa se non riesco ad alzarmi in piedi? Ci pulisco il sangue. L'accordo resta: mi servono i medicinali, o da questo vicolo non uscite vivi.", choices=scelte_prag_fase_3,
            effects={"info_shared": "solidali_depot", "set_flag": {"vex_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vex_prag_n2_ammo", speaker="Vex", text="[Risata secca che finisce in un gemito] I proiettili non fermano le emorragie. Posso avere tutto il piombo del mondo, ma se svengo divento un buffet per i morti. O mi portate il materiale medico, o premo il grilletto.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"vex_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vex_diplo_n2_trade", speaker="Vex", text="[Sbuffa, seguito da un leggero gemito di dolore] Se potessi fare le scale non sarei qui a negoziare. Apprezzo l'offerta di scorta, ma non ho l'autonomia per muovermi. Andate a prendere il kit e i farmaci. O niente passaggio.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"vex_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vex_diplo_n2_honor", speaker="Vex", text="[Tono piatto] La tua diagnosi è ineccepibile. Sparare mi farà male. Ma se non fermo la perdita morirò comunque. Avete la capacità di muovervi, io no. Sfruttatela per trovare le mie cure.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"vex_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vex_aggro_n2_intimidate", speaker="Vex", text="[Risata raschiante] Accomodati! Ho le scale piene di mine a strappo e l'ottica incollata sulle vostre arterie femorali. Salite e saltate in aria, oppure portatemi quelle cure. Scegli.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"vex_aggro_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="vex_aggro_n2_suppress", speaker="Vex", text="[Rumore di calcinacci. Vex torna increspato dalla rabbia] Spari come un cieco! E io non posso arrendermi se non mi reggo in piedi! Mettete via le armi e portatemi 1 Kit Medico Avanzato, Bende e Antibiotici, è l'unico fottuto modo che avete per passare.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"vex_aggro_quest_active": True}, "combat_risk": 0.10}))

        tree.add_node(DialogueNode(node_id="vex_emp_n2_past", speaker="Vex", text="[La voce si fa più sottile] Cercavo materiali... crollo strutturale. Prima che il mondo andasse all'inferno, ero un idraulico. E ora... ora c'è una perdita in me e non so come tapparla. Ma non provate a salire! Trovatemi le cure e portatele qui sotto.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"vex_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vex_emp_n2_trust", speaker="Vex", text="[Respiro tremante] Morire da solo... è quello che mi terrorizza di più. [Un fischio acuto di dolore gli mozza il fiato] Vi supplico... non fatevi illusioni e non avvicinatevi troppo. Trovate quei maledetti farmaci. Vi lascerò passare, ma ho bisogno di quella cura!", choices=scelte_emp_fase_3,
            effects={"set_flag": {"vex_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vex_prag_n3_deal", speaker="Vex", text="[Megafono che frizza per un istante] Sbrigatevi. La mia pazienza dura esattamente quanto il mio sangue. E niente scherzi... il mirino resta puntato sull'uscita. Muovetevi.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_diplo_n3_thanks", speaker="Vex", text="[Un colpo di tosse soffocato] Bene. Un accordo ragionevole tra persone ragionevoli. Il mio dito resta fuori dal ponte del grilletto... per ora. Non metteteci troppo, la mia autonomia è limitata.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_aggro_n3_leave", speaker="Vex", text="[Gremito soffocato] Risparmia il fiato per correre. Il mio mirino resta su di voi finché non siete fuori portata. Portatemi il materiale medico o deciderò di portarvi all'inferno con me.", choices=[],
            effects={"end": True, "combat_avoided": True, "combat_risk": 0.30}))

        tree.add_node(DialogueNode(node_id="vex_emp_n3_care", speaker="Vex", text="[Si ode un colpo di tosse debole. Sussurra a fatica] Io... aspetterò. Non sparerò a nessuno. Per favore... fate in fretta. Non voglio che finisca così. Grazie.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vex_eval_flee", speaker="Vex", text="Scappano! Non lasciateli andare!", choices=[],
            effects={"end": True, "flee_attempt": True, "flee_success_rate": 0.55, "on_fail": "start_combat", "reputation": {"razziatori": -3}}))

        return tree

class SolidaliDialogues:

    @staticmethod
    def build_marco() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Marco")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        alluminio_posseduto = count_item("alluminio_01")
        rottame_posseduto = count_item("scrap_metal")
        kevlar_posseduto = count_item("kevlar_scrap")

        ha_i_requisiti = alluminio_posseduto >= 20 and rottame_posseduto >= 15 and kevlar_posseduto >= 10

        q_prag  = gs.flags.get("marco_prag_quest_active", False)
        q_diplo = gs.flags.get("marco_diplo_quest_active", False)
        q_aggro = gs.flags.get("marco_aggro_quest_active", False)
        q_emp   = gs.flags.get("marco_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("marco_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Marco",
                    text="Le barricate sono sicure grazie al vostro materiale. Il passaggio è libero. Fate attenzione là fuori.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "L'accordo era chiaro: 20 Alluminio, 15 Rottami e 10 Kevlar per il pedaggio. Li avete?"
            elif q_diplo:
                greeting = "Bentornati. Spero abbiate trovato quei materiali. Le nostre difese ne hanno un disperato bisogno."
            elif q_aggro:
                greeting = "Siete ancora qui. Avete portato i materiali industriali o volete continuare a lanciare minacce?"
            elif q_emp:
                greeting = "Ehi... avete per caso trovato i materiali per rinforzare il blocco? I miei ragazzi sono esausti."
            else:
                greeting = "Senza le forniture di alluminio, rottami e kevlar non posso farvi passare."

            if ha_i_requisiti:
                scelte_ritorno = [("«Sì, ecco tutto il materiale richiesto. Prendilo.»", "marco_standby_pay")]
            else:
                scelte_ritorno = [("«Non ancora, ci stiamo lavorando.»", "marco_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Marco", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="marco_standby_wait", speaker="Marco",
                text="Tornate quando avrete qualcosa da offrire. Il blocco non si muove.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="marco_standby_pay", speaker="Marco",
                text="[Esamina i materiali industriali e le fibre] Straordinario. Ottima qualità. Vi apro il passaggio, potete andare.",
                choices=[], effects={
                    "cost": {"alluminio_01": 20, "scrap_metal": 15, "kevlar_scrap": 10},
                    "set_flag": {"marco_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"solidali": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Ho tutto il materiale industriale qui con me. Facciamo lo scambio.»", "marco_prag_n2_pay", {"ethics": +1, "reputation": {"solidali": +1}}))
            scelte_diplo_fase_2.append(("«Riconosciamo l'importanza delle vostre difese. Ecco alluminio, rottami e kevlar in segno di cooperazione.»", "marco_diplo_n2_pay", {"ethics": +2, "reputation": {"solidali": +2}}))
            scelte_aggro_fase_2.append(("«Tieni la tua fottuta spazzatura industriale e aprimi questo cancello all'istante.»", "marco_aggro_n2_pay", {"ethics": -2, "reputation": {"solidali": -1}}))
            scelte_emp_fase_2.append(("«Tenete. Tutto il materiale per blindare questo posto e farvi riposare un po'.»", "marco_emp_n2_pay", {"ethics": +3, "reputation": {"solidali": +2}}))
        else:
            scelte_prag_fase_2.append(("«Non portiamo questo equipaggiamento pesante addosso. Dacci il tempo di setacciare la zona per recuperarli.»", "marco_prag_n2_fetch", {"ethics": +1}))
            scelte_diplo_fase_2.append(("«Non li abbiamo qui ora, ma ci offriamo volontari per andarli a cercare per voi.»", "marco_diplo_n2_fetch", {"ethics": +2, "reputation": {"solidali": +1}}))
            scelte_aggro_fase_2.append(("«Non sono un mulo da soma per tutto quel ferro. Vado a prenderli, ma tenete a bada i vostri cecchini.»", "marco_aggro_n2_fetch", {"ethics": -1, "reputation": {"solidali": -1}}))
            scelte_emp_fase_2.append(("«Lascia che ci pensiamo noi. Andremo a cercare quei materiali apposta per darti il cambio.»", "marco_emp_n2_fetch", {"ethics": +2, "reputation": {"solidali": +1}}))

        scelte_prag_fase_2.extend([
            ("«I materiali scarseggiano. In cambio del passaggio, posso offrirvi coordinate tattiche su una pattuglia nemica nel settore nord.»", "marco_prag_n2_info", {"ethics": -1, "reputation": {"solidali": +2}}),
            ("«Tutto quel metallo è ingombrante. Vi offro munizioni calibro 5.56 al posto dei materiali. Il piombo vi fa comodo.»", "marco_prag_n2_trade", {"reputation": {"solidali": +1}}),
            ("«[Ignora e allontanati]»", "marco_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Le risorse materiali scarseggiano, ma abbiamo competenze tattiche e mediche. Potremmo aiutarvi a pattugliare i confini interni.»", "marco_diplo_n2_trade", {"ethics": +2, "reputation": {"solidali": +2}}),
            ("«Che ne dite di stipulare un'alleanza a lungo termine? Il nostro gruppo potrebbe diventare un partner esterno affidabile.»", "marco_diplo_n2_alliance", {"ethics": +1, "reputation": {"solidali": +2}}),
            ("«[Ignora e allontanati]»", "marco_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«Provaci. Se mi spari, ti garantisco che prima di toccare terra mi porterò all'inferno mezza della tua squadra.»", "marco_aggro_n2_intimidate", {"ethics": -3, "reputation": {"solidali": -2}}),
            ("«Non prendo ordini da un cane da guardia di basso livello. Chiama il tuo fottuto comandante, subito.»", "marco_aggro_n2_superior", {"ethics": -2, "reputation": {"solidali": -3}}),
            ("«[Ignora e allontanati]»", "marco_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Tu passi le notti a vegliare su tutte queste persone, Marco. Ma chi veglia su di te? Se non ti prendi cura di te, crollerai.»", "marco_emp_n2_care", {"ethics": +3, "reputation": {"solidali": +2}}),
            ("«Non devi portare tutto il peso del mondo sulle tue spalle. Siamo umani, vogliamo darvi una mano a proteggere i civili.»", "marco_emp_n2_alone", {"ethics": +2, "reputation": {"solidali": +1}}),
            ("«[Ignora e allontanati]»", "marco_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Mantenete la posizione, andiamo a cercare la vostra roba»", "marco_prag_n3_deal", {"ethics": 0}),
            ("«Un accordo è un accordo. Torneremo quando avremo il materiale.»", "marco_prag_n3_deal", {"ethics": +1}),
            ("«Ricevuto. Torneremo con le forniture da costruzione. Tenete d'occhio la strada.»", "marco_prag_n3_deal", {"ethics": 0}),
        ]

        scelte_diplo_fase_3 = [
            ("«Comprendiamo perfettamente la necessità di queste difese. Cercheremo i materiali e torneremo a bussare alla vostra porta.»", "marco_diplo_n3_thanks", {"ethics": +1}),
            ("«Le regole sono ciò che ci separa dal caos. Le rispetteremo: aspettateci, torneremo con i rifornimenti.»", "marco_diplo_n3_thanks", {"ethics": +2}),
            ("«Collaboreremo volentieri per la sicurezza di tutti. Raccoglieremo i materiali, mantenete la posizione.»", "marco_diplo_n3_thanks", {"ethics": +1}),
        ]

        scelte_aggro_fase_3 = [
            ("«Ti porto la tua spazzatura, ma dite ai vostri cecchini di togliermi quel laser di dosso.»", "marco_aggro_n3_leave", {"ethics": -1, "reputation": {"solidali": -1}}),
            ("«Andiamo a cercarli. Tieni i tuoi uomini calmi, o tornerò solo per farveli usare come lapidi.»", "marco_aggro_n3_leave", {"ethics": -2, "reputation": {"solidali": -2}}),
            ("«Avrai i tuoi materiali. Non fate mosse false mentre mi allontano.»", "marco_aggro_n3_leave", {"ethics": -1})
        ]

        scelte_emp_fase_3 = [
            ("«Tieni duro ancora un po', Marco. Andiamo a cercare quei materiali per voi.»", "marco_emp_n3_care", {"ethics": +2}),
            ("«Riposati il più possibile finché non torniamo. Considerala una promessa.»", "marco_emp_n3_care", {"ethics": +2}),
            ("«Prometto che ti aiuteremo a proteggerli. Raccogli le forze, a presto.»", "marco_emp_n3_care", {"ethics": +1})]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Tagliamo corto. C'è un posto di blocco, il che significa che c'è un pedaggio. Qual è la tariffa logistica oggi?»", "marco_prag_n1_direct", {"ethics": 0, "reputation": {"solidali": +1}}),
                     ("«Dobbiamo passare e voi avete il cancello. Proponiamo uno scambio veloce di merci per risolvere la questione.»", "marco_prag_n1_direct", {"ethics": +1, "reputation": {"solidali": +1}}),
                     ("«Niente convenevoli, andiamo dritti al sodo. Quanto ci costa, in termini pratici, far aprire questa barricata?»", "marco_prag_n1_direct", {"ethics": -1, "reputation": {"solidali": 0}})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«[Con tono pacato] Salve. Veniamo in pace. Chiediamo l'autorizzazione per transitare. Ammirevole il vostro perimetro.»", "marco_diplo_n1_civic", {"ethics": +2, "reputation": {"solidali": +2}}),
                     ("«[Fermandosi a debita distanza] Buongiorno. Non siamo una minaccia. Quali sono le procedure per un lasciapassare civile?»", "marco_diplo_n1_civic", {"ethics": +1, "reputation": {"solidali": +1}}),
                     ("«[Con un cenno di saluto formale] Apprezziamo lo sforzo che fate per questo settore. Vogliamo collaborare pacificamente.»", "marco_diplo_n1_civic", {"ethics": +2, "reputation": {"solidali": +1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«Aprite questo fottuto cancello. Non ho tempo da perdere con boy scout in mimetica che giocano ai soldati.»", "marco_aggro_n1_head", {"ethics": -2, "reputation": {"solidali": -2}}),
                     ("«Spostatevi immediatamente o vi faccio saltare la barricata. Voi non possedete questa strada.»", "marco_aggro_n1_head", {"ethics": -3, "reputation": {"solidali": -3}}),
                     ("«Metti giù quel fucile, ragazzino, e fammi passare. O giuro che te lo faccio ingoiare pezzo per pezzo.»", "marco_aggro_n1_head", {"ethics": -3, "reputation": {"solidali": -2}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«[Mani in vista, voce calma] Hai gli occhi rossi e fatichi a tenere le spalle dritte. Da quanti turni non dormi? Abbassa l'arma.»", "marco_emp_n1_care", {"ethics": +3, "reputation": {"solidali": +2}}),
                     ("«[Sorriso rassicurante] Sembri esausto. So che proteggi delle famiglie lì dentro. È un fardello enorme da portare.»", "marco_emp_n1_care", {"ethics": +3, "reputation": {"solidali": +3}}),
                     ("«[Tono protettivo] Non c'è bisogno del fucile. Sei al limite delle forze. Hai bisogno di acqua o di riprendere fiato?»", "marco_emp_n1_care", {"ethics": +2, "reputation": {"solidali": +2}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Marco", text="Alt là! Siete arrivati al perimetro dei Solidali. Identificatevi e diteci cosa volete.",
            choices=[
                ("«[Rivet] Dobbiamo passare. Dimmi cosa vuoi in cambio.»", "marco_prag_n1_direct"),
                ("«[Rivet] Togliete questa barricata dalla strada. Ora.»", "marco_aggro_n1_head"),
                ("«[Echo] Veniamo in pace, chiediamo il transito.»", "marco_diplo_n1_civic"),
                ("«[Echo] Siete molto esposti qui... possiamo aiutarvi?»", "marco_emp_n1_care")
            ]))

        tree.add_node(DialogueNode(node_id="marco_prag_n1_direct", speaker="Marco", text="[Mantiene la posizione di guardia, l'arma a tracolla e lo sguardo vigile] Apprezzo la sintesi, civile. L'accesso all'avamposto è attualmente ristretto. Tuttavia, il Comando autorizza delle eccezioni per chi contribuisce alla nostra logistica. Abbiamo bisogno di rinforzare pesantemente le difese perimetrali: consegnate 20 Alluminio, 15 Rottami e 10 Kevlar e vi accorderò l'autorizzazione al transito.", choices=scelte_prag_fase_2, effects={"reputation": {"solidali": +1}}))

        tree.add_node(DialogueNode(node_id="marco_diplo_n1_civic", speaker="Marco", text="[Abbassa visibilmente la canna del fucile, rilassando le spalle] Un approccio civile... è una boccata d'aria fresca, ve lo assicuro. Vi do il benvenuto a nome dei Solidali. Con grande rammarico devo informarvi che non posso autorizzare un transito gratuito. Le direttive impongono di rinforzare i muri. Per ottenere il visto d'ingresso, è richiesto un forte contributo logistico: 20 Alluminio, 15 Rottami e 10 Kevlar.", choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="marco_aggro_n1_head", speaker="Marco", text="[Alza il fucile d'assalto ad altezza petto, togliendo la sicura] Protocollo di difesa attivato. Al primo movimento brusco, i tiratori sulle torrette apriranno il fuoco. Questa è un'area militare ristretta. Se volete transitare senza finire in un sacco per cadaveri, pagherete contribuendo alla sicurezza dell'avamposto: consegnate 20 Alluminio, 15 Rottami e 10 Kevlar. Fino ad allora, la strada è sbarrata.", choices=scelte_aggro_fase_2, effects={"ethics": -1, "reputation": {"solidali": -3}}))

        tree.add_node(DialogueNode(node_id="marco_emp_n1_care", speaker="Marco", text="[Abbassa lentamente la canna del fucile, colto alla sprovvista, e si lascia sfuggire un lungo sospiro stanco] Io... vi ringrazio. Non ci sono abituato. La verità è che siamo al limite. Le difese stanno cedendo e ho il terrore che stanotte non reggeranno. Vorrei farvi entrare per mettervi al sicuro, ma mi servono disperatamente 20 Alluminio, 15 Rottami e 10 Kevlar per le barricate. Fino ad allora, le porte restano sigillate.", choices=scelte_emp_fase_2, effects={"ethics": +2, "reputation": {"solidali": +2}}))

        tree.add_node(DialogueNode(node_id="marco_prag_n2_pay", speaker="Marco", text="[Ritira i materiali industriali] Ottimo. Questi ci faranno comodo.", choices=[],
            effects={"cost": {"alluminio_01": 20, "scrap_metal": 15, "kevlar_scrap": 10}, "reputation": {"solidali": +3}, "set_flag": {"marco_prag_quest_active": True, "marco_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="marco_prag_n2_fetch", speaker="Marco", text="[Scandisce le parole con tono professionale] Avete tutto il tempo che vi occorre. Noi manteniamo la posizione, questo cancello non si sposterà. Non chiedete l'apertura finché non avrete fisicamente con voi l'intero carico richiesto.", choices=[],
            effects={"set_flag": {"marco_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_diplo_n2_pay", speaker="Marco", text="[Ispeziona i materiali e fa un cenno alla torretta] Le regole sono onorate. Benvenuti tra noi.", choices=[],
            effects={"cost": {"alluminio_01": 20, "scrap_metal": 15, "kevlar_scrap": 10}, "reputation": {"solidali": +4}, "set_flag": {"marco_diplo_quest_active": True, "marco_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="marco_diplo_n2_fetch", speaker="Marco", text="[Annuisce formale] Molto bene, civili. Attendiamo il vostro ritorno con il contributo pattuito.", choices=[],
            effects={"set_flag": {"marco_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_aggro_n2_pay", speaker="Marco", text="[Prende i materiali tenendo d'occhio le vostre mani] Materiale ricevuto. Entrate, ma vi teniamo d'occhio. Un passo falso e siete finiti.", choices=[],
            effects={"cost": {"alluminio_01": 20, "scrap_metal": 15, "kevlar_scrap": 10}, "reputation": {"solidali": -1}, "set_flag": {"marco_aggro_quest_active": True, "marco_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="marco_aggro_n2_fetch", speaker="Marco", text="[Mantiene l'arma puntata] Andate. E non avvicinatevi di nuovo al perimetro senza la merce in bella vista.", choices=[],
            effects={"set_flag": {"marco_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_emp_n2_pay", speaker="Marco", text="[Sospira, visibilmente sollevato] Noi... vi siamo profondamente grati. Potete passare, andate al sicuro.", choices=[],
            effects={"ethics": +4, "reputation": {"solidali": +10}, "cost": {"alluminio_01": 20, "scrap_metal": 15, "kevlar_scrap": 10}, "set_flag": {"marco_emp_quest_active": True, "marco_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="marco_emp_n2_fetch", speaker="Marco", text="[Un'ombra di profonda tristezza gli attraversa il volto] Fare una pausa... sarebbe un dono immenso. Vi prego, trovateli per noi.", choices=[],
            effects={"set_flag": {"marco_emp_quest_active": True}, "ethics": +1, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_prag_n2_info", speaker="Marco", text="[Annuisce in modo marziale] L'intelligence tattica è vitale e il Comando ringrazia. Ma un rapporto di ricognizione non ferma un'orda che preme sulle recinzioni. Procurate le risorse industriali.", choices=scelte_prag_fase_3,
            effects={"info_shared": "dannati_patrol", "set_flag": {"marco_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="marco_prag_n2_trade", speaker="Marco", text="[Aggiusta la postura, inflessibile] Il piombo è inutile se i muri cedono. La priorità è l'integrità strutturale, non l'armeria. O portate le forniture, o la via rimane interdetta.", choices=scelte_prag_fase_3,
            effects={"set_flag": {"marco_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="marco_diplo_n2_trade", speaker="Marco", text="[Fa un cenno di sincero rispetto] Il supporto tattico è prezioso. Tuttavia, non possiamo chiudere una breccia con la tattica se le barricate cedono. La sicurezza strutturale ha la priorità.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"marco_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="marco_diplo_n2_alliance", speaker="Marco", text="[Sorride appena] Una rete di alleati esterni è esattamente ciò a cui aspiriamo. Ma ogni alleanza solida deve basarsi sul rispetto delle procedure. Dimostrate la vostra affidabilità portandoci i materiali.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"marco_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="marco_aggro_n2_intimidate", speaker="Marco", text="[Fissa il giocatore negli occhi] La matematica tattica non è dalla tua parte, civile. Hai tre mirini laser puntati sul cranio in questo esatto momento. Portaci i materiali o fai dietrofront.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"marco_aggro_quest_active": True}, "combat_risk": 0.05}))
        tree.add_node(DialogueNode(node_id="marco_aggro_n2_superior", speaker="Marco", text="[Scuote impercettibilmente la testa] Il Comando non spreca tempo con civili ostili. Su questo cancello, io sono l'autorità assoluta. Fai un respiro profondo e ragiona: procuri i materiali o la tua strada finisce qui.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"marco_aggro_quest_active": True}, "combat_risk": 0.05}))

        tree.add_node(DialogueNode(node_id="marco_emp_n2_care", speaker="Marco", text="[Si sfrega gli occhi stanchi] Quando chiudo gli occhi, vedo i rifugi che non sono riuscito a salvare... preferisco restare sveglio. La disciplina ci tiene in vita. L'unico modo per aiutare me e la mia gente è portarmi quei materiali.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"marco_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="marco_emp_n2_alone", speaker="Marco", text="[Le spalle si abbassano per un secondo] È così pesante. Ogni singolo bambino dipende da me. Ma il dovere richiede forza. L'empatia non ferma i morti: i muri sì. Vi prego, portatemi l'alluminio e il kevlar.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"marco_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="marco_prag_n3_deal", speaker="Marco", text="[Si porta due dita alla fronte in un saluto militare] Affermativo. Massima allerta là fuori. Il checkpoint resterà chiuso fino all'avvenuta consegna della requisizione. Passo e chiudo.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_diplo_n3_thanks", speaker="Marco", text="[Si porta due dita alla visiera in un saluto impeccabile] È un onore trattare con civili ragionevoli. Manteniamo il perimetro e restiamo in attesa del vostro ritorno. A presto.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_aggro_n3_leave", speaker="Marco", text="[Voce fredda e professionale] Indietreggiate lentamente, mani ben in vista. Avvicinatevi di nuovo al perimetro solo quando avrete la merce richiesta ben visibile. Passo e chiudo.", choices=[],
            effects={"end": True, "combat_avoided": True, "combat_risk": 0.10}))

        tree.add_node(DialogueNode(node_id="marco_emp_n3_care", speaker="Marco", text="[Le labbra gli si piegano in un sorriso stanco, fragile ma genuino] Vi aspetterò. Fate molta attenzione là fuori... e grazie per avermi ricordato perché l'umanità vale ancora la pena di essere salvata.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="marco_eval_walk_away", speaker="Marco", text="Torna indietro quando avrai deciso.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        return tree

    @staticmethod
    def build_vera() -> DialogueTree:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        tree = DialogueTree(npc_name="Vera")

        if not hasattr(gs, "flags"): gs.flags = {}

        def count_item(item_name):
            c1 = sum(i.quantity for i in gs.Rivet.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            c2 = sum(i.quantity for i in gs.Echo.inventory.all_items() if getattr(i, "item_id", "").lower() == item_name.lower() or i.name.lower() == item_name.lower())
            return c1 + c2

        bende_possedute = count_item("bandage_01")
        antibiotici_posseduti = count_item("antibiotics_01")

        ha_i_requisiti = bende_possedute >= 3 and antibiotici_posseduti >= 2

        q_prag  = gs.flags.get("vera_prag_quest_active", False)
        q_diplo = gs.flags.get("vera_diplo_quest_active", False)
        q_aggro = gs.flags.get("vera_aggro_quest_active", False)
        q_emp   = gs.flags.get("vera_emp_quest_active", False)

        is_quest_active = q_prag or q_diplo or q_aggro or q_emp
        is_paid = gs.flags.get("vera_paid", False)

        if is_paid:
            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Vera",
                    text="Grazie ancora per quei medicinali. Stanno già facendo la differenza qui in infermeria. Fate attenzione là fuori.",
                    choices=[], effects={"end": True, "combat_avoided": True}))
            return tree

        if is_quest_active:
            if q_prag:
                greeting = "Siamo ancora d'accordo per lo scambio? Ho bisogno di 3 bende e 2 antibiotici."
            elif q_diplo:
                greeting = "Speravo di rivedervi. L'infermeria è a corto di scorte. Avete trovato le 3 bende e i 2 antibiotici?"
            elif q_aggro:
                greeting = "[Si irrigidisce] Siete tornati. Avete i medicinali che mi avete promesso, o volete minacciare di nuovo i miei pazienti?"
            elif q_emp:
                greeting = "[Sorride stanca] Siete voi. Avete trovato le bende e gli antibiotici per aiutarci?"
            else:
                greeting = "Le mie scorte sono a zero. Avete i medicinali?"

            if ha_i_requisiti:
                scelte_ritorno = [("«Sì, abbiamo 3 bende e 2 antibiotici. Eccoli qui.»", "vera_standby_pay")]
            else:
                scelte_ritorno = [("«Li stiamo ancora cercando, tieni duro.»", "vera_standby_wait")]

            for tone in ["root", "root_pragmatic", "root_diplomatic", "root_aggressive", "root_empathic", "root_intercept"]:
                tree.add_node(DialogueNode(node_id=tone, speaker="Vera", text=greeting, choices=scelte_ritorno))

            tree.add_node(DialogueNode(node_id="vera_standby_wait", speaker="Vera",
                text="Fate in fretta, per favore. Le infezioni non aspettano.",
                choices=[], effects={"end": True, "combat_avoided": True}))

            tree.add_node(DialogueNode(node_id="vera_standby_pay", speaker="Vera",
                text="[Prende i medicinali con cura] Sono perfetti. Grazie, davvero. Questo salverà delle vite.",
                choices=[], effects={
                    "cost": {"bandage_01": 3, "antibiotics_01": 2},
                    "set_flag": {"vera_paid": True},
                    "end": True,
                    "combat_avoided": True,
                    "reputation": {"solidali": +5}
                }))
            return tree

        scelte_prag_fase_2 = []
        scelte_diplo_fase_2 = []
        scelte_aggro_fase_2 = []
        scelte_emp_fase_2 = []

        if ha_i_requisiti:
            scelte_prag_fase_2.append(("«Ecco 3 bende e 2 antibiotici. Consideralo un investimento sulla nostra salute futura.»", "vera_prag_n2_pay", {"ethics": +1, "reputation": {"solidali": +1}}))
            scelte_diplo_fase_2.append(("«Siamo felici di poter rifornire il vostro avamposto. Ecco le 3 bende e i 2 antibiotici.»", "vera_diplo_n2_pay", {"ethics": +2, "reputation": {"solidali": +2}}))
            scelte_aggro_fase_2.append(("«Prenditi queste 3 bende e i 2 antibiotici e lasciami in pace.»", "vera_aggro_n2_pay", {"ethics": -2, "reputation": {"solidali": -1}}))
            scelte_emp_fase_2.append(("«Abbiamo 3 bende e 2 antibiotici con noi. Usali per chi ne ha davvero bisogno, subito.»", "vera_emp_n2_pay", {"ethics": +3, "reputation": {"solidali": +3}}))
        else:
            scelte_prag_fase_2.append(("«Trovare 3 bende e 2 antibiotici costa caro. Voglio un contratto blindato: cure gratuite e prioritarie per me e il mio gruppo, a vita.»", "vera_prag_n2_fetch", {"ethics": -1}))
            scelte_diplo_fase_2.append(("«Non ne abbiamo a sufficienza, ma considereremo la ricerca di 3 bende e 2 antibiotici una nostra priorità.»", "vera_diplo_n2_fetch", {"ethics": +1, "reputation": {"solidali": +1}}))
            scelte_aggro_fase_2.append(("«Non faccio i miracoli. Vado a prenderli, ma vedete di non morire tutti nel frattempo.»", "vera_aggro_n2_fetch", {"ethics": -2, "reputation": {"solidali": -2}}))
            scelte_emp_fase_2.append(("«Non dovrai fare quella scelta. Porteremo noi questo peso sulle spalle: troveremo quelle bende e quegli antibiotici.»", "vera_emp_n2_fetch", {"ethics": +2, "reputation": {"solidali": +2}}))

        scelte_prag_fase_2.extend([
            ("«Le buone intenzioni non ci proteggono nei vicoli. Vogliamo informazioni tattiche come anticipo sulla consegna, giusto per coprire le spese.»", "vera_prag_n2_info", {"ethics": -1, "reputation": {"solidali": -1}}),
            ("«Fuori c'è il caos e i prezzi dei farmaci sono alle stelle. Mi aspetto una ricompensa che valga davvero il rischio, non briciole.»", "vera_prag_n2_price", {"ethics": -2, "reputation": {"solidali": -2}}),
            ("«[Ignora e allontanati]»", "vera_eval_walk_away")
        ])

        scelte_diplo_fase_2.extend([
            ("«Proponiamo un patto di mutuo soccorso a lungo termine. Coordinando le nostre risorse, potremmo garantire la sicurezza sanitaria.»", "vera_diplo_n2_alliance", {"ethics": +2, "reputation": {"solidali": +2}}),
            ("«Se potete fornirci una lista delle farmacie accessibili, potremmo dirigerci lì per bonificare l'area e recuperare i farmaci.»", "vera_diplo_n2_info", {"ethics": +1, "reputation": {"solidali": +1}}),
            ("«[Ignora e allontanati]»", "vera_eval_walk_away")
        ])

        scelte_aggro_fase_2.extend([
            ("«[Avvicinando un accendino a una pila di bende] Forse un falò ti schiarirà le idee. Vediamo se preferisci curarmi o guardare questo posto bruciare!»", "vera_aggro_n2_intimidate", {"ethics": -4, "reputation": {"solidali": -3}}),
            ("«[Puntandole la pistola alla tempia] Non prendo ordini da un macellaio col camice. Dammi quello che chiedo o ti apro un buco in testa!»", "vera_aggro_n2_force", {"ethics": -4, "reputation": {"solidali": -4}}),
            ("«[Ignora e allontanati]»", "vera_eval_walk_away")
        ])

        scelte_emp_fase_2.extend([
            ("«Parlami di chi è più in pericolo. C'è qualcuno in particolare che ti sta a cuore? Renderemo la nostra ricerca una missione per loro.»", "vera_emp_n2_care", {"ethics": +3, "reputation": {"solidali": +3}}),
            ("«Il tuo sacrificio non passerà inosservato. La città ha bisogno di persone come te, Vera. Non lasceremo che il tuo lavoro crolli nel silenzio.»", "vera_emp_n2_help", {"ethics": +2, "reputation": {"solidali": +2}}),
            ("«[Ignora e allontanati]»", "vera_eval_walk_away")
        ])

        scelte_prag_fase_3 = [
            ("«Affare fatto. Andiamo a cercare la roba, vedi di non far crepare nessuno nel frattempo.»", "vera_prag_n3_deal", {"ethics": -1}),
            ("«Preparate la ricompensa. Torniamo presto con il carico, assicuratevi che i crediti siano pronti.»", "vera_prag_n3_deal", {"ethics": 0}),
            ("«Le troveremo. Ma tieni la borsa aperta, dottoressa. Non lavoriamo gratis.»", "vera_prag_n3_deal", {"ethics": -1}),
        ]

        scelte_diplo_fase_3 = [
            ("«Sottoscriviamo l'impegno, Dottoressa. Cercheremo i farmaci e li consegneremo secondo il protocollo richiesto.»", "vera_diplo_n3_thanks", {"ethics": +1}),
            ("«Faremo tutto il possibile per rifornire la clinica. Considerate la nostra parola come un contratto vincolante.»", "vera_diplo_n3_thanks", {"ethics": +1}),
            ("«Considerate la missione prioritaria. Torneremo presto con i materiali necessari per rendere operativa l'infermeria.»", "vera_diplo_n3_thanks", {"ethics": +1}),
        ]

        scelte_aggro_fase_3 = [
            ("«Ti porterò i tuoi maledetti medicinali, ma non finisce qui. Vedi di non farti venire strane idee mentre sono fuori.»", "vera_aggro_n3_leave", {"ethics": -2}),
            ("«Andrò a fare il tuo lavoro sporco, dottoressa. Ma quando sarò di ritorno, vedi di farti trovare pronta o raderò al suolo questo posto.»", "vera_aggro_n3_leave", {"ethics": -3}),
            ("«Vado, ma guai a te se quando torno non ho quello che mi serve. Consideralo un investimento per la tua incolumità.»", "vera_aggro_n3_leave", {"ethics": -2}),
        ]

        scelte_emp_fase_3 = [
            ("«Tieni duro ancora un po', Vera. Non lasceremo che muoiano. Torneremo con tutto il necessario.»", "vera_emp_n3_care", {"ethics": +2}),
            ("«Resisti, dottoressa. Glielo dobbiamo per tutto quello che ha fatto finora. Avrai quei medicinali, te lo prometto.»", "vera_emp_n3_care", {"ethics": +2}),
            ("«Siamo con te in questa lotta. Non sei più sola a vegliare su di loro. Cercheremo quei medicinali adesso.»", "vera_emp_n3_care", {"ethics": +3}),
        ]

        tree.add_node(DialogueNode(node_id="root_pragmatic", speaker="Rivet", text="[ Scegli l'apertura pragmatica ]",
            choices=[("«Vedo che i vostri scaffali sono vuoti. Se rimedio bende e disinfettanti, cosa mi entra in tasca?»", "vera_prag_n1_direct", {"ethics": -1, "reputation": {"solidali": -1}}),
                     ("«In questa città la salute è un lusso che pochi possono permettersi. Qual è il tasso di cambio attuale per delle medicine?»", "vera_prag_n1_direct", {"ethics": 0}),
                     ("«Possiamo rifornire la vostra infermeria, ma non facciamo beneficenza. Cosa scambiate per dei farmaci?»", "vera_prag_n1_direct", {"ethics": 0, "reputation": {"solidali": +1}})]))

        tree.add_node(DialogueNode(node_id="root_diplomatic", speaker="Echo", text="[ Scegli l'apertura diplomatica ]",
            choices=[("«Buongiorno, Dottoressa. Siamo qui in veste di potenziali alleati. Vorremmo offrire il nostro supporto ai Solidali.»", "vera_diplo_n1_civic", {"ethics": +2, "reputation": {"solidali": +2}}),
                     ("«Dottoressa Vera, il vostro lavoro è il pilastro di questo avamposto. Quali sono le necessità prioritarie della clinica al momento?»", "vera_diplo_n1_civic", {"ethics": +1, "reputation": {"solidali": +1}}),
                     ("«L'organizzazione di questo presidio medico è encomiabile. Come possiamo aiutarvi a mantenere gli standard operativi per i civili?»", "vera_diplo_n1_civic", {"ethics": +2, "reputation": {"solidali": +1}})]))

        tree.add_node(DialogueNode(node_id="root_aggressive", speaker="Rivet", text="[ Scegli l'approccio violento ]",
            choices=[("«[Sbatto i pugni sul vassoio chirurgico] Spostati da quel ferito, dottoressa! Le mie cure vengono prima di questo peso morto!»", "vera_aggro_n1_head", {"ethics": -3, "reputation": {"solidali": -2}}),
                     ("«[Giro il fucile verso le scaffalature] Questo posto è un insulto alla medicina. O mi raddrizzi subito o sfascerò quel poco di integro che ti è rimasto!»", "vera_aggro_n1_head", {"ethics": -4, "reputation": {"solidali": -3}}),
                     ("«[Afferro Vera per il camice] Non mi interessa chi sta crepando in quegli angoli. Ho bisogno di medicinali e non voglio aspettare!»", "vera_aggro_n1_head", {"ethics": -3, "reputation": {"solidali": -3}})]))

        tree.add_node(DialogueNode(node_id="root_empathic", speaker="Echo", text="[ Scegli l'approccio empatico ]",
            choices=[("«Vera, guardami per un secondo. Ti prendi cura di ogni singola anima in questo posto, ma chi si prende cura di te in questo inferno?»", "vera_emp_n1_care", {"ethics": +3, "reputation": {"solidali": +2}}),
                     ("«Quello che stai facendo qui è un miracolo, dottoressa. Lascia che ti aiuti a riprendere fiato.»", "vera_emp_n1_care", {"ethics": +2, "reputation": {"solidali": +1}}),
                     ("«[Posando idealmente una mano sulla sua spalla] Vedo il tremito nelle tue mani. Non è solo stanchezza, è dolore. Non sei sola oggi.»", "vera_emp_n1_care", {"ethics": +3, "reputation": {"solidali": +3}})]))

        tree.add_node(DialogueNode(node_id="root_intercept", speaker="Vera", text="Fermi lì! Siete feriti? Se non lo siete, per favore fatevi da parte. Abbiamo troppe emergenze e poche scorte.",
            choices=[
                ("«[Rivet] Le scorte si possono comprare. Trattiamo.»", "vera_prag_n1_direct"),
                ("«[Rivet] Curaci le ferite. Muoviti, non ammetto repliche.»", "vera_aggro_n1_head"),
                ("«[Echo] Vorremmo discutere di un supporto formale.»", "vera_diplo_n1_civic"),
                ("«[Echo] Sembrate esausta. Possiamo aiutarvi?»", "vera_emp_n1_care")
            ]))

        tree.add_node(DialogueNode(node_id="vera_prag_n1_direct", speaker="Vera", text="[Si pulisce le mani insanguinate su uno straccio già lercio, sospirando pesantemente] Siete l'ennesimo avvoltoio che cerca di speculare sull'agonia, vero? Mi disgusta, ma non posso permettermi il lusso di avere un'etica intatta. Siamo a secco e i miei pazienti non possono aspettare. Portatemi 3 Bende e 2 Antibiotici. Vi pagherò secondo il valore di mercato dell'avamposto, non un proiettile di più. Prendere o lasciare.", choices=scelte_prag_fase_2, effects={"reputation": {"solidali": +1}}))

        tree.add_node(DialogueNode(node_id="vera_diplo_n1_civic", speaker="Vera", text="[Posa uno stetoscopio e vi guarda con un cenno di assenso, sistemandosi il camice logoro ma pulito] Un tono misurato e una proposta di collaborazione... fa bene constatare che la razionalità non è andata perduta. Tuttavia, la diplomazia è uno strumento sterile senza mezzi operativi. Al momento, il mio reparto è bloccato: ho un disperato bisogno di 3 Bende e 2 Antibiotici. È la nostra condizione prioritaria per stabilire un accordo.", choices=scelte_diplo_fase_2, effects={"ethics": +1}))

        tree.add_node(DialogueNode(node_id="vera_aggro_n1_head", speaker="Vera", text="[Continua a ricucire una ferita senza sollevare lo sguardo, la voce è un sussurro glaciale] Se hai intenzione di sparare, Rivet, fallo pure. Colpirai solo gente che ha già un piede nella fossa e mi risparmierai l'ennesimo turno di venti ore. Ma se vuoi che io muova un solo dito per te, la tariffa è fissa: portami 3 Bende e 2 Antibiotici. Altrimenti, l'uscita è da quella parte. Cerca di non dissanguarti sul mio pavimento pulito.", choices=scelte_aggro_fase_2, effects={"ethics": -1, "reputation": {"solidali": -3}}))

        tree.add_node(DialogueNode(node_id="vera_emp_n1_care", speaker="Vera", text="[Si ferma bruscamente, abbassando lo sguardo sul vassoio degli strumenti. Le sue spalle tremano per un istante prima di irrigidire la postura per non crollare] Nessuno... nessuno me lo chiedeva da molto tempo. Grazie. Ma la verità è che la speranza in questo reparto sta finendo insieme alle scorte. Se non trovo 3 Bende e 2 Antibiotici entro stasera, la mia coscienza non basterà a salvarli. Dovrò scegliere chi lasciar morire domani mattina.", choices=scelte_emp_fase_2, effects={"ethics": +2, "reputation": {"solidali": +2}}))

        tree.add_node(DialogueNode(node_id="vera_prag_n2_pay", speaker="Vera", text="[Prende i materiali] Siete di parola. Vi darò accesso alle merci dell'infermeria.", choices=[],
            effects={"cost": {"bandage_01": 3, "antibiotics_01": 2}, "reputation": {"solidali": +3}, "trade": True, "set_flag": {"vera_prag_quest_active": True, "vera_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vera_prag_n2_fetch", speaker="Vera", text="[Con voce piatta e professionale] Non firmo assegni in bianco sulla vita della gente. Se vuoi essere curata, questa clinica deve restare operativa. Portami quelle 3 bende e 2 antibiotici, poi discuteremo dei tuoi futuri acciacchi.", choices=[],
            effects={"set_flag": {"vera_prag_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_diplo_n2_pay", speaker="Vera", text="[Annuisce con profonda gratitudine] Questi medicinali cambiano tutto. Siete i benvenuti qui, in qualsiasi momento.", choices=[],
            effects={"cost": {"bandage_01": 3, "antibiotics_01": 2}, "reputation": {"solidali": +4}, "set_flag": {"vera_diplo_quest_active": True, "vera_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vera_diplo_n2_fetch", speaker="Vera", text="[Annuisce gravemente] Le vostre intenzioni sono nobili. Confido che tornerete con le risorse necessarie.", choices=[],
            effects={"set_flag": {"vera_diplo_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_aggro_n2_pay", speaker="Vera", text="[Prende i materiali tenendo un bisturi ben saldo] Le tue maniere fanno schifo, ma la tua merce salva vite. Va' fuori.", choices=[],
            effects={"cost": {"bandage_01": 3, "antibiotics_01": 2}, "reputation": {"solidali": -2}, "set_flag": {"vera_aggro_quest_active": True, "vera_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vera_aggro_n2_fetch", speaker="Vera", text="[Gli occhi glaciali] Le tue minacce non creano farmaci dal nulla. Torna con le bende e gli antibiotici o stai lontano.", choices=[],
            effects={"set_flag": {"vera_aggro_quest_active": True}, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_emp_n2_pay", speaker="Vera", text="[Con le lacrime agli occhi] Voi non sapete cosa significa questo per noi. Grazie... vi curerò sempre gratuitamente.", choices=[],
            effects={"ethics": +4, "reputation": {"solidali": +10}, "cost": {"bandage_01": 3, "antibiotics_01": 2}, "heal_player": True, "set_flag": {"vera_emp_quest_active": True, "vera_paid": True}, "end": True, "combat_avoided": True}))
        tree.add_node(DialogueNode(node_id="vera_emp_n2_fetch", speaker="Vera", text="[Si asciuga una lacrima furtiva] C'è un bambino nell'angolo, si chiama Leo. Se perdo lui, perderò l'ultima parte di me che crede nel domani. Ti supplico, portami quelle 3 bende e 2 antibiotici, o il suo letto sarà vuoto domani.", choices=[],
            effects={"set_flag": {"vera_emp_quest_active": True}, "ethics": +2, "end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_prag_n2_info", speaker="Vera", text="[Senza alzare lo sguardo, voce gelida] L'unico anticipo che posso darti è la certezza che, se non ricevo quella roba, non avrai né informazioni né proiettili dal Comando. I magazzini restano chiusi finché l'infermeria è in emergenza.", choices=scelte_prag_fase_3,
            effects={"info_shared": "dannati_radio", "set_flag": {"vera_prag_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vera_prag_n2_price", speaker="Vera", text="[Si scosta una ciocca di capelli sudata] Il mercato è crudele, ma la morte lo è di più. Non ci sarà alcuna ricompensa da riscuotere se l'avamposto cade per un'infezione o se io chiudo i battenti. Portami quelle bende e quegli antibiotici se vuoi vedere un solo credito.", choices=scelte_prag_fase_3,
            effects={"info_shared": "dannati_radio", "set_flag": {"vera_prag_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vera_diplo_n2_alliance", speaker="Vera", text="[Apre un registro delle scorte] Una visione lungimirante. Ma un patto richiede che entrambe le parti siano in grado di onorarlo, e io non posso offrire soccorso se le scaffalature restano vuote. Prima dobbiamo risolvere la crisi attuale.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"vera_diplo_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vera_diplo_n2_info", speaker="Vera", text="[Estrae una mappa del settore] Ho segnalazioni su depositi non ancora saccheggiati. Posso darvi i dati, ma la ricognizione è inutile senza il recupero. Non tornate senza i medicinali, o non avremo nulla su cui basare l'accordo.", choices=scelte_diplo_fase_3,
            effects={"set_flag": {"vera_diplo_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vera_aggro_n2_intimidate", speaker="Vera", text="[Senza guardare] Dacci pure fuoco. Almeno morirò al caldo per una volta. Ma le fiamme non fabbricano antibiotici: resta il fatto che senza quelle forniture, non avrai nulla da me. Muoviti.", choices=scelte_aggro_fase_3,
            effects={"set_flag": {"vera_aggro_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vera_aggro_n2_force", speaker="Vera", text="[Sospira, appoggiando la fronte contro la lampada operatoria] Fallo. Un proiettile è l'unica vacanza che posso permettermi in questo inferno. Ma finché respiro, le mie mani non si muovono gratis. Portami quei farmaci o premi quel grilletto e falla finita.", choices=scelte_aggro_fase_3,
            effects={"heal_player": True, "set_flag": {"vera_aggro_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vera_emp_n2_care", speaker="Vera", text="[Sospira con un filo di voce] Penso sempre a chi non ce l'ha fatta... Ho paura che il buio stasera si porti via anche gli ultimi rimasti. Ma il mio dolore non è un farmaco. Senza quei medicinali, questo posto diventerà un cimitero prima dell'alba.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"vera_emp_quest_active": True}}))
        tree.add_node(DialogueNode(node_id="vera_emp_n2_help", speaker="Vera", text="[Ti guarda fisso negli occhi] A volte mi sento un fantasma tra i moribondi. Ma non posso arrendermi, non finché c'è un battito. Però i battiti hanno bisogno di bende e medicinali, non di elogi. Ti prego, vai.", choices=scelte_emp_fase_3,
            effects={"set_flag": {"vera_emp_quest_active": True}}))

        tree.add_node(DialogueNode(node_id="vera_prag_n3_deal", speaker="Vera", text="[Torna a chinarsi su un paziente, stringendo forte un laccio emostatico] Risparmiate il fiato e muovetevi. Ogni minuto che passate a mercanteggiare è un minuto di agonia che pesa sulla vostra coscienza, ammesso che ne abbiate una.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_diplo_n3_thanks", speaker="Vera", text="[Vi stringe la mano con fermezza professionale] Molto bene. Tratterò questa intesa come un impegno ufficiale verso la comunità. Il tempo è una risorsa scarsa quanto i medicinali. Confido nella vostra affidabilità.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_aggro_n3_leave", speaker="Vera", text="[Riprende a lavorare con ferocia chirurgica] Meno chiacchiere e più risultati. Esci da quella porta e non farti rivedere se non hai il materiale richiesto. Ho delle vite da salvare, io. Sparisci.", choices=[],
            effects={"end": True, "combat_avoided": True, "combat_risk": 0.10}))

        tree.add_node(DialogueNode(node_id="vera_emp_n3_care", speaker="Vera", text="[Un sussurro di ringraziamento, quasi una preghiera, le scivola dalle labbra] Sia benedetta la vostra compassione. Vi aspetterò qui... vi prego, fate in fretta. Ogni secondo che passa è una vita che trema.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        tree.add_node(DialogueNode(node_id="vera_eval_walk_away", speaker="Vera", text="Non sprecate il mio tempo se non siete seri.", choices=[],
            effects={"end": True, "combat_avoided": True}))

        return tree


class DialogueManager(ISystem):
    """
    ISystem che gestisce la conversazione attiva: avvia alberi, naviga le
    scelte, applica effetti sull'EventBus.

    Registro _TREES: mappa npc_name → callable che costruisce il DialogueTree.
    Per aggiungere un NPC basta fare:
        DialogueManager._TREES["NomNPC"] = MioModulo.build_npc
    """

    _TREES: dict[str, Callable[[], DialogueTree]] = {
        "Marco": SolidaliDialogues.build_marco,
        "Vera":  SolidaliDialogues.build_vera,
        "Scar":  RazziatorDialogues.build_scar,
        "Vex":   RazziatorDialogues.build_vex,
        "Sybil": ErrantiDialogues.build_sybil,
        "Rael":  ErrantiDialogues.build_rael,
        "Griss": DannatiDialogues.build_griss,
        "Tomas": DannatiDialogues.build_tomas
    }

    def __init__(self) -> None:
        self._active_tree: DialogueTree | None = None
        self._bus: EventBus | None = None

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus

    def cleanup(self) -> None:
        self._active_tree = None

    def start_dialogue(self, npc_name: str, start_node: str = "root") -> DialogueNode | None:
        """Avvia il dialogo dal nodo radice indicato."""
        builder = self._TREES.get(npc_name) or self._TREES.get(npc_name.capitalize()) or self._TREES.get(npc_name.lower())

        if builder is None:
            return None

        self._active_tree = builder()

        if start_node not in self._active_tree._nodes:
            start_node = "root"

        node = self._active_tree.start(start_node)

        if node and node.effects:
            self._apply_effects(node.effects)

        return node

    def choose(self, choice_index: int) -> tuple[DialogueNode | None, bool]:
        """
        Delega la navigazione all'albero attivo.
        Restituisce (nodo_successivo, is_ended).
        Applica automaticamente gli effetti sull'EventBus.
        """
        if self._active_tree is None:
            return None, True

        next_node, effects = self._active_tree.choose(choice_index)
        self._apply_effects(effects)
        return next_node, self._active_tree.is_ended()

    def _apply_effects(self, effects: dict) -> None:
        if not effects:
            return
        if self._bus is None:
            import logging
            logging.warning(
                "DialogueManager._apply_effects: EventBus non inizializzato. "
                "Gli effetti del dialogo vengono ignorati. "
                "Assicurarsi di chiamare DialogueManager.initialize(bus) prima di avviare i dialoghi."
            )
            return

        if "ethics" in effects:
            self._bus.publish(EventType.ETHICS_CHANGED,
                              {"delta": effects["ethics"]})
        if "reputation" in effects:
            for faction_id, delta in effects["reputation"].items():
                self._bus.publish(EventType.REPUTATION_CHANGED,
                                  {"faction": faction_id, "delta": delta})
        if effects.get("trade"):
            self._bus.publish(EventType.TRADE_UNLOCKED,
                              {"npc": self._active_tree.npc_name
                               if self._active_tree else "unknown"})
        if effects.get("heal_player"):
            self._bus.publish(EventType.HEAL_PLAYER, {"amount": 25})

        if "combat_risk" in effects:
            self._bus.publish(EventType.COMBAT_RISK_EVALUATED, {
                "risk": effects["combat_risk"],
                "npc": self._active_tree.npc_name if self._active_tree else "unknown"
            })

        if effects.get("start_combat"):
            self._bus.publish(EventType.START_ENCOUNTER, {
                "npc": self._active_tree.npc_name if self._active_tree else "unknown",
                "source": "dialogue"
            })

        if effects.get("flee_attempt"):
            self._bus.publish(EventType.START_ENCOUNTER, {
                "npc": self._active_tree.npc_name if self._active_tree else "unknown",
                "source": "flee_attempt",
                "flee_success_rate": effects.get("flee_success_rate", 0.5),
                "on_fail": effects.get("on_fail", "start_combat")
            })

        if "cost" in effects:
            self._bus.publish(EventType.ITEM_DELIVERED, {
                "items": effects["cost"],
                "npc": self._active_tree.npc_name if self._active_tree else "unknown"
            })

        if "set_flag" in effects:
            for flag_key, flag_val in effects["set_flag"].items():
                self._bus.publish(EventType.FLAG_SET_EVENT, {
                    "key": flag_key, "value": flag_val
                })
