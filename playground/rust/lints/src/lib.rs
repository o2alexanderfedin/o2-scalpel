//! Lint-pattern fixtures for `scalpel_inline` and `scalpel_change_visibility`.
//!
//! # Facade targets
//!
//! ## `scalpel_inline`
//! `report` calls `sum_helper` exactly once.  The E2E test inlines
//! `sum_helper` at its single call site, collapsing the two functions into
//! one.  After inlining, `sum_helper` is removed and `report`'s body
//! becomes `items.iter().sum()` directly.
//!
//! ## `scalpel_change_visibility`
//! `unused_pub` is declared `pub` but is never called outside this crate.
//! The E2E test narrows it to `pub(crate)` (or to private, depending on
//! the rust-analyzer assist offered).

/// Computes the sum of `items` by delegating to `sum_helper`.
///
/// `sum_helper` is the inline target: after `scalpel_inline`, this
/// function's body becomes `items.iter().sum()` directly.
pub fn report(items: &[i64]) -> i64 {
    sum_helper(items)
}

/// Declared `pub` but never used outside this crate — a
/// `scalpel_change_visibility` target.  The E2E test narrows this to
/// `pub(crate)`.
pub fn unused_pub() -> i64 {
    42
}

/// Single-use helper — the inline candidate.
///
/// Called only by `report`; the E2E test inlines it there and removes
/// this definition.
fn sum_helper(items: &[i64]) -> i64 {
    items.iter().sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sums() {
        assert_eq!(report(&[1, 2, 3]), 6);
    }

    #[test]
    fn empty_slice() {
        assert_eq!(report(&[]), 0);
    }

    #[test]
    fn unused_pub_returns_42() {
        assert_eq!(unused_pub(), 42);
    }
}
