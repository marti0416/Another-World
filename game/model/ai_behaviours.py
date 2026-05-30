"""
ai_behaviours.py — Comportamenti AI dei nemici in battaglia (pattern Strategy GoF).

Ogni classe concreta implementa ``IBattleAI`` e definisce la logica decisionale
di un tipo di nemico o fazione. Il metodo ``decide_move()`` restituisce un dict
che descrive l'azione scelta; il sistema di battaglia lo interpreta ed esegue.

Formato del dict restituito da ``decide_move``
----------------------------------------------
Chiavi comuni:
    - ``action``  : str — tipo di azione ("attack", "special", "summon", "flee",
                    "tentacle", "idle", "summon_and_flee").
    - ``power``   : int — potere dell'attacco (0 se non applicabile).
    - ``log``     : str — messaggio testuale da mostrare in battaglia.

Chiavi condizionali:
    - ``target``        : singolo bersaglio.
    - ``targets``       : lista di bersagli.
    - ``split_damage``  : bool — se True il danno è diviso tra tutti i target.
    - ``status_effect`` : dict con "name", "duration", "damage" da applicare.
    - ``entity``        : str — tipo di entità da evocare ("infetto", "orda").
    - ``qty``           : int — quantità di entità da evocare.
"""

import random
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Interfaccia Strategy
# ---------------------------------------------------------------------------

class IBattleAI(ABC):
    """Strategy astratta GoF per il comportamento AI in battaglia.

    Ogni ConcreteStrategy implementa ``decide_move()`` con la logica specifica
    del tipo di nemico. Il metodo statico ``_alive()`` è un helper condiviso.
    """

    @abstractmethod
    def decide_move(self, enemy, targets: list) -> dict:
        """Decide e restituisce la mossa da eseguire questo turno.

        Args:
            enemy:   Il nemico che esegue la mossa (accesso a stats e flag interni).
            targets: Lista di tutti i possibili bersagli (vivi o meno).

        Returns:
            Dizionario che descrive l'azione scelta (vedi formato nella docstring
            del modulo).
        """
        pass

    @staticmethod
    def _alive(targets: list) -> list:
        """Filtra la lista dei bersagli restituendo solo quelli in vita.

        Args:
            targets: Lista di oggetti con attributo ``is_alive()``.

        Returns:
            Lista dei bersagli con HP > 0.
        """
        return [t for t in targets if t.is_alive()]


# ---------------------------------------------------------------------------
# AI per nemici zombie
# ---------------------------------------------------------------------------

class InfettoAI(IBattleAI):
    """Comportamento AI dell'Infetto (zombie base).

    Logica:
    - 25% di probabilità: sputa Mucillagine su tutti i bersagli (DOT + debuff difesa).
    - 75%: attacco fisico diviso su tutti i bersagli vivi.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": f"{enemy.name} barcolla."}

        if random.random() < 0.25:
            return {
                "action": "special",
                "targets": alive,
                "power": 0,
                "status_effect": {"name": "mucillagine", "duration": 2, "damage": 5},
                "log": f"{enemy.name} sputa Mucillagine! Danni nel tempo applicati."
            }

        return {
            "action": "attack",
            "targets": alive,
            "split_damage": True,
            "power": enemy.stats.atk,
            "log": f"{enemy.name} attacca brutalmente Echo e Rivet!"
        }


class CorazzatoAI(IBattleAI):
    """Comportamento AI del Corazzato (zombie con armatura).

    Logica:
    - Se HP ≤ 30% e non ha ancora evocato: 25% di probabilità di richiamare un Infetto.
    - Altrimenti: attacca il bersaglio più debole (HP minimi).
    Il flag ``_has_summoned`` sull'enemy previene evocazioni multiple.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": f"{enemy.name} ringhia."}

        is_low_hp     = enemy.stats.hp <= (enemy.stats.max_hp * 0.3)
        has_summoned  = getattr(enemy, "_has_summoned", False)

        if is_low_hp and not has_summoned and random.random() < 0.25:
            enemy._has_summoned = True
            return {
                "action": "summon",
                "entity": "infetto",
                "power": 0,
                "log": f"{enemy.name} lancia un urlo gutturale e richiama un Infetto!"
            }

        # Attacca il bersaglio più debole (in caso di parità, sceglie casualmente).
        min_hp = min(t.stats.hp for t in alive)
        weakest_targets = [t for t in alive if t.stats.hp == min_hp]
        target = random.choice(weakest_targets)

        return {
            "action": "attack",
            "target": target,
            "power": enemy.stats.atk,
            "log": f"{enemy.name} si scaglia contro {target.name}!"
        }


