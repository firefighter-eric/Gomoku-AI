use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn choose_move_v5(
    grid: Vec<i8>,
    size: usize,
    win_length: usize,
    stone: i8,
    depth: usize,
    candidate_radius: usize,
    candidate_limit: usize,
    seed: u64,
) -> Result<Vec<u32>, JsValue> {
    gomoku_ai_rust::choose_move_v5_flat(
        grid,
        size,
        win_length,
        stone,
        depth,
        candidate_radius,
        candidate_limit,
        seed,
    )
    .map(|result| vec![result.row as u32, result.col as u32])
    .map_err(|message| JsValue::from_str(&message))
}
