//! `change_return_type` fixture.
//!
//! `square` currently returns a concrete `i32`.  The
//! `scalpel_change_return_type` E2E test places the cursor on the
//! return-type token (`i32`) and triggers rust-analyzer's rewrite
//! assist to wrap it in `Option<i32>`.

/// Compute the square of `n`.
///
/// `change_return_type` target: cursor on the `i32` return type triggers
/// the *Wrap Return Type in Option* assist offered by rust-analyzer.
pub fn square(n: i32) -> i32 {
    n * n
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn squares_positive() {
        assert_eq!(square(4), 16);
    }

    #[test]
    fn squares_zero() {
        assert_eq!(square(0), 0);
    }
}