class OrdaAI(IBattleAI):
    """Comportamento AI dell'Orda (gruppo di zombie minori).

    Logica: attacco di massa diviso su tutti i bersagli vivi ogni turno.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": "L'orda si disperde."}

        return {
            "action": "attack",
            "targets": alive,
            "split_damage": True,
            "power": enemy.stats.atk,
            "log": f"{enemy.name} travolge i bersagli attaccando tutti insieme!"
        }


class MeatGiantAI(IBattleAI):
    """Comportamento AI del Gigante di Carne (boss zombie).

    Logica alternata ogni 2 turni:
    - Turno pari: attacco tentacolare (80% ATK) su tutti i bersagli.
    - Turno dispari: attacco singolo casuale (100% ATK).
    - Prima evocazione (25% prob.): richiama 2 Orde come supporto.
    Il contatore ``_turn_counter`` e il flag ``_has_summoned`` vengono
    memorizzati direttamente sull'oggetto enemy.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": f"{enemy.name} ruggisce."}

        has_summoned = getattr(enemy, "_has_summoned", False)
        if not has_summoned and random.random() < 0.25:
            enemy._has_summoned = True
            return {
                "action": "summon",
                "entity": "orda",
                "qty": 2,
                "power": 0,
                "log": f"{enemy.name} fa tremare la terra ed evoca un'Orda!"
            }

        turn = getattr(enemy, "_turn_counter", 0) + 1
        enemy._turn_counter = turn

        if turn % 2 == 0:
            return {
                "action": "tentacle",
                "targets": alive,
                "power": int(enemy.stats.atk * 0.8),
                "log": f"{enemy.name} sferra un possente attacco tentacolare!"
            }

        target = random.choice(alive)
        return {
            "action": "attack",
            "target": target,
            "power": enemy.stats.atk,
            "log": f"{enemy.name} schiaccia {target.name}!"
        }


# ---------------------------------------------------------------------------
# AI per nemici fazione (umani ostili)
# ---------------------------------------------------------------------------

class BaseFazioneAI(IBattleAI):
    """Classe base condivisa per le AI delle fazioni umane.

    Fornisce il metodo ``check_reputation_flee()`` che verifica se la
    reputazione corrente supera la soglia di -10: in quel caso il nemico
    tenta di fuggire anziché combattere.
    """

    def check_reputation_flee(self, enemy, reputation: int) -> dict | None:
        """Controlla se il nemico deve fuggire per motivi di reputazione.

        Args:
            enemy:      Il nemico che potrebbe fuggire.
            reputation: Reputazione attuale del giocatore verso questa fazione.

        Returns:
            Dict di fuga se ``reputation > -10``, altrimenti ``None``.
        """
        if reputation > -10:
            return {"action": "flee", "power": 0, "log": f"{enemy.name} tenta la fuga pacificamente."}
        return None


