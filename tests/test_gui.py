import pygame

from gomoku_ai.core import BLACK, WHITE
from gomoku_ai.game import MAX_UI_DEPTH, GameResult, GameSettings
from gomoku_ai.gui import (
    PygameGomoku,
    adjusted_settings,
    board_to_pixel,
    build_buttons,
    create_layout,
    panel_buttons_top,
    pixel_to_board,
    row_label_rect,
    settings_lines,
)


def test_gui_coordinate_mapping_round_trips_board_points():
    layout = create_layout(15)

    x, y = board_to_pixel(7, 7, layout)

    assert pixel_to_board(x, y, layout) == (7, 7)
    assert pixel_to_board(x + layout.cell_size // 4, y, layout) == (7, 7)


def test_gui_coordinate_mapping_rejects_gaps_and_outside_board():
    layout = create_layout(15)
    x, y = board_to_pixel(7, 7, layout)

    assert pixel_to_board(x + layout.cell_size, y + layout.cell_size // 2, layout) is None
    assert pixel_to_board(layout.left - layout.cell_size, layout.top, layout) is None


def test_row_labels_are_right_aligned_away_from_board_grid():
    pygame.font.init()
    font = pygame.font.SysFont("arial", 15)
    layout = create_layout(15)

    one_digit = row_label_rect(0, layout, font)
    two_digit = row_label_rect(14, layout, font)

    assert one_digit.right == two_digit.right == layout.left - 18
    assert two_digit.right <= layout.left - 16


def test_build_buttons_switches_to_settlement_controls_after_result():
    settings = GameSettings(mode="human-ai", size=15, human_stone=BLACK, depth=3)
    layout = create_layout(15)

    live_actions = [button.action for button in build_buttons(settings, None, layout)]
    settlement_actions = [
        button.action
        for button in build_buttons(settings, GameResult(winner=BLACK, moves=5, elapsed=0.1), layout)
    ]

    assert live_actions == ["resign", "restart", "exit"]
    assert settlement_actions == ["depth_dec", "depth_inc", "side_toggle", "restart", "exit"]


def test_button_hit_testing_returns_enabled_actions_only():
    settings = GameSettings(mode="ai-ai", size=15, black_depth=2, white_depth=3)
    layout = create_layout(15)
    button = build_buttons(settings, None, layout)[0]
    x, y, width, height = button.rect

    assert button.contains(x + width // 2, y + height // 2)
    assert not button.contains(x - 1, y + height // 2)


def test_adjusted_settings_clamps_depth_and_toggles_side():
    settings = GameSettings(mode="human-ai", size=15, human_stone=BLACK, depth=1)

    assert adjusted_settings(settings, "depth_dec").depth == 1
    assert adjusted_settings(settings, "depth_inc").depth == 2
    assert adjusted_settings(settings, "side_toggle").human_stone == WHITE

    high_settings = GameSettings(mode="human-ai", size=15, human_stone=BLACK, depth=MAX_UI_DEPTH)
    assert adjusted_settings(high_settings, "depth_inc").depth == MAX_UI_DEPTH


def test_adjusted_ai_ai_settings_are_independent():
    settings = GameSettings(mode="ai-ai", size=15, black_depth=MAX_UI_DEPTH, white_depth=1)

    adjusted = adjusted_settings(settings, "black_depth_inc")
    adjusted = adjusted_settings(adjusted, "white_depth_dec")

    assert adjusted.black_depth == MAX_UI_DEPTH
    assert adjusted.white_depth == 1


def test_panel_buttons_follow_status_and_settings_text():
    settings = GameSettings(mode="ai-ai", size=15, black_depth=3, white_depth=2)
    status_line_count = 2
    settings_top = 62 + 48 + 28 + 28 + 36 + status_line_count * 22 + 12
    settings_bottom = settings_top + len(settings_lines(settings)) * 28

    assert panel_buttons_top(settings, status_line_count) >= settings_bottom + 10
    assert panel_buttons_top(settings, 3) > panel_buttons_top(settings, 1)


def test_human_click_shows_move_and_ai_thinking_before_ai_turn(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game = PygameGomoku(settings=GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))
    try:
        x, y = board_to_pixel(2, 2, game.layout)

        game._handle_click(x, y)

        assert game.session.board.grid[2][2] == BLACK
        assert game.session.current == WHITE
        assert game.session.is_ai_turn()
        assert game.message == "AI (white) thinking..."
    finally:
        pygame.quit()


def test_gui_loop_flips_frame_before_ai_calculation(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game = PygameGomoku(settings=GameSettings(mode="human-ai", size=5, human_stone=BLACK, depth=1))
    calls = []

    class FakeClock:
        def tick(self, fps: int) -> None:
            calls.append(f"tick:{fps}")

    def handle_events() -> None:
        calls.append("events")
        game.running = False

    try:
        game.clock = FakeClock()
        monkeypatch.setattr(game, "_handle_events", handle_events)
        monkeypatch.setattr(game, "_draw", lambda: calls.append("draw"))
        monkeypatch.setattr(game, "_maybe_play_ai", lambda: calls.append("ai"))
        monkeypatch.setattr(pygame.display, "flip", lambda: calls.append("flip"))

        game.run()

        assert calls == ["events", "draw", "flip", "ai", "tick:60"]
    finally:
        pygame.quit()
