//! `complete_match_arms` fixture.
//!
//! `Direction` is a sealed enum.  `describe` matches over it but uses a
//! wildcard `_ => unreachable!()` arm instead of listing all variants
//! explicitly.  The `scalpel_complete_match_arms` E2E test places the
//! cursor on the `match` keyword and triggers rust-analyzer's
//! *Add Missing Match Arms* assist, replacing the wildcard with the
//! four named arms.

/// A cardinal direction.
#[derive(Debug, PartialEq, Eq)]
pub enum Direction {
    North,
    South,
    East,
    West,
}

/// Return a human-readable label for `dir`.
///
/// `complete_match_arms` target: the wildcard arm below should be
/// replaced with explicit `Direction::North | South | East | West` arms.
pub fn describe(dir: Direction) -> &'static str {
    match dir {
        Direction::North => "north",
        _ => "other",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn north_label() {
        assert_eq!(describe(Direction::North), "north");
    }

    #[test]
    fn south_label() {
        assert_eq!(describe(Direction::South), "other");
    }
}
