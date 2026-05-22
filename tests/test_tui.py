import curses

from gomoku_ai.core import BLACK, WHITE
from gomoku_ai.game import MAX_UI_DEPTH, GameResult
from gomoku_ai.tui import BoardGeometry, _TuiGame, board_to_screen, screen_to_board


def test_board_to_screen_uses_stable_cell_spacing():
    geometry = BoardGeometry(top=3, left=5, cell_width=3)

    assert board_to_screen(0, 0, geometry) == (4, 5)
    assert board_to_screen(7, 7, geometry) == (11, 26)


def test_screen_to_board_accepts_cell_and_nearby_space():
    geometry = BoardGeometry(top=3, left=5, cell_width=3)

    assert screen_to_board(11, 26, size=15, geometry=geometry) == (7, 7)
    assert screen_to_board(11, 27, size=15, geometry=geometry) == (7, 7)


def test_screen_to_board_rejects_outside_board():
    geometry = BoardGeometry(top=3, left=5, cell_width=3)

    assert screen_to_board(3, 5, size=15, geometry=geometry) is None
    assert screen_to_board(11, 3, size=15, geometry=geometry) is None
    assert screen_to_board(11, 49, size=15, geometry=geometry) is None
    assert screen_to_board(20, 5, size=15, geometry=geometry) is None


def test_finish_keeps_result_without_blocking_for_exit():
    window = FakeWindow()

    game = _make_game(window)
    game.board.play(2, 2, BLACK)
    result = game._finish(BLACK)

    assert result.winner == BLACK
    assert result.moves == 1
    assert "Black wins" in game.message
    assert window.getch_calls == 0


def test_settlement_menu_can_update_settings_and_restart(monkeypatch):
    window = FakeWindow(keys=[curses.KEY_RIGHT, curses.KEY_DOWN, curses.KEY_RIGHT, curses.KEY_DOWN, ord("\n")])
    flushed = []
    monkeypatch.setattr(curses, "flushinp", lambda: flushed.append(True))

    game = _make_game(window)
    restart = game._settlement_menu(GameResult(winner=BLACK, moves=1, elapsed=0.1))

    assert restart is True
    assert game.depth == 2
    assert game.human_stone == WHITE
    assert flushed == [True]
    assert -1 in window.timeouts
    assert window.getch_calls == 5


def test_settlement_menu_clamps_depth_to_ten(monkeypatch):
    keys = [curses.KEY_RIGHT] * 20 + [curses.KEY_DOWN, curses.KEY_DOWN, ord("\n")]
    window = FakeWindow(keys=keys)
    monkeypatch.setattr(curses, "flushinp", lambda: None)

    game = _make_game(window)
    restart = game._settlement_menu(GameResult(winner=BLACK, moves=1, elapsed=0.1))

    assert restart is True
    assert game.depth == MAX_UI_DEPTH


def test_settlement_menu_can_exit(monkeypatch):
    window = FakeWindow(keys=[ord("q")])
    flushed = []
    monkeypatch.setattr(curses, "flushinp", lambda: flushed.append(True))

    game = _make_game(window)
    restart = game._settlement_menu(GameResult(winner=BLACK, moves=1, elapsed=0.1))

    assert restart is False
    assert flushed == [True]


def test_tui_settings_preserve_algorithm_choices():
    game = _make_game(FakeWindow(), ai_algorithm="v0", black_algorithm="v0")

    settings = game._settings()

    assert settings.ai_algorithm == "v0"
    assert settings.black_algorithm == "v0"
    assert settings.white_algorithm == "v3"


def _make_game(window, **overrides):
    values = {
        "ai_algorithm": "v3",
        "black_algorithm": "v3",
        "white_algorithm": "v3",
    }
    values.update(overrides)
    return _TuiGame(
        stdscr=window,
        mode="human-ai",
        size=5,
        human_stone=BLACK,
        ai_algorithm=values["ai_algorithm"],
        depth=1,
        black_algorithm=values["black_algorithm"],
        white_algorithm=values["white_algorithm"],
        black_depth=1,
        white_depth=1,
        delay=0,
        max_moves=None,
    )


class FakeWindow:
    def __init__(self, keys=None):
        self.keys = list(keys or [])
        self.timeouts = []
        self.getch_calls = 0

    def erase(self):
        return None

    def getmaxyx(self):
        return 40, 100

    def addstr(self, *_args):
        return None

    def refresh(self):
        return None

    def timeout(self, value):
        self.timeouts.append(value)

    def getch(self):
        self.getch_calls += 1
        if self.keys:
            return self.keys.pop(0)
        return ord("q")
