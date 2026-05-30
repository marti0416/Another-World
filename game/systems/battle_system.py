"""
battle_system.py — Comandi di battaglia (pattern Command GoF) e ISystem di battaglia.

Struttura
---------
- ``IBattleCommand``  : Command astratto GoF con ``execute() -> str``.
- ``AttackCommand``   : attacco con arma equipaggiata o ATK base (legacy).
- ``WeaponCommand``   : uso diretto di un'arma speciale con validazione.
- ``SkillCommand``    : uso di un'abilità dalla SkillWheel con prob. dinamica.
- ``ItemCommand``     : uso di un consumabile in battaglia.
- ``ComboCommand``    : attacco combinato letale tra i due personaggi.
- ``FleeCommand``     : fuga (60% di probabilità di successo).
- ``BattleSystem``    : ISystem che orchestra il ciclo di battaglia via EventBus.
"""

from __future__ import annotations
import random
from abc import ABC, abstractmethod
from game.events.isystem import ISystem
from game.events.event_bus import EventBus
from game.events.event_types import EventType


class IBattleCommand(ABC):
    """Command astratto GoF — interfaccia comune a tutti i comandi di battaglia.

        Ogni ConcreteCommand incapsula una singola azione (attacco, skill, fuga, ecc.)
        ed esegue tramite ``execute()``, restituendo un messaggio di log.
    """
    @abstractmethod
    def execute(self) -> str: ...


class AttackCommand(IBattleCommand):
    """Attacco base. Se l'attaccante ha un'arma equipaggiata la usa;
    altrimenti calcola il danno grezzo da stats.atk (comportamento legacy).
    """
    def __init__(self, attacker, target) -> None:
        self.attacker = attacker
        self.target   = target

    def execute(self) -> str:
        weapon = getattr(self.attacker, "equipped_weapon", None)
        if weapon is not None and not weapon.is_out_of_ammo():
            result = weapon.use(self.attacker, [self.target])

            if weapon.is_out_of_ammo():
                from game.model.weapon_system import WeaponCategory
                if weapon.category in (WeaponCategory.EXPLOSIVE, WeaponCategory.MELEE) or result.get("consumed"):
                    if weapon in self.attacker.weapons:
                        self.attacker.weapons.remove(weapon)
                    self.attacker.unequip_weapon()

            return result["log"]

        dmg = self.target.stats.take_damage(self.attacker.stats.atk)
        return f"{self.attacker.name} attacca {self.target.name}: -{dmg} HP"


class WeaponCommand(IBattleCommand):
    """Usa direttamente un'arma speciale su uno o più bersagli."""
    def __init__(self, user, weapon, targets: list,
                 context: dict | None = None, bus: EventBus | None = None) -> None:
        self.user    = user
        self.weapon  = weapon
        self.targets = targets
        self.context = context or {}
        self._bus    = bus

    def execute(self) -> str:
        from game.model.weapon_system import WeaponValidator, WeaponCategory
        ok, reason = WeaponValidator.can_use(self.user.name, self.weapon)
        if not ok:
            return f"[ERRORE] {reason}"

        result = self.weapon.use(self.user, self.targets, self.context)

        if result.get("jammed") and self._bus:
            self._bus.publish(EventType.WEAPON_JAMMED,
                              {"weapon_id": self.weapon.item_id,
                               "character": self.user.name})

        if self.weapon.is_out_of_ammo():
            if self.weapon.category in (WeaponCategory.EXPLOSIVE, WeaponCategory.MELEE) or result.get("consumed"):
                if self.weapon in self.user.weapons:
                    self.user.weapons.remove(self.weapon)
                if getattr(self.user, "equipped_weapon", None) == self.weapon:
                    self.user.unequip_weapon()

        return result["log"]


