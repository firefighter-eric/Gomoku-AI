use gomoku_ai_rust::choose_move_v5_flat;
use std::env;
use std::process;

fn main() {
    match run() {
        Ok(()) => {}
        Err(message) => {
            eprintln!("{message}");
            process::exit(2);
        }
    }
}

fn run() -> Result<(), String> {
    let mut size: Option<usize> = None;
    let mut win_length: usize = 5;
    let mut stone: Option<i8> = None;
    let mut depth: usize = 4;
    let mut candidate_radius: usize = 2;
    let mut candidate_limit: usize = 18;
    let mut seed: u64 = 20260521;
    let mut grid: Option<Vec<i8>> = None;

    let args: Vec<String> = env::args().skip(1).collect();
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--help" | "-h" => {
                print_help();
                return Ok(());
            }
            "--size" => size = Some(parse_next(&args, &mut index, "--size")?),
            "--win-length" => win_length = parse_next(&args, &mut index, "--win-length")?,
            "--stone" => stone = Some(parse_next(&args, &mut index, "--stone")?),
            "--depth" => depth = parse_next(&args, &mut index, "--depth")?,
            "--candidate-radius" => {
                candidate_radius = parse_next(&args, &mut index, "--candidate-radius")?
            }
            "--candidate-limit" => {
                candidate_limit = parse_next(&args, &mut index, "--candidate-limit")?
            }
            "--seed" => seed = parse_next(&args, &mut index, "--seed")?,
            "--grid" => {
                let value: String = parse_next(&args, &mut index, "--grid")?;
                grid = Some(parse_grid(&value)?);
            }
            option => return Err(format!("unknown option: {option}")),
        }
        index += 1;
    }

    let size = size.ok_or_else(|| "--size is required".to_string())?;
    let stone = stone.ok_or_else(|| "--stone is required".to_string())?;
    let grid = grid.ok_or_else(|| "--grid is required".to_string())?;

    let result = choose_move_v5_flat(
        grid,
        size,
        win_length,
        stone,
        depth,
        candidate_radius,
        candidate_limit,
        seed,
    )?;
    println!(
        "{} {} {} {}",
        result.row, result.col, result.nodes, result.cache_hits
    );
    Ok(())
}

fn parse_next<T: std::str::FromStr>(
    args: &[String],
    index: &mut usize,
    option: &str,
) -> Result<T, String> {
    *index += 1;
    let value = args
        .get(*index)
        .ok_or_else(|| format!("{option} requires a value"))?;
    value
        .parse::<T>()
        .map_err(|_| format!("invalid value for {option}: {value}"))
}

fn parse_grid(value: &str) -> Result<Vec<i8>, String> {
    value
        .split(',')
        .map(|part| {
            part.parse::<i8>()
                .map_err(|_| format!("invalid grid value: {part}"))
        })
        .collect()
}

fn print_help() {
    println!(
        "gomoku-ai-rust-engine --size N --stone 1|-1 --grid comma-separated-cells [--depth N]"
    );
}
