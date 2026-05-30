"""test_screen_state.py — Pattern State: MenuScreen, ExploreScreen, BattleScreen (STA_01…17)."""
import unittest
import base_setup  # noqa: F401
import pygame
from game.controller.game_manager import GameManager


def _fonts():
    pygame.font.init()
    f = pygame.font.Font(None, 24)
    return {k: f for k in ('sm', 'md', 'lg', 'xl', 'title', 'bold', 'small', 'normal', 'large', 'huge')}


class TestMenuScreen(unittest.TestCase):

    def setUp(self):
        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()
        from game.screens.menu_screen import MenuScreen
        self.screen = MenuScreen(_fonts())
        self.surf = pygame.display.get_surface()

    def tearDown(self):
        GameManager.reset()

    # ── STA_01 ───────────────────────────────────────────────────────────────
    def test_STA_01_handle_quit(self):
        """STA_01 — MenuScreen.handle_event(QUIT) → gioco terminato (SystemExit o no-crash)."""
        ev = pygame.event.Event(pygame.QUIT)
        try:
            self.screen.handle_event(ev)
        except SystemExit:
            pass  # accettato: il gioco termina con sys.exit()

    # ── STA_02 ───────────────────────────────────────────────────────────────
    def test_STA_02_update(self):
        """STA_02 — MenuScreen.update() non solleva eccezioni."""
        self.screen.update()

    # ── STA_03 ───────────────────────────────────────────────────────────────
    def test_STA_03_draw(self):
        """STA_03 — MenuScreen.draw(surface) non solleva eccezioni."""
        self.screen.draw(self.surf)

    # ── STA_04 ───────────────────────────────────────────────────────────────
    def test_STA_04_on_enter(self):
        """STA_04 — MenuScreen.on_enter() non solleva eccezioni (risorse caricate)."""
        self.assertTrue(hasattr(self.screen, 'on_enter'),
                        "MenuScreen deve avere on_enter()")
        self.screen.on_enter()

    # ── STA_05 ───────────────────────────────────────────────────────────────
    def test_STA_05_on_exit(self):
        """STA_05 — MenuScreen.on_exit() non solleva eccezioni (risorse liberate)."""
        self.assertTrue(hasattr(self.screen, 'on_exit'),
                        "MenuScreen deve avere on_exit()")
        self.screen.on_exit()


class TestExploreScreen(unittest.TestCase):

    def setUp(self):
        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()
        from game.screens.explore_screen import ExploreScreen
        self.screen = ExploreScreen(_fonts())
        self.surf = pygame.display.get_surface()

    def tearDown(self):
        GameManager.reset()

    # ── STA_06 ───────────────────────────────────────────────────────────────
    def test_STA_06_keydown_wasd(self):
        """STA_06 — ExploreScreen gestisce KEYDOWN WASD senza eccezioni."""
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w, mod=0,
                                unicode='w', scancode=0)
        self.screen.handle_event(ev)

    # ── STA_07 ───────────────────────────────────────────────────────────────
    def test_STA_07_update(self):
        """STA_07 — ExploreScreen.update() non solleva eccezioni."""
        self.screen.update()

    # ── STA_08 ───────────────────────────────────────────────────────────────
    def test_STA_08_draw(self):
        """STA_08 — ExploreScreen.draw(surface) non solleva eccezioni."""
        self.screen.draw(self.surf)

    # ── STA_09 ───────────────────────────────────────────────────────────────
    def test_STA_09_on_enter(self):
        """STA_09 — ExploreScreen.on_enter() non solleva eccezioni (mappa caricata)."""
        self.assertTrue(hasattr(self.screen, 'on_enter'),
                        "ExploreScreen deve avere on_enter()")
        self.screen.on_enter()

    # ── STA_10 ───────────────────────────────────────────────────────────────
    def test_STA_10_on_exit(self):
        """STA_10 — ExploreScreen.on_exit() non solleva eccezioni."""
        self.assertTrue(hasattr(self.screen, 'on_exit'),
                        "ExploreScreen deve avere on_exit()")
        self.screen.on_exit()


class TestBattleScreen(unittest.TestCase):

    def setUp(self):
        GameManager.reset()
        gm = GameManager.get_instance()
        gm.initialize()
        from game.screens.battle_screen import BattleScreen
        self.screen = BattleScreen(_fonts())
        self.surf = pygame.display.get_surface()

    def tearDown(self):
        GameManager.reset()

    # ── STA_11 ───────────────────────────────────────────────────────────────
    def test_STA_11_keydown_enter(self):
        """STA_11 — BattleScreen gestisce KEYDOWN ENTER senza eccezioni."""
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0,
                                unicode='\r', scancode=0)
        self.screen.handle_event(ev)

    # ── STA_12 ───────────────────────────────────────────────────────────────
    def test_STA_12_update(self):
        """STA_12 — BattleScreen.update() non solleva eccezioni."""
        self.screen.update()

    # ── STA_13 ───────────────────────────────────────────────────────────────
    def test_STA_13_draw(self):
        """STA_13 — BattleScreen.draw(surface) non solleva eccezioni."""
        self.screen.draw(self.surf)

    # ── STA_14 ───────────────────────────────────────────────────────────────
    def test_STA_14_on_enter(self):
        """STA_14 — BattleScreen.on_enter() non solleva eccezioni (BattleSystem avviato)."""
        self.assertTrue(hasattr(self.screen, 'on_enter'),
                        "BattleScreen deve avere on_enter()")
        self.screen.on_enter()

    # ── STA_15 ───────────────────────────────────────────────────────────────
    def test_STA_15_on_exit(self):
        """STA_15 — BattleScreen.on_exit() non solleva eccezioni."""
        self.assertTrue(hasattr(self.screen, 'on_exit'),
                        "BattleScreen deve avere on_exit()")
        self.screen.on_exit()


class TestChangeScreen(unittest.TestCase):

    def setUp(self):
        GameManager.reset()
        self.gm = GameManager.get_instance()
        self.gm.initialize()

    def tearDown(self):
        GameManager.reset()

    # ── STA_16 ───────────────────────────────────────────────────────────────
    def test_STA_16_change_screen_to_explore(self):
        """STA_16 — change_screen('explore') → ExploreScreen attiva."""
        self.gm.change_screen("explore")
        self.assertEqual(self.gm.screen, "explore")

    # ── STA_17 ───────────────────────────────────────────────────────────────
    def test_STA_17_change_screen_to_battle(self):
        """STA_17 — change_screen('battle') → BattleScreen attiva."""
        self.gm.change_screen("battle")
        self.assertEqual(self.gm.screen, "battle")


if __name__ == "__main__":
    unittest.main()