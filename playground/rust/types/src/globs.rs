//! `expand_glob_imports` fixture.
//!
//! This module uses a glob import (`use std::collections::*;`).  The
//! `scalpel_expand_glob_imports` E2E test places the cursor on the `*`
//! token and triggers rust-analyzer's *Expand Glob Import* assist, which
//! replaces the glob with the explicit names that are actually used
//! (e.g. `HashMap`, `HashSet`).

use std::collections::*;

/// Build a character-frequency map for `text`.
///
/// `expand_glob_imports` target: the `HashMap` and `BTreeMap` names here
/// are resolved via the glob import above; the assist will expand the
/// glob to list them explicitly.
pub fn char_frequency(text: &str) -> HashMap<char, usize> {
    let mut map = HashMap::new();
    for ch in text.chars() {
        *map.entry(ch).or_insert(0) += 1;
    }
    map
}

/// Return a sorted list of unique characters in `text`.
pub fn unique_chars_sorted(text: &str) -> Vec<char> {
    let set: BTreeSet<char> = text.chars().collect();
    set.into_iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frequency_hello() {
        let freq = char_frequency("hello");
        assert_eq!(freq.get(&'l'), Some(&2));
        assert_eq!(freq.get(&'h'), Some(&1));
    }

    #[test]
    fn unique_chars() {
        let chars = unique_chars_sorted("banana");
        assert_eq!(chars, vec!['a', 'b', 'n']);
    }
}
