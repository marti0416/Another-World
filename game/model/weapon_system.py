from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.model.enemy import Enemy

Rivet_MAX_CARRY_WEIGHT: int = 80
Echo_MAX_CARRY_WEIGHT:  int = 50

class WeaponCategory:
    LIGHT     = "light"
    HEAVY     = "heavy"
    EXPLOSIVE = "explosive"
    MELEE     = "melee"
    SPECIAL   = "special"

Echo_ALLOWED_CATEGORIES: set[str] = {WeaponCategory.LIGHT, WeaponCategory.MELEE}

def _empty_result(name: str) -> dict:
    return {"log": f"{name}: nessun bersaglio valido.", "hits": [],
            "total_damage": 0, "special_effect": None, "jammed": False}

def _atk_hit_chance(user, base: float, spread: float = 0.05) -> float:
    """Probabilità di colpire basata sull'ATK. base è la prob. base (0‑1).
    Ogni punto ATK sopra 5 aggiunge spread. Cappata tra 0.20 e 0.98."""
    atk = getattr(getattr(user, "stats", None), "atk", 5)
    chance = base + max(0, atk - 5) * spread
    return max(0.20, min(0.98, chance))

class IWeaponBehaviour(ABC):
    @abstractmethod
    def fire(self, user, targets: list["Enemy"], context: dict) -> dict: ...
    @property
    @abstractmethod
    def category(self) -> str: ...
    @property
    @abstractmethod
    def weight(self) -> int: ...
    @property
    @abstractmethod
    def display_name(self) -> str: ...



class JammableWeaponBehaviour(IWeaponBehaviour):
    """Classe base Template Method per armi che possono incepparsi.

    Struttura GoF:
      fire()      → template (algoritmo fisso, non sovrascrivibile)
      _jam_rate() → hook concreto (sovrascrivibile per varianti speciali)
      _do_fire()  → hook astratto (implementato dalle sottoclassi)

    Le sottoclassi definiscono:
      JAM_BASE: float  — probabilità base di inceppamento (default 0.05)
      _do_fire()       — logica di danno specifica dell'arma
    """

    JAM_BASE: float = 0.05

    def _jam_rate(self, user) -> float:
        """Calcola la probabilità di inceppamento in base all'ATK del portatore.

        Ogni punto ATK sopra 5 riduce la probabilità dell'1%.
        Minimo: 0.0 (non può diventare negativa).
        Sovrascrivibile per armi con formula jam diversa (es. jam fisso).
        """
        atk = getattr(getattr(user, "stats", None), "atk", 5)
        return max(0.0, self.JAM_BASE - max(0, atk - 5) * 0.01)

    def fire(self, user, targets: list, context: dict) -> dict:
        """Template Method — algoritmo fisso: jam check → _do_fire()."""
        if random.random() < self._jam_rate(user):
            return {
                "log":            f"{user.name} → [{self.display_name}] INCEPPATO! Turno perso.",
                "hits":           [],
                "total_damage":   0,
                "special_effect": "jammed",
                "jammed":         True,
            }
        return self._do_fire(user, targets, context)

    @abstractmethod
    def _do_fire(self, user, targets: list, context: dict) -> dict:
        """Hook astratto — implementa il danno specifico dell'arma.

        Precondizione: il check di inceppamento è già stato superato.
        Non è necessario verificare il jam qui dentro.
        """
        ...



