"""
encounters.py — Tabella degli incontri casuali in esplorazione.

``ENCOUNTERS`` è una lista di factory callable: ogni elemento è una lambda
senza argomenti che, quando invocata, restituisce la lista di ``Enemy``
per quell'incontro specifico.

Usare callable anziché liste pre-create garantisce che ogni incontro
produca nuove istanze di Enemy con HP e stati azzerati.

Esempio di utilizzo in ``ExploreScreen``::

    import random
    from game.world.encounters import ENCOUNTERS

    factory = random.choice(ENCOUNTERS)
    enemies = factory()   # lista di Enemy freschi
"""

from __future__ import annotations

from game.model.enemy import EnemyFactory

# Lista di factory callable; ogni elemento produce un gruppo di nemici distinto.
# L'ordine suggerisce difficoltà crescente, ma la selezione è casuale.
ENCOUNTERS: list = [
    lambda: [EnemyFactory.create_infetto()],                                      # 1 Infetto
    lambda: [EnemyFactory.create_infetto(), EnemyFactory.create_infetto()],       # 2 Infetti
    lambda: [EnemyFactory.create_orda()],                                         # 1 Orda
    lambda: [EnemyFactory.create_corazzato()],                                    # 1 Corazzato
    lambda: [EnemyFactory.create_meat_giant()],                                   # Boss: Gigante
]
