from __future__ import annotations

import threading

from games.orquantix.engine import TemperatureScale
from games.orquantix.vocabulary import Pools


class OrquantixState:
    """État d'Orquantix, isolé de la coquille.

    Vit côté serveur : c'est ce qui permet de quitter vers le menu et de
    retrouver sa partie en revenant.
    """

    def __init__(self) -> None:
        self.phase: str = "idle"  # idle | downloading | loading | ready | error
        self.progress: int = 0
        self.detail: str = ""
        self.model = None
        self.littre = None
        self.pools: Pools | None = None
        self.scale: TemperatureScale | None = None
        self.neighbours: list[tuple[str, float]] = []
        self.top1000: dict[str, int] = {}
        self.norm_to_model: dict[str, str] = {}
        self.difficulty_thresholds: list[float] = []
        self.mystery_word: str = ""
        self.difficulty: int = 0
        self.game_index: int = 0
        self.guesses: list[dict] = []
        self._lock = threading.Lock()

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "phase": self.phase,
                "progress": self.progress,
                "detail": self.detail,
            }
