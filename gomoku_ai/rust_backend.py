from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gomoku_ai.core import Board

ENGINE_NAME = "gomoku-ai-rust-engine"
ENV_ENGINE_PATH = "GOMOKU_RUST_ENGINE"


def rust_backend_available() -> bool:
    return _engine_path() is not None


def rust_backend_name() -> str:
    path = _engine_path()
    return "rust-engine" if path is not None else "python-v4-fallback"


def choose_move_v5(
    board: Board,
    stone: int,
    *,
    depth: int,
    candidate_radius: int,
    candidate_limit: int,
    seed: int,
) -> tuple[int, int, int, int]:
    path = _engine_path()
    if path is None:
        raise RuntimeError(
            "Rust engine is not built. Run `cargo build --release` to enable alpha-beta:v5 acceleration."
        )

    flat_grid = ",".join(str(value) for row in board.grid for value in row)
    command = [
        str(path),
        "--size",
        str(board.size),
        "--win-length",
        str(board.win_length),
        "--stone",
        str(stone),
        "--depth",
        str(depth),
        "--candidate-radius",
        str(candidate_radius),
        "--candidate-limit",
        str(candidate_limit),
        "--seed",
        str(seed),
        "--grid",
        flat_grid,
    ]
    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Rust engine failed: {message}")

    parts = completed.stdout.strip().split()
    if len(parts) != 4:
        raise RuntimeError(f"Rust engine returned unexpected output: {completed.stdout!r}")
    row, col, nodes, cache_hits = (int(part) for part in parts)
    return row, col, nodes, cache_hits


def _engine_path() -> Path | None:
    configured = os.environ.get(ENV_ENGINE_PATH)
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_file() else None

    suffix = ".exe" if os.name == "nt" else ""
    for root in _candidate_roots():
        for profile in ("release", "debug"):
            path = root / "target" / profile / f"{ENGINE_NAME}{suffix}"
            if path.is_file():
                return path
    return None


def _candidate_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    for root in (Path.cwd(), Path(__file__).resolve().parents[1]):
        for candidate in (root, *root.parents):
            if candidate not in roots:
                roots.append(candidate)
    return tuple(roots)