class SkillCommand(IBattleCommand):
    """Command GoF per l'esecuzione di un'abilità dalla SkillWheel.

        La probabilità di successo è calcolata dinamicamente da ATK e/o DEF
        tramite ``_atk_prob``, ``_def_prob``, ``_def_atk_prob``.
        Ogni abilità ha la propria formula e logica di esecuzione.
    """
    def __init__(self, user, skill_node, target, targets_list) -> None:
        self.user       = user
        self.skill_node = skill_node
        self.target     = target
        self.targets_list = targets_list

    @staticmethod
    def _atk_prob(atk: int, base: float, cap: float = 1.0) -> float:
        """Probabilità che cresce con ATK. base è il punto di partenza a ATK=0."""
        chance = base + atk * (cap - base) / 20.0
        return max(base, min(cap, chance))

    @staticmethod
    def _def_prob(defense: int, base: float, cap: float = 1.0) -> float:
        """Probabilità che cresce con DEF. base è il punto di partenza a DEF=0."""
        chance = base + defense * (cap - base) / 20.0
        return max(base, min(cap, chance))

    @staticmethod
    def _def_atk_prob(defense: int, atk: int, base: float, cap: float = 1.0) -> float:
        """Probabilità che cresce con la media di DEF e ATK."""
        avg = (defense + atk) / 2.0
        chance = base + avg * (cap - base) / 20.0
        return max(base, min(cap, chance))

    def execute(self) -> str:
        from game.controller.game_manager import GameManager as _GM
        _gs = _GM.get_instance()

        name = self.skill_node.name
        atk  = getattr(getattr(self.user, "stats", None), "atk",     5)
        defense = getattr(getattr(self.user, "stats", None), "defense", 5)

        if name == "Schianto Brutale":
            dyn_rate = self._atk_prob(atk, base=0.50, cap=1.0)
        elif name == "Rattoppo d'Emergenza":
            dyn_rate = self._def_prob(defense, base=0.35, cap=1.0)
        elif name == "Onda al Plasma":
            dyn_rate = self._atk_prob(atk, base=0.75, cap=1.0)
        elif name == "Punto di Fusione":
            dyn_rate = self._atk_prob(atk, base=0.85, cap=1.0)
        elif name == "Manovra Evasiva":
            dyn_rate = self._def_prob(defense, base=0.50, cap=1.0)
        elif name == "Interferenza Cognitiva":
            dyn_rate = self._def_prob(defense, base=0.75, cap=1.0)
        elif name == "Miraggio Tattico":
            dyn_rate = self._def_prob(defense, base=0.75, cap=1.0)
        elif name == "Cortocircuito Sinaptico":
            dyn_rate = self._def_atk_prob(defense, atk, base=0.85, cap=1.0)
        else:
            dyn_rate = self.skill_node.success_rate

        once_flag = {
            "Rattoppo d'Emergenza": "_rattoppo_used_this_battle",
            "Punto di Fusione":     "_fusione_used_this_battle",
            "Miraggio Tattico":     "_miraggio_used_this_battle",
        }
        if name in once_flag:
            flag = once_flag[name]
            if getattr(_gs, flag, False):
                return f"{self.user.name}: {name} è già stata usata in questa battaglia!"

        if random.random() > dyn_rate:
            self.skill_node.current_cooldown = self.skill_node.max_cooldown
            return f"{self.user.name} tenta {name} ma fallisce!"

        self.skill_node.current_cooldown = self.skill_node.max_cooldown
        if name in once_flag:
            setattr(_gs, once_flag[name], True)
            self.skill_node.current_cooldown = 999

        tech_gained = max(1, self.skill_node.unlock_tech // 3)
        self.user.stats.gain_tech_points(tech_gained)


        if name == "Schianto Brutale":
            alive = [t for t in self.targets_list if t.is_alive()]
            target = random.choice(alive) if alive else self.target
            dmg = target.stats.take_damage(int(atk * 1.5))
            return f"{self.user.name} — SCHIANTO BRUTALE su {target.name}: -{dmg} HP!"

        elif name == "Rattoppo d'Emergenza":
            healed = self.user.stats.heal(20)
            if self.user.name == "Rivet": _gs._rivet_healed_in_battle = True
            elif self.user.name == "Echo": _gs._echo_healed_in_battle = True
            return f"{self.user.name} — RATTOPPO D'EMERGENZA: recupera +{healed} HP!"

        elif name == "Onda al Plasma":
            alive = [t for t in self.targets_list if t.is_alive()]
            if not alive:
                return f"{self.user.name} — nessun bersaglio vivo per Onda al Plasma."
            primary = max(alive, key=lambda t: t.stats.hp)
            dmg_log = []
            for t in alive:
                if t is primary:
                    d = t.stats.take_damage(int(atk * 1.5))
                else:
                    d = t.stats.take_damage(atk)
                dmg_log.append(f"{t.name}: -{d}")
            return f"{self.user.name} — ONDA AL PLASMA! " + ", ".join(dmg_log)

        elif name == "Punto di Fusione":
            alive = [t for t in self.targets_list if t.is_alive()]
            if not alive:
                return f"{self.user.name} — nessun bersaglio vivo per Punto di Fusione."
            primary = max(alive, key=lambda t: t.stats.hp)
            dmg_log = []
            for t in alive:
                if t is primary:
                    d = t.stats.take_damage(int(atk * 3))
                else:
                    d = t.stats.take_damage(int(atk * 1.5))
                dmg_log.append(f"{t.name}: -{d}")
            return f"{self.user.name} — PUNTO DI FUSIONE! " + ", ".join(dmg_log)


        elif name == "Manovra Evasiva":
            from game.model.stats import StatusEffect
            self.user.stats.add_effect(StatusEffect("Evasione", duration=1, delta_hp=0))
            return f"{self.user.name} — MANOVRA EVASIVA: prossimo attacco schivato!"

        elif name == "Interferenza Cognitiva":
            from game.model.stats import StatusEffect
            self.target.stats.add_effect(StatusEffect("Confusione", duration=1, delta_hp=0))
            return f"{self.user.name} — INTERFERENZA COGNITIVA: {self.target.name} è confuso!"

        elif name == "Miraggio Tattico":
            from game.model.stats import StatusEffect
            self.target.stats.add_effect(StatusEffect("Confusione", duration=1, delta_hp=0))
            log = f"{self.user.name} — MIRAGGIO TATTICO: {self.target.name} è confuso!"
            if random.random() < 0.35:
                dmg = self.target.stats.take_damage(atk)
                log += f" (danno bonus: -{dmg} HP!)"
            return log

        elif name == "Cortocircuito Sinaptico":
            from game.model.stats import StatusEffect
            dmg = self.target.stats.take_damage(int(atk * 2.5))
            self.target.stats.add_effect(StatusEffect("Shock", duration=1, delta_hp=0))
            return (f"{self.user.name} — CORTOCIRCUITO SINAPTICO su {self.target.name}: "
                    f"-{dmg} HP + Shock (turno saltato)!")

        return f"{self.user.name} usa {name}."

class ItemCommand(IBattleCommand):
    """
    Usa un consumabile in battaglia.
    Ogni item_id ha la propria logica (danno, AoE, self-hit, DoT programmati, ecc.).
    """
    def __init__(self, user, item_id: str, targets: list | None = None,
                 heal_target=None) -> None:
        self.user        = user
        self.item_id     = item_id
        self.targets     = targets or []
        self.heal_target = heal_target

    def _ethics_and_self_damage(self, pg, dmg_raw: int, log_parts: list, gs) -> None:
        """Applica danno ai personaggi (autoferimento) e abbassa l'etica di 1."""
        actual = pg.stats.take_damage(dmg_raw)
        log_parts.append(f"[AUTOFERIMENTO] {pg.name}: -{actual} HP!")
        gs.modify_ethics(-1)

    def _pg_list(self, gs):
        """Restituisce i personaggi vivi."""
        return [c for c in [gs.Rivet, gs.Echo] if c and c.is_alive()]

    def _avg_def(self, pgs) -> float:
        if not pgs: return 0.0
        return sum(c.stats.defense for c in pgs) / len(pgs)

    def _avg_atk(self, pgs) -> float:
        if not pgs: return 0.0
        return sum(c.stats.atk for c in pgs) / len(pgs)

    def execute(self) -> str:
        import random
        from game.model.item import ItemType
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()

        item = self.user.inventory.get_item(self.item_id)
        if not item:
            return f"{self.user.name}: '{self.item_id}' non trovato nell'inventario."

        log_parts: list[str] = []
        alive = [t for t in self.targets if t.is_alive()]
        pgs   = self._pg_list(gs)
        avg_def = self._avg_def(pgs)
        avg_atk = self._avg_atk(pgs)

        if item.hp_restore > 0:
            heal_char = self.heal_target if self.heal_target is not None else self.user
            healed = heal_char.stats.heal(item.hp_restore)
            log_parts.append(f"+{healed} HP a {heal_char.name}")

        iid = self.item_id

        if iid == "battle_explosive":
            if alive:
                primary = random.choice(alive)
                dmg = primary.stats.take_damage(25)
                log_parts.append(f"{primary.name}: -{dmg} HP")
                splash_chance = min(0.60, 0.20 + avg_atk * 0.02)
                for t in alive:
                    if t is not primary and random.random() < splash_chance:
                        sd = t.stats.take_damage(12)
                        log_parts.append(f"{t.name} (splash ½): -{sd} HP")
                self_chance = max(0.02, 0.30 - avg_def * 0.015)
                for pg in pgs:
                    if random.random() < self_chance:
                        self._ethics_and_self_damage(pg, 12, log_parts, gs)
            else:
                log_parts.append("nessun bersaglio vivo")

        elif iid == "molotov_cocktail":
            if alive:
                primary = random.choice(alive)
                dmg = primary.stats.take_damage(15)
                log_parts.append(f"{primary.name}: -{dmg} HP")
                splash_chance = min(0.50, 0.15 + avg_atk * 0.02)
                for t in alive:
                    if t is not primary and random.random() < splash_chance:
                        sd = t.stats.take_damage(7)
                        log_parts.append(f"{t.name} (splash ½): -{sd} HP")
                self_chance = max(0.01, 0.15 - avg_def * 0.01)
                for pg in pgs:
                    if random.random() < self_chance:
                        self._ethics_and_self_damage(pg, 7, log_parts, gs)
            else:
                log_parts.append("nessun bersaglio vivo")

        elif iid == "grenade_01":
            from game.model.stats import StatusEffect
            confused = 0
            for t in alive:
                if random.random() < 0.75:
                    t.stats.add_effect(StatusEffect("Confusione", duration=2, delta_hp=0))
                    confused += 1
            log_parts.append(f"Flash! {confused}/{len(alive)} nemici confusi (2 turni)")

        elif iid == "thermite_01":
            from game.model.stats import StatusEffect
            if alive:
                dmg_now = 15
                turn = 1
                total = 0
                for t in alive:
                    d = t.stats.take_damage(dmg_now)
                    total += d
                    remaining = dmg_now // 2
                    delay = 1
                    while remaining >= 1:
                        t.stats.add_effect(StatusEffect(f"Termite_t{turn+delay}",
                                                        duration=delay, delta_hp=-remaining))
                        remaining = remaining // 2
                        delay += 1
                log_parts.append(f"Termite su tutti! Danno immediato {dmg_now}, poi dimezza ogni turno")
            else:
                log_parts.append("nessun bersaglio vivo")

        elif iid == "c4_01":
            from game.model.stats import StatusEffect
            if alive:
                for t in alive:
                    t.stats.add_effect(StatusEffect("C4_Detonazione", duration=1, delta_hp=-50))
                log_parts.append(f"C4 piazzata! Detonazione al prossimo turno su {len(alive)} nemici (−50 HP)")
                self_chance = max(0.01, 0.15 - avg_def * 0.01)
                for pg in pgs:
                    if random.random() < self_chance:
                        self._ethics_and_self_damage(pg, 25, log_parts, gs)
            else:
                log_parts.append("nessun bersaglio vivo")

        elif iid == "landmine_01":
            if alive:
                for t in alive:
                    d = t.stats.take_damage(80)
                    log_parts.append(f"{t.name}: -{d} HP")
                self_chance = max(0.05, 0.60 - avg_def * 0.02)
                for pg in pgs:
                    if random.random() < self_chance:
                        self._ethics_and_self_damage(pg, 40, log_parts, gs)
            else:
                log_parts.append("nessun bersaglio vivo")

        elif iid == "piranha_solution":
            if getattr(gs, "_piranha_used_this_battle", False):
                return f"{self.user.name}: la Piranha Solution è già stata usata in questa battaglia!"
            gs._piranha_used_this_battle = True

            if alive:
                target = max(alive, key=lambda t: t.stats.hp)

                target.stats.hp = max(0, target.stats.hp - 10)
                log_parts.append(f"{target.name} (HP più alti): -10 HP (Impatto acido)")

                from game.model.stats import StatusEffect
                target.stats.add_effect(StatusEffect("Soluzione Piranha", duration=999, delta_hp=0))

                log_parts.append("L'acido indebolisce il bersaglio! Danni extra crescenti ai prossimi attacchi.")
            else:
                log_parts.append("nessun bersaglio vivo")

        elif item.damage > 0:
            if alive:
                for t in alive:
                    d = t.stats.take_damage(item.damage)
                    log_parts.append(f"{t.name}: -{d} HP")
            else:
                log_parts.append("nessun bersaglio vivo")

        if not log_parts:
            return f"{self.user.name}: '{item.name}' non ha effetti utilizzabili."

        if item.item_type == ItemType.CONSUMABLE or item.damage > 0:
            self.user.inventory.remove_item(self.item_id, 1)

        return f"{self.user.name} usa {item.name}! " + " | ".join(log_parts)


class ComboCommand(IBattleCommand):
    """Command GoF per l'attacco combinato letale dei due personaggi.

        Azzera istantaneamente gli HP del bersaglio. Disponibile solo quando
        entrambi i personaggi sono vivi e il bersaglio è l'unico rimasto.
    """
    def __init__(self, initiator, partner, target) -> None:
        self.initiator = initiator
        self.partner   = partner
        self.target    = target

    def execute(self) -> str:
        hp_rimasti = self.target.stats.hp
        self.target.stats.hp = 0

        return (f"COMBO LETALE! {self.initiator.name} ed {self.partner.name} "
                f"uniscono le forze e annientano {self.target.name} (-{hp_rimasti} HP)!")


class FleeCommand(IBattleCommand):
    """Command GoF per il tentativo di fuga (60% di probabilità di successo).

        In caso di successo, pubblica ``BATTLE_ENDED`` con ``result="fled"``.
    """
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def execute(self) -> str:
        if random.random() > 0.4:
            self._bus.publish(EventType.BATTLE_ENDED, {"result": "fled"})
            return "Fuga riuscita!"
        return "Fuga fallita!"

class BattleSystem(ISystem):
    """ISystem che gestisce il ciclo di vita di una battaglia.

        Si iscrive a ``START_ENCOUNTER`` per ricevere i nemici e avviare la battaglia.
        Espone ``check_end()`` per verificare vittoria/sconfitta ogni turno.
    """
    def __init__(self) -> None:
        self._bus          = None
        self._party: list  = []
        self._enemies: list = []
        self.running       = False

    def initialize(self, bus: EventBus) -> None:
        self._bus = bus
        bus.subscribe(EventType.START_ENCOUNTER, self._on_start_encounter)

    def cleanup(self) -> None:
        if self._bus:
            self._bus.unsubscribe(EventType.START_ENCOUNTER, self._on_start_encounter)

    def _on_start_encounter(self, data: dict) -> None:
        self._enemies = data.get("enemies", [])
        self.start_battle()

    def start_battle(self) -> None:
        self.running = True

    def check_end(self) -> str | None:
        if all(not e.is_alive() for e in self._enemies):
            self.running = False
            return "victory"
        if any(not c.is_alive() for c in self._party):
            self.running = False
            return "defeat"
        return None