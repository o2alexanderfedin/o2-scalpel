//! `extract_lifetime` fixture.
//!
//! `first_word` returns a `&str` slice of its input without an explicit
//! lifetime annotation.  The `scalpel_extract_lifetime` E2E test places
//! the cursor on the `&str` return token and triggers rust-analyzer's
//! *Extract Lifetime* assist, which introduces an explicit `'a` and
//! rewrites the signature to `fn first_word<'a>(s: &'a str) -> &'a str`.

/// Returns the first whitespace-delimited word in `s`.
///
/// Lifetime-extraction target: the returned reference borrows from `s`
/// but the signature currently has no explicit lifetime parameter.
pub fn first_word(s: &str) -> &str {
    s.split_whitespace().next().unwrap_or("")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_first() {
        assert_eq!(first_word("hello world"), "hello");
    }

    #[test]
    fn empty_string() {
        assert_eq!(first_word(""), "");
    }
}
