import pytest

from gomoku_ai.core import BLACK, Board
from gomoku_ai.players import PlayerSpec, RandomAI, available_algorithms, create_player


def test_available_algorithms_include_baseline_and_alphabeta():
    assert available_algorithms() == ("v0", "v1", "v2", "v3")


def test_create_player_uses_player_spec():
    player = create_player(BLACK, PlayerSpec("v0", seed=1))

    assert isinstance(player, RandomAI)
    assert player.stone == BLACK


def test_create_player_accepts_alphabeta_alias():
    player = create_player(BLACK, PlayerSpec("alpha-beta", depth=1))

    assert player.name == "v3"


def test_create_player_accepts_v1_alias():
    player = create_player(BLACK, PlayerSpec("v1", depth=1))

    assert player.name == "v1"


def test_create_player_accepts_v3_alias():
    player = create_player(BLACK, PlayerSpec("v3", depth=1))

    assert player.name == "v3"


def test_create_player_rejects_unknown_algorithm():
    with pytest.raises(ValueError):
        create_player(BLACK, PlayerSpec("unknown"))


def test_random_ai_returns_legal_move():
    board = Board(size=5)
    board.play(2, 2, BLACK)
    player = RandomAI(BLACK, seed=1)

    row, col = player.choose_move(board)

    assert board.is_empty_at(row, col)


def test_player_spec_labels_depth_for_alphabeta():
    assert PlayerSpec("v1", depth=3).label == "alpha-beta:v1(d3)"
    assert PlayerSpec("v2", depth=3).label == "alpha-beta:v2(d3)"
    assert PlayerSpec("v3", depth=3).label == "alpha-beta:v3(d3)"
    assert PlayerSpec("v0", depth=3).label == "random:v0"


def test_player_spec_exposes_registry_name_and_version():
    spec = PlayerSpec("v3", depth=3)

    assert spec.registry_name == "alpha-beta"
    assert spec.version == "v3"


def test_legacy_algorithm_names_are_aliases():
    assert PlayerSpec("random").normalized_algorithm == "v0"
    assert PlayerSpec("alphabeta-v1").normalized_algorithm == "v1"
    assert PlayerSpec("alphabeta").normalized_algorithm == "v3"
    assert PlayerSpec("alphabeta-v3").normalized_algorithm == "v3"
