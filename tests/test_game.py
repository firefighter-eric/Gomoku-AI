from gomoku_ai.core import BLACK, WHITE
from gomoku_ai.game import GameSession, GameSettings


def test_default_settings_use_depth_four():
    settings = GameSettings()

    assert settings.depth == 4
    assert settings.black_depth == 4
    assert settings.white_depth == 4
    assert settings.ai_algorithm == "v4"
    assert settings.black_algorithm == "v4"
    assert settings.white_algorithm == "v4"


def test_human_move_updates_board_and_turn():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))

    outcome = session.play_human_move(2, 2)

    assert outcome.kind == "played"
    assert outcome.move == (2, 2)
    assert session.board.grid[2][2] == BLACK
    assert session.current == WHITE
    assert session.is_ai_turn()


def test_invalid_move_does_not_advance_turn():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))

    outcome = session.play_human_move(-1, 0)

    assert outcome.kind == "invalid"
    assert session.board.move_count == 0
    assert session.current == BLACK


def test_session_finishes_on_winning_move():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))
    for col in range(4):
        session.board.play(0, col, BLACK)

    outcome = session.play_human_move(0, 4)

    assert outcome.result is not None
    assert outcome.result.winner == BLACK
    assert outcome.result.moves == 5
    assert session.result is outcome.result


def test_resign_awards_win_to_opponent():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=WHITE, depth=1))

    outcome = session.resign()

    assert outcome.result is not None
    assert outcome.result.winner == BLACK
    assert outcome.result.resigned


def test_restart_can_apply_new_settings():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))
    session.play_human_move(2, 2)

    session.restart(session.with_settings(depth=2, human_stone=WHITE))

    assert session.board.move_count == 0
    assert session.current == BLACK
    assert session.settings.depth == 2
    assert session.settings.human_stone == WHITE


def test_ai_ai_move_can_stop_at_max_moves():
    session = GameSession(
        GameSettings(
            mode="ai-ai",
            size=5,
            depth=1,
            black_depth=1,
            white_depth=1,
            max_moves=1,
        )
    )

    outcome = session.play_ai_move()

    assert outcome.kind == "stopped"
    assert outcome.result is not None
    assert outcome.result.winner is None
    assert outcome.result.moves == 1


def test_ai_players_can_use_configured_algorithms():
    session = GameSession(
        GameSettings(
            mode="ai-ai",
            size=5,
            black_algorithm="v0",
            white_algorithm="v0",
            max_moves=1,
        )
    )

    assert session.players[BLACK].name == "v0"
    assert session.players[WHITE].name == "v0"


def test_session_stops_before_move_when_max_moves_is_already_reached():
    session = GameSession(GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1, max_moves=0))

    outcome = session.play_human_move(2, 2)

    assert outcome.result is not None
    assert outcome.result.moves == 0
    assert session.board.move_count == 0
