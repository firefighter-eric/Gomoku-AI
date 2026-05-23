import pygame

from gomoku_ai.core import BLACK, WHITE
from gomoku_ai.game import MAX_UI_DEPTH, GameResult, GameSettings
from gomoku_ai.gui import (
    PygameGomoku,
    adjusted_settings,
    algorithm_label,
    board_frame_rect,
    board_to_pixel,
    build_buttons,
    build_dropdowns,
    create_layout,
    panel_buttons_top,
    panel_frame_rect,
    pixel_to_board,
    row_label_rect,
    settings_with_algorithm,
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


def test_board_and_panel_frames_align_with_visible_gap():
    layout = create_layout(15)

    board_rect = board_frame_rect(layout)
    panel_rect = panel_frame_rect(layout)

    assert panel_rect.top == board_rect.top
    assert panel_rect.bottom == board_rect.bottom
    assert panel_rect.left - board_rect.right == 28


def test_build_buttons_switches_to_settlement_controls_after_result():
    settings = GameSettings(mode="human-ai", size=15, human_stone=BLACK, depth=3)
    layout = create_layout(15)

    live_actions = [button.action for button in build_buttons(settings, None, layout)]
    settlement_actions = [
        button.action
        for button in build_buttons(settings, GameResult(winner=BLACK, moves=5, elapsed=0.1), layout)
    ]

    assert live_actions == ["mode_toggle", "resign", "restart", "exit"]
    assert settlement_actions == ["mode_toggle", "depth_dec", "depth_inc", "side_toggle", "restart", "exit"]


def test_build_dropdowns_exposes_algorithm_selectors_after_result():
    layout = create_layout(15)
    result = GameResult(winner=BLACK, moves=5, elapsed=0.1)

    human_dropdowns = build_dropdowns(GameSettings(mode="human-ai", ai_algorithm="v2"), result, layout)
    ai_dropdowns = build_dropdowns(
        GameSettings(mode="ai-ai", black_algorithm="v1", white_algorithm="v3"),
        result,
        layout,
    )

    assert [dropdown.action for dropdown in human_dropdowns] == ["ai_algorithm"]
    assert human_dropdowns[0].value == "v2"
    assert [dropdown.action for dropdown in ai_dropdowns] == ["black_algorithm", "white_algorithm"]
    assert ai_dropdowns[0].value == "v1"
    assert ai_dropdowns[1].value == "v3"


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


def test_adjusted_settings_toggles_between_human_and_ai_ai_modes():
    human_settings = GameSettings(mode="human-ai", size=15, human_stone=BLACK, ai_algorithm="v3", depth=6)

    ai_settings = adjusted_settings(human_settings, "mode_toggle")

    assert ai_settings.mode == "ai-ai"
    assert ai_settings.black_algorithm == "v3"
    assert ai_settings.white_algorithm == "v3"
    assert ai_settings.black_depth == 6
    assert ai_settings.white_depth == 6

    human_settings = adjusted_settings(
        GameSettings(
            mode="ai-ai",
            size=15,
            human_stone=BLACK,
            black_algorithm="v3",
            white_algorithm="v1",
            black_depth=5,
            white_depth=2,
        ),
        "mode_toggle",
    )

    assert human_settings.mode == "human-ai"
    assert human_settings.ai_algorithm == "v1"
    assert human_settings.depth == 2


def test_random_algorithm_disables_depth_controls():
    settings = GameSettings(mode="human-ai", size=15, ai_algorithm="v0")
    layout = create_layout(15)

    buttons = {
        button.action: button
        for button in build_buttons(settings, GameResult(winner=BLACK, moves=5, elapsed=0.1), layout)
    }

    assert "Difficulty: -" in settings_lines(settings)
    assert not buttons["depth_dec"].enabled
    assert not buttons["depth_inc"].enabled


def test_algorithm_labels_use_registry_and_version():
    assert algorithm_label("v0") == "random:v0"
    assert algorithm_label("v2") == "alpha-beta:v2"
    assert algorithm_label("v4") == "alpha-beta:v4"
    assert algorithm_label("v5") == "alpha-beta:v5"


def test_dropdown_selection_updates_algorithm_setting():
    settings = GameSettings(mode="ai-ai", black_algorithm="v1", white_algorithm="v2")

    settings = settings_with_algorithm(settings, "black_algorithm", "v3")
    settings = settings_with_algorithm(settings, "white_algorithm", "v0")

    assert settings.black_algorithm == "v3"
    assert settings.white_algorithm == "v0"


def test_dropdown_option_hit_testing_uses_expanded_menu_rows():
    layout = create_layout(15)
    dropdown = build_dropdowns(
        GameSettings(mode="human-ai", ai_algorithm="v2"),
        GameResult(winner=BLACK, moves=5, elapsed=0.1),
        layout,
        top=300,
    )[0]
    x, y, width, height = dropdown.rect

    assert dropdown.contains(x + 10, y + 10)
    assert dropdown.option_at(x + 10, y + height + 1) == "v0"
    assert dropdown.option_at(x + 10, y + height + 30 + 1) == "v1"
    assert dropdown.option_at(x + width + 1, y + height + 1) is None


def test_panel_buttons_follow_status_and_settings_text():
    settings = GameSettings(mode="ai-ai", size=15, black_depth=3, white_depth=2)
    status_line_count = 2
    settings_top = 58 + 48 + 28 + 28 + 36 + status_line_count * 22 + 12
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


def test_dropdown_click_selects_algorithm(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game = PygameGomoku(settings=GameSettings(mode="human-ai", size=5, ai_algorithm="v2", depth=1))
    try:
        game.session.result = GameResult(winner=BLACK, moves=5, elapsed=0.1)
        dropdown = game._dropdowns()[0]
        x, y, _width, height = dropdown.rect

        game._handle_click(x + 10, y + 10)
        game._handle_click(x + 10, y + height + 3 * 30 + 1)

        assert game.open_dropdown is None
        assert game.settings.ai_algorithm == "v3"
    finally:
        pygame.quit()


def test_gui_mode_toggle_click_restarts_live_game_as_ai_ai(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game = PygameGomoku(settings=GameSettings(mode="human-ai", size=5, human_stone=BLACK, ai_algorithm="v3", depth=2))
    try:
        game.session.board.play(2, 2, BLACK)
        button = next(button for button in game._buttons() if button.action == "mode_toggle")
        x, y, width, height = button.rect

        game._handle_click(x + width // 2, y + height // 2)

        assert game.settings.mode == "ai-ai"
        assert game.session.settings.mode == "ai-ai"
        assert game.session.board.move_count == 0
        assert game.session.is_ai_turn()
        assert game.settings.black_algorithm == "v3"
        assert game.settings.white_algorithm == "v3"
        assert game.message == "New game started."
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
