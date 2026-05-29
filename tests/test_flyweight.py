"""test_flyweight.py — Pattern Flyweight: AssetCache (FLY_01…10)."""
import unittest
import base_setup  # noqa: F401
import pygame
from game.view.asset_loader import AssetCache


class TestFlyweight(unittest.TestCase):

    def setUp(self):
        AssetCache.clear()

    def tearDown(self):
        AssetCache.clear()

    def test_FLY_01_get_surface_returns_pygame_surface(self):
        """FLY_01 — get_surface(path, alpha=True) restituisce una Surface pygame valida."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "tile.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            surf = AssetCache.get_surface(img_path, alpha=False)
            self.assertIsInstance(surf, pygame.Surface)

    def test_FLY_02_same_instance_on_second_call(self):
        """FLY_02 — seconda chiamata con stesso path → stessa istanza (is)."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "tile2.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            s1 = AssetCache.get_surface(img_path, alpha=False)
            s2 = AssetCache.get_surface(img_path, alpha=False)
            self.assertIs(s1, s2)

    def test_FLY_03_get_scaled_adds_to_scaled_cache(self):
        """FLY_03 — get_scaled(path, scale=2) aggiunge entry alla cache scaled."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "s.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            AssetCache.get_scaled(img_path, scale=2, alpha=False)
            self.assertGreaterEqual(len(AssetCache._scaled), 1)

    def test_FLY_04_different_scale_different_entry(self):
        """FLY_04 — scale=2 e scale=3 producono entry distinte nella cache."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "s2.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            s2 = AssetCache.get_scaled(img_path, scale=2, alpha=False)
            s3 = AssetCache.get_scaled(img_path, scale=3, alpha=False)
            self.assertIsNot(s2, s3)

    def test_FLY_05_get_tile_returns_surface(self):
        """FLY_05 — get_tile() da un tileset valido restituisce una Surface."""
        tileset = pygame.Surface((64, 64))
        result = AssetCache.get_tile(tileset, col=0, row=0, tw=32, th=32, scale=1)
        self.assertIsInstance(result, pygame.Surface)
        self.assertEqual(result.get_size(), (32, 32))

    def test_FLY_06_get_tile_same_instance_on_second_call(self):
        """FLY_06 — seconda chiamata get_tile con stessi args → stessa istanza (is)."""
        tileset = pygame.Surface((64, 64))
        t1 = AssetCache.get_tile(tileset, col=0, row=0, tw=32, th=32, scale=1)
        t2 = AssetCache.get_tile(tileset, col=0, row=0, tw=32, th=32, scale=1)
        self.assertIs(t1, t2)

    def test_FLY_07_clear_resets_surfaces_count(self):
        """FLY_07 — AssetCache.clear() → surfaces_cached == 0."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "test.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            AssetCache.get_surface(img_path, alpha=False)
            AssetCache.clear()
            self.assertEqual(AssetCache.stats()["surfaces_cached"], 0)

    def test_FLY_08_stats_surfaces_cached_count(self):
        """FLY_08 — dopo 3 get_surface distinte → stats()['surfaces_cached'] == 3."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                p = os.path.join(tmp, f"img{i}.png")
                pygame.image.save(pygame.Surface((8, 8)), p)
                AssetCache.get_surface(p, alpha=False)
            self.assertEqual(AssetCache.stats()["surfaces_cached"], 3)

    def test_FLY_09_get_surface_without_alpha(self):
        """FLY_09 — get_surface(path, alpha=False) restituisce Surface senza alpha."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            img_path = os.path.join(tmp, "noalpha.png")
            pygame.image.save(pygame.Surface((8, 8)), img_path)
            surf = AssetCache.get_surface(img_path, alpha=False)
            self.assertIsInstance(surf, pygame.Surface)
            self.assertEqual(surf.get_masks()[3], 0)

    def test_FLY_10_nonexistent_raises(self):
        """FLY_10 — get_surface su file inesistente → eccezione."""
        with self.assertRaises(Exception):
            AssetCache.get_surface("/nonexistent_path_xyz_abc.png", alpha=False)


if __name__ == "__main__":
    unittest.main()