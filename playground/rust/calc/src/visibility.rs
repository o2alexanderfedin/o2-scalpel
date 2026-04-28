//! Visibility refactoring targets for `scalpel_change_visibility`.
#![allow(dead_code)]
//!
//! `promote_to_public` is declared `pub(super)` but is suitable for a
//! full `pub` promotion — the E2E test calls `scalpel_change_visibility`
//! to widen it.
//!
//! `demote_to_private` is declared `pub` but is not actually part of the
//! intended public API — the E2E test can narrow it to `pub(crate)`.

/// Returns a version string.  Declared `pub(super)` as a change_visibility
/// target: the E2E suite promotes this to `pub`.
pub(super) fn promote_to_public() -> &'static str {
    "calc 0.1.0"
}

/// Returns the build flavour.  Declared `pub` as a change_visibility
/// target: the E2E suite can demote this to `pub(crate)`.
pub fn demote_to_private() -> &'static str {
    "debug"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn promote_returns_version() {
        assert!(!promote_to_public().is_empty());
    }

    #[test]
    fn demote_returns_flavour() {
        assert!(!demote_to_private().is_empty());
    }
}