class AssaultRifleBehaviour(JammableWeaponBehaviour):
    """Fucile d'Assalto Pesante.
    Danno 25 fisso. Inceppamento base 5%, ridotto dall'ATK del portatore.
    Ogni punto ATK sopra 5 abbassa l'inceppamento dell'1%.
    """
    BASE_DMG = 25
    JAM_BASE = 0.05

    @property
    def category(self)     -> str: return WeaponCategory.HEAVY
    @property
    def weight(self)       -> int: return 12
    @property
    def display_name(self) -> str: return "Fucile d'Assalto"

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = random.choice(alive)
        actual = target.stats.take_damage(self.BASE_DMG)
        return {"log": f"{user.name} spara con il {self.display_name} → {target.name}: -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}


class RailGunBehaviour(JammableWeaponBehaviour):
    """Rail Gun: 35 danni per bersaglio, colpisce fino a 2 nemici.
    NON ignora la difesa. Inceppamento base 5%, ridotto dall'ATK.
    """
    BASE_DMG = 35
    JAM_BASE = 0.05

    @property
    def category(self)     -> str: return WeaponCategory.HEAVY
    @property
    def weight(self)       -> int: return 12
    @property
    def display_name(self) -> str: return "Rail Gun"

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        hits, total = [], 0
        for target in alive[:2]:
            dmg = target.stats.take_damage(self.BASE_DMG)
            hits.append((target.name, dmg))
            total += dmg
        log = (f"{user.name} spara il RAIL GUN — "
               + ", ".join(f"{n}: -{d} HP" for n, d in hits))
        return {"log": log, "hits": hits, "total_damage": total,
                "special_effect": None, "jammed": False}


class AcidGunBehaviour(JammableWeaponBehaviour):
    """Acid Gun: 15 danni + corrosione 6 HP/turno × 3 turni su TUTTI i nemici.
    Inceppamento base 8% (ridotto dall'ATK).
    """
    BASE_DMG        = 15
    JAM_BASE        = 0.08
    CORROSION_TURNS = 3
    CORROSION_DPS   = 6

    @property
    def category(self)     -> str: return WeaponCategory.HEAVY
    @property
    def weight(self)       -> int: return 8
    @property
    def display_name(self) -> str: return "Acid Gun"

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        from game.model.stats import StatusEffect
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        hits, total = [], 0
        for target in alive:
            dmg = target.stats.take_damage(self.BASE_DMG)
            target.stats.add_effect(
                StatusEffect("Corrosione", duration=self.CORROSION_TURNS, delta_hp=-self.CORROSION_DPS)
            )
            hits.append((target.name, dmg))
            total += dmg
        log = (f"{user.name} spara l'ACID GUN su tutti! "
               f"Danno immediato + {self.CORROSION_DPS} HP/turno ×{self.CORROSION_TURNS}")
        return {"log": log, "hits": hits, "total_damage": total,
                "special_effect": "corrosion_aoe", "jammed": False}


class IncendiaryMissileBehaviour(IWeaponBehaviour):
    """Missile Incendiario: 45 danni fissi + Fuoco (10/turno × 2).
    L'ATK determina la precisione — percentuale di mancato è bassa.
    Munizioni 1-3 per partita.
    """
    BASE_DMG   = 45
    FIRE_TURNS = 2
    FIRE_DPS   = 10
    MISS_BASE  = 0.12

    @property
    def category(self)     -> str: return WeaponCategory.SPECIAL
    @property
    def weight(self)       -> int: return 15
    @property
    def display_name(self) -> str: return "Missile Incendiario"

    def fire(self, user, targets: list, context: dict) -> dict:
        from game.model.stats import StatusEffect
        atk = getattr(getattr(user, "stats", None), "atk", 5)
        miss_rate = max(0.02, self.MISS_BASE - max(0, atk - 5) * 0.01)
        if random.random() < miss_rate:
            return {"log": f"{user.name} lancia il MISSILE INCENDIARIO ma manca il bersaglio!",
                    "hits": [], "total_damage": 0, "special_effect": "miss", "jammed": False}
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = alive[0]
        target.stats.hp = max(0, target.stats.hp - self.BASE_DMG)
        target.stats.add_effect(StatusEffect("Fuoco", duration=self.FIRE_TURNS, delta_hp=-self.FIRE_DPS))
        log = f"{user.name} guida il MISSILE INCENDIARIO su {target.name}: -{self.BASE_DMG} HP + fuoco!"
        return {"log": log, "hits": [(target.name, self.BASE_DMG)], "total_damage": self.BASE_DMG,
                "special_effect": "fire_dot", "jammed": False, "consumed": True}


class ArtilleryBehaviour(IWeaponBehaviour):
    """Colpo Artiglieria: 65 danni fissi, ignora difesa.
    Bersaglia il nemico con HP+DEF più alti.
    ATK determina la mira — percentuale di mancato è media.
    Munizioni 1-3 per partita.
    """
    BASE_DMG  = 65
    MISS_BASE = 0.30

    @property
    def category(self)     -> str: return WeaponCategory.SPECIAL
    @property
    def weight(self)       -> int: return 20
    @property
    def display_name(self) -> str: return "Colpo Artiglieria"

    def fire(self, user, targets: list, context: dict) -> dict:
        atk = getattr(getattr(user, "stats", None), "atk", 5)
        miss_rate = max(0.05, self.MISS_BASE - max(0, atk - 5) * 0.02)
        if random.random() < miss_rate:
            return {"log": f"{user.name} chiama l'ARTIGLIERIA ma il colpo manca!",
                    "hits": [], "total_damage": 0, "special_effect": "miss", "jammed": False}
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = max(alive, key=lambda t: t.stats.defense + t.stats.hp)
        target.stats.hp = max(0, target.stats.hp - self.BASE_DMG)
        log = f"ARTIGLIERIA! {user.name} distrugge {target.name}: -{self.BASE_DMG} HP (difesa ignorata)!"
        return {"log": log, "hits": [(target.name, self.BASE_DMG)], "total_damage": self.BASE_DMG,
                "special_effect": "fortification_breach", "jammed": False, "consumed": True}


class ThermobaricRocketBehaviour(IWeaponBehaviour):
    """Razzo Termobarico: 95 danni fissi su TUTTI i nemici.
    ATK determina la mira — percentuale di mancato è alta.
    Munizioni 1-3 per partita.
    """
    BASE_DMG  = 95
    MISS_BASE = 0.50

    @property
    def category(self)     -> str: return WeaponCategory.SPECIAL
    @property
    def weight(self)       -> int: return 18
    @property
    def display_name(self) -> str: return "Razzo Termobarico"

    def fire(self, user, targets: list, context: dict) -> dict:
        atk = getattr(getattr(user, "stats", None), "atk", 5)
        miss_rate = max(0.10, self.MISS_BASE - max(0, atk - 5) * 0.03)
        if random.random() < miss_rate:
            return {"log": f"{user.name} lancia il RAZZO TERMOBARICO ma manca!",
                    "hits": [], "total_damage": 0, "special_effect": "miss", "jammed": False}
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        hits, total = [], 0
        for target in alive:
            target.stats.hp = max(0, target.stats.hp - self.BASE_DMG)
            hits.append((target.name, self.BASE_DMG))
            total += self.BASE_DMG
        log = f"{user.name} lancia il RAZZO TERMOBARICO! {len(alive)} nemici colpiti!"
        return {"log": log, "hits": hits, "total_damage": total,
                "special_effect": "thermobaric", "jammed": False, "consumed": True}


class AntimatterGrenadeBehaviour(IWeaponBehaviour):
    """Granata Antimateria: 50 danni garantiti al bersaglio primario casuale.
    Percentuale (legata all'ATK) di splash sui nemici restanti.
    Percentuale (ridotta dalla DEF dei personaggi) di colpire se stessi.
    Munizioni 1-3 per partita.
    """
    PRIMARY_DMG   = 50
    SPLASH_BASE   = 0.40
    SELF_HIT_BASE = 0.20

    @property
    def category(self)     -> str: return WeaponCategory.EXPLOSIVE
    @property
    def weight(self)       -> int: return 5
    @property
    def display_name(self) -> str: return "Granata Antimateria"

    def fire(self, user, targets: list, context: dict) -> dict:
        from game.controller.game_manager import GameManager
        gs = GameManager.get_instance()
        atk = getattr(getattr(user, "stats", None), "atk", 5)
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)

        log_parts = []
        hits = []
        total = 0

        primary = random.choice(alive)
        primary.stats.hp = max(0, primary.stats.hp - self.PRIMARY_DMG)
        hits.append((primary.name, self.PRIMARY_DMG))
        total += self.PRIMARY_DMG
        log_parts.append(f"{primary.name}: -{self.PRIMARY_DMG} HP")

        others = [t for t in alive if t is not primary]
        splash_chance = min(0.90, self.SPLASH_BASE + max(0, atk - 5) * 0.04)
        for t in others:
            if random.random() < splash_chance:
                dmg = t.stats.take_damage(self.PRIMARY_DMG // 2)
                hits.append((t.name, dmg))
                total += dmg
                log_parts.append(f"{t.name} (splash): -{dmg} HP")

        avg_def = 0
        pgs = [c for c in [gs.Rivet, gs.Echo] if c and c.is_alive()]
        if pgs:
            avg_def = sum(c.stats.defense for c in pgs) / len(pgs)
        self_hit_chance = max(0.02, self.SELF_HIT_BASE - avg_def * 0.01)
        for pg in pgs:
            if random.random() < self_hit_chance:
                dmg = pg.stats.take_damage(self.PRIMARY_DMG // 2)
                log_parts.append(f"[AUTOFERIMENTO] {pg.name}: -{dmg} HP!")
                gs.modify_ethics(-1)

        log = f"{user.name} lancia la GRANATA ANTIMATERIA! " + ", ".join(log_parts)
        return {"log": log, "hits": hits, "total_damage": total,
                "special_effect": "antimatter", "jammed": False, "consumed": True}



class LightPistolBehaviour(JammableWeaponBehaviour):
    """Pistola Leggera: 15 danni. Inceppamento base 5%, ridotto dall'ATK.
    Bersaglio casuale.
    """
    BASE_DMG = 15
    JAM_BASE = 0.05

    @property
    def category(self)     -> str: return WeaponCategory.LIGHT
    @property
    def weight(self)       -> int: return 2
    @property
    def display_name(self) -> str: return "Pistola Leggera"

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = random.choice(alive)
        actual = target.stats.take_damage(self.BASE_DMG)
        return {"log": f"{user.name} spara con la Pistola Leggera → {target.name}: -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}


class RustyPistolBehaviour(JammableWeaponBehaviour):
    """Pistola Arrugginita: 20 danni. Inceppamento base 10%, ridotto dall'ATK.
    Bersaglio casuale.
    """
    BASE_DMG = 20
    JAM_BASE = 0.10

    @property
    def category(self)     -> str: return WeaponCategory.LIGHT
    @property
    def weight(self)       -> int: return 3
    @property
    def display_name(self) -> str: return "Pistola Arrugginita"

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = random.choice(alive)
        actual = target.stats.take_damage(self.BASE_DMG)
        return {"log": f"{user.name} spara con la Pistola Arrugginita → {target.name}: -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}


class RecoveredWeaponBehaviour(JammableWeaponBehaviour):
    """Arma Recuperata: 25 danni. Inceppamento 3% fisso (non scala con ATK).
    Bersaglio con HP più bassi tra i vivi.

    Sovrascrive _jam_rate() per usare un valore fisso invece della formula
    ATK-dipendente della classe base — variante del Template Method.
    """
    BASE_DMG = 25
    JAM_RATE = 0.03

    @property
    def category(self)     -> str: return WeaponCategory.LIGHT
    @property
    def weight(self)       -> int: return 4
    @property
    def display_name(self) -> str: return "Arma Recuperata"

    def _jam_rate(self, user) -> float:
        return self.JAM_RATE

    def _do_fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = min(alive, key=lambda t: t.stats.hp)
        actual = target.stats.take_damage(self.BASE_DMG)
        return {"log": f"{user.name} usa [Arma Recuperata] → {target.name} (HP più bassi): -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}



class ImprovisedClubBehaviour(IWeaponBehaviour):
    BASE_DMG = 18
    @property
    def category(self)     -> str: return WeaponCategory.MELEE
    @property
    def weight(self)       -> int: return 4
    @property
    def display_name(self) -> str: return "Mazza di Fortuna"

    def fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = random.choice(alive)
        actual = target.stats.take_damage(self.BASE_DMG + user.stats.atk)
        return {"log": f"{user.name} colpisce con la Mazza → {target.name}: -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}


class ImprovisedKnifeBehaviour(IWeaponBehaviour):
    BASE_DMG = 14
    @property
    def category(self)     -> str: return WeaponCategory.MELEE
    @property
    def weight(self)       -> int: return 2
    @property
    def display_name(self) -> str: return "Coltello Improvvisato"

    def fire(self, user, targets: list, context: dict) -> dict:
        alive = [t for t in targets if t.is_alive()]
        if not alive: return _empty_result(self.display_name)
        target = random.choice(alive)
        actual = target.stats.take_damage(self.BASE_DMG + user.stats.atk)
        return {"log": f"{user.name} pugnala con il Coltello → {target.name}: -{actual} HP",
                "hits": [(target.name, actual)], "total_damage": actual,
                "special_effect": None, "jammed": False}



class WeaponValidator:
    """Rivet può usare qualsiasi arma. Echo solo leggere e mischia."""

    @staticmethod
    def can_use(character_name: str, weapon: "Weapon") -> tuple[bool, str]:
        if character_name.lower() == "echo":
            if weapon.category not in Echo_ALLOWED_CATEGORIES:
                return (False,
                        f"Echo non può usare armi di categoria '{weapon.category}'. "
                        f"Consentite: {Echo_ALLOWED_CATEGORIES}")
        return True, "ok"

    @staticmethod
    def validate_or_raise(character_name: str, weapon: "Weapon") -> None:
        ok, reason = WeaponValidator.can_use(character_name, weapon)
        if not ok:
            raise ValueError(f"Arma non consentita: {reason}")



@dataclass
class Weapon:
    item_id:   str
    behaviour: IWeaponBehaviour
    ammo:      int = -1

    @property
    def display_name(self) -> str: return self.behaviour.display_name
    @property
    def category(self)     -> str: return self.behaviour.category
    @property
    def weight(self)       -> int: return self.behaviour.weight

    def use(self, user, targets: list, context: dict | None = None) -> dict:
        ctx = context or {}
        ok, reason = WeaponValidator.can_use(getattr(user, "name", ""), self)
        if not ok:
            return {"log": f"[ERRORE] {reason}", "hits": [], "total_damage": 0,
                    "special_effect": None, "jammed": False}
        if self.ammo == 0:
            return {"log": f"[{self.display_name}] Munizioni esaurite!",
                    "hits": [], "total_damage": 0, "special_effect": None, "jammed": False}

        result = self.behaviour.fire(user, targets, ctx)

        if self.ammo > 0 and not result.get("jammed", False):
            self.ammo -= 1

        return result

    def is_out_of_ammo(self) -> bool:
        return self.ammo == 0



class WeaponCreator(ABC):
    """Creator astratto — Factory Method GoF.

    Definisce il factory method ``create_weapon()`` che ogni sottoclasse
    concreta sovrascrive per istanziare il prodotto Weapon specifico.
    ``forge()`` è l'operazione pubblica che chiama il factory method.
    """

    DEFAULT_AMMO_MIN: int = 1
    DEFAULT_AMMO_MAX: int = 20

    @abstractmethod
    def create_weapon(self, ammo: int) -> Weapon:
        """Factory Method: costruisce e restituisce il Weapon concreto."""
        ...

    def _resolve_ammo(self, ammo: int) -> int:
        """Risolve il valore ammo: se -1, estrae un valore casuale nel range del Creator."""
        if ammo == -1:
            return random.randint(self.DEFAULT_AMMO_MIN, self.DEFAULT_AMMO_MAX)
        return ammo

    def forge(self, ammo: int = -1) -> Weapon:
        """Operazione pubblica: risolve le munizioni e chiama il factory method."""
        return self.create_weapon(self._resolve_ammo(ammo))


class RailGunCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("rail_gun", RailGunBehaviour(), ammo=ammo)


class AcidGunCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("acid_gun", AcidGunBehaviour(), ammo=ammo)


class AntimatterGrenadeCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 3

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("antimatter_grenade", AntimatterGrenadeBehaviour(), ammo=ammo)


class IncendiaryMissileCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 3

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("incendiary_missile", IncendiaryMissileBehaviour(), ammo=ammo)


class ArtilleryCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 3

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("artillery", ArtilleryBehaviour(), ammo=ammo)


class ThermobaricRocketCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 3

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("thermobaric_rocket", ThermobaricRocketBehaviour(), ammo=ammo)


class RecoveredWeaponCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("recovered_weapon", RecoveredWeaponBehaviour(), ammo=ammo)


class LightPistolCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("light_pistol", LightPistolBehaviour(), ammo=ammo)


class RustyPistolCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("rusty_pistol", RustyPistolBehaviour(), ammo=ammo)


class ImprovisedClubCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 8

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("improvised_club", ImprovisedClubBehaviour(), ammo=ammo)


class ImprovisedKnifeCreator(WeaponCreator):
    DEFAULT_AMMO_MIN = 1
    DEFAULT_AMMO_MAX = 8

    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("improvised_knife", ImprovisedKnifeBehaviour(), ammo=ammo)


class HeavyRifleCreator(WeaponCreator):
    def create_weapon(self, ammo: int) -> Weapon:
        return Weapon("heavy_rifle_01", AssaultRifleBehaviour(), ammo=ammo)


class WeaponRegistry:
    """Facade di retrocompatibilità — API pubblica invariata.

    Delega internamente ai ConcreteCreator GoF; tutto il codice esistente
    che chiama WeaponRegistry.*() continua a funzionare senza modifiche.
    """

    @staticmethod
    def rail_gun(ammo: int = -1) -> Weapon:
        return RailGunCreator().forge(ammo)

    @staticmethod
    def acid_gun(ammo: int = -1) -> Weapon:
        return AcidGunCreator().forge(ammo)

    @staticmethod
    def antimatter_grenade(qty: int = -1) -> Weapon:
        return AntimatterGrenadeCreator().forge(qty)

    @staticmethod
    def incendiary_missile(ammo: int = -1) -> Weapon:
        return IncendiaryMissileCreator().forge(ammo)

    @staticmethod
    def artillery(charges: int = -1) -> Weapon:
        return ArtilleryCreator().forge(charges)

    @staticmethod
    def thermobaric_rocket(ammo: int = -1) -> Weapon:
        return ThermobaricRocketCreator().forge(ammo)

    @staticmethod
    def recovered_weapon(ammo: int = -1) -> Weapon:
        return RecoveredWeaponCreator().forge(ammo)

    @staticmethod
    def light_pistol(ammo: int = -1) -> Weapon:
        return LightPistolCreator().forge(ammo)

    @staticmethod
    def rusty_pistol(ammo: int = -1) -> Weapon:
        return RustyPistolCreator().forge(ammo)

    @staticmethod
    def improvised_club(ammo: int = -1) -> Weapon:
        return ImprovisedClubCreator().forge(ammo)

    @staticmethod
    def improvised_knife(ammo: int = -1) -> Weapon:
        return ImprovisedKnifeCreator().forge(ammo)

    @staticmethod
    def heavy_rifle(ammo: int = -1) -> Weapon:
        return HeavyRifleCreator().forge(ammo)



class InventoryWeightManager:
    @staticmethod
    def max_weight(character_name: str) -> int:
        if character_name.lower() == "rivet":
            return Rivet_MAX_CARRY_WEIGHT
        return Echo_MAX_CARRY_WEIGHT

    @staticmethod
    def current_weight(inventory, weapon_list: list[Weapon] | None = None) -> int:
        item_weight   = sum(i.quantity for i in inventory.all_items())
        weapon_weight = sum(w.weight for w in (weapon_list or []))
        return item_weight + weapon_weight

    @staticmethod
    def can_add(character_name: str, inventory, item_weight: int,
                weapon_list: list[Weapon] | None = None) -> bool:
        current = InventoryWeightManager.current_weight(inventory, weapon_list)
        return current + item_weight <= InventoryWeightManager.max_weight(character_name)