class DannatiAI(BaseFazioneAI):
    """Comportamento AI dei Dannati (fazione aggressiva con armi da fuoco).

    Logica:
    - Se reputazione > -10: tenta la fuga.
    - Se HP ≤ 50% (30% prob.): usa un Infetto come distrazione e fugge.
    - Prima volta (15% prob.): estrae l'arma da fuoco (danno x2 su un bersaglio).
    - Altrimenti: attacco di massa diviso su tutti.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        rep = getattr(enemy, "_current_reputation", -11)
        flee = self.check_reputation_flee(enemy, rep)
        if flee:
            return flee

        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": ""}

        is_low_hp = enemy.stats.hp <= (enemy.stats.max_hp * 0.5)
        if is_low_hp and random.random() < 0.30:
            return {"action": "summon_and_flee", "entity": "infetto", "power": 0,
                    "log": f"{enemy.name} usa un Infetto come distrazione e fugge!"}

        used_firearm = getattr(enemy, "_used_firearm", False)
        if not used_firearm and random.random() < 0.15:
            enemy._used_firearm = True
            target = random.choice(alive)
            return {"action": "special", "target": target, "power": enemy.stats.atk * 2,
                    "log": f"{enemy.name} estrae un'arma da fuoco e spara a {target.name}!"}

        return {"action": "attack", "targets": alive, "split_damage": True,
                "power": enemy.stats.atk, "log": f"{enemy.name} attacca con foga!"}


class RazziatoriAI(BaseFazioneAI):
    """Comportamento AI dei Razziatori (fazione con armi da taglio).

    Logica:
    - Se reputazione > -10: tenta la fuga.
    - Prima volta (15% prob.): colpo con arma da taglio (danno x1.5 su un bersaglio).
    - Altrimenti: attacco di massa diviso su tutti.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        rep = getattr(enemy, "_current_reputation", -11)
        flee = self.check_reputation_flee(enemy, rep)
        if flee:
            return flee

        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": ""}

        used_blade = getattr(enemy, "_used_blade", False)
        if not used_blade and random.random() < 0.15:
            enemy._used_blade = True
            target = random.choice(alive)
            return {"action": "special", "target": target,
                    "power": int(enemy.stats.atk * 1.5),
                    "log": f"{enemy.name} usa un'arma da taglio su {target.name}!"}

        return {"action": "attack", "targets": alive, "split_damage": True,
                "power": enemy.stats.atk, "log": f"{enemy.name} assalta il gruppo!"}


class ErrantiAI(BaseFazioneAI):
    """Comportamento AI degli Erranti (fazione con sostanze chimiche).

    Logica:
    - Se reputazione > -10: tenta la fuga.
    - Prima volta (5% prob.): lancia Soluzione Piranha su tutti (DOT crescente).
    - Altrimenti: attacco imprevedibile di massa diviso su tutti.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        rep = getattr(enemy, "_current_reputation", -11)
        flee = self.check_reputation_flee(enemy, rep)
        if flee:
            return flee

        alive = self._alive(targets)
        if not alive:
            return {"action": "idle", "power": 0, "log": ""}

        used_piranha = getattr(enemy, "_used_piranha", False)
        if not used_piranha and random.random() < 0.05:
            enemy._used_piranha = True
            return {"action": "special", "targets": alive, "power": 0,
                    "status_effect": {"name": "piranha", "duration": 2, "damage": 8},
                    "log": f"{enemy.name} lancia una Soluzione Piranha su tutti!"}

        return {"action": "attack", "targets": alive, "split_damage": True,
                "power": enemy.stats.atk, "log": f"{enemy.name} attacca in modo imprevedibile!"}


class SolidaliAI(BaseFazioneAI):
    """Comportamento AI dei Solidali (fazione non ostile, si difende solo se attaccata).

    Logica:
    - 5% di probabilità di fuggire spontaneamente.
    - Altrimenti: attacco difensivo debole (50% ATK) su un bersaglio casuale.
    I Solidali non cercano attivamente lo scontro.
    """

    def decide_move(self, enemy, targets: list) -> dict:
        if random.random() < 0.05:
            return {"action": "flee", "power": 0, "log": f"{enemy.name} riesce a fuggire!"}
        return {"action": "attack", "target": random.choice(self._alive(targets)),
                "power": int(enemy.stats.atk * 0.5),
                "log": f"{enemy.name} attacca debolmente per difendersi."}
