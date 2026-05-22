from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Protocol

from gomoku_ai.ai import AlphaBetaAI, AlphaBetaV1AI, AlphaBetaV3AI, AlphaBetaV4AI, generate_candidate_moves
from gomoku_ai.core import BLACK, WHITE, Board

ALGORITHM_NAMES = ("v0", "v1", "v2", "v3", "v4")
REGISTRY_NAME_CHOICES = ("random", "alpha-beta")
REGISTRY_NAMES = {
    "v0": "random",
    "v1": "alpha-beta",
    "v2": "alpha-beta",
    "v3": "alpha-beta",
    "v4": "alpha-beta",
}


class GomokuPlayer(Protocol):
    stone: int
    name: str

    def choose_move(self, board: Board) -> tuple[int, int]:
        """Return a legal move for the current board."""
        ...


@dataclass(frozen=True)
class PlayerSpec:
    algorithm: str = "v4"
    depth: int = 4
    seed: int = 20260521

    @property
    def normalized_algorithm(self) -> str:
        return normalize_algorithm(self.algorithm)

    @property
    def registry_name(self) -> str:
        return REGISTRY_NAMES[self.normalized_algorithm]

    @property
    def version(self) -> str:
        return self.normalized_algorithm

    @property
    def label(self) -> str:
        algorithm = self.normalized_algorithm
        if algorithm == "v0":
            return f"{self.registry_name}:{algorithm}"
        return f"{self.registry_name}:{algorithm}(d{self.depth})"


class RandomAI:
    """Simple baseline AI for smoke tests and algorithm comparison."""

    name = "v0"

    def __init__(self, stone: int, seed: int = 20260521) -> None:
        if stone not in (BLACK, WHITE):
            raise ValueError("AI stone must be BLACK or WHITE")
        self.stone = stone
        self._rng = Random(seed)

    def choose_move(self, board: Board) -> tuple[int, int]:
        candidates = generate_candidate_moves(board)
        if not candidates:
            candidates = board.legal_moves()
        if not candidates:
            raise ValueError("cannot choose a move on a full board")
        return self._rng.choice(candidates)


def available_algorithms() -> tuple[str, ...]:
    return ALGORITHM_NAMES


def normalize_algorithm(algorithm: str) -> str:
    value = algorithm.strip().lower().replace("_", "-")
    aliases = {
        "random": "v0",
        "baseline": "v0",
        "alpha-beta-v1": "v1",
        "alphabeta-v1": "v1",
        "alphabeta_v1": "v1",
        "alpha-beta": "v4",
        "alpha_beta": "v4",
        "alphabeta": "v4",
        "ab": "v4",
        "alpha-beta-v2": "v2",
        "alphabeta-v2": "v2",
        "alphabeta_v2": "v2",
        "alpha-beta-v3": "v3",
        "alphabeta-v3": "v3",
        "alphabeta_v3": "v3",
        "alpha-beta-v4": "v4",
        "alphabeta-v4": "v4",
        "alphabeta_v4": "v4",
        "pattern": "v4",
    }
    value = aliases.get(value, value)
    if value not in ALGORITHM_NAMES:
        names = ", ".join(ALGORITHM_NAMES)
        raise ValueError(f"unknown algorithm: {algorithm!r}. Available algorithms: {names}")
    return value


def resolve_algorithm_version(registry_name: str | None, version: str | None = None) -> str:
    """Resolve a registry name plus version into a concrete algorithm version."""

    registry_value = (registry_name or "alpha-beta").strip().lower().replace("_", "-")
    version_value = normalize_algorithm(version) if version is not None else None

    if registry_value in REGISTRY_NAME_CHOICES:
        default_version = "v0" if registry_value == "random" else "v4"
        resolved = version_value or default_version
        if REGISTRY_NAMES[resolved] != registry_value:
            raise ValueError(f"version {resolved!r} does not belong to registry {registry_value!r}")
        return resolved

    resolved = normalize_algorithm(registry_value)
    if version_value is not None and version_value != resolved:
        raise ValueError(f"conflicting algorithm version: {registry_name!r} with {version_value!r}")
    return resolved


def create_player(stone: int, spec: PlayerSpec | None = None) -> GomokuPlayer:
    spec = spec or PlayerSpec()
    algorithm = spec.normalized_algorithm
    if algorithm == "v0":
        return RandomAI(stone, seed=spec.seed)
    if algorithm == "v1":
        return AlphaBetaV1AI(stone, depth=spec.depth, seed=spec.seed)
    if algorithm == "v2":
        return AlphaBetaAI(stone, depth=spec.depth, seed=spec.seed)
    if algorithm == "v3":
        return AlphaBetaV3AI(stone, depth=spec.depth, seed=spec.seed)
    if algorithm == "v4":
        return AlphaBetaV4AI(stone, depth=spec.depth, seed=spec.seed)
    raise AssertionError(f"unhandled algorithm: {algorithm}")
