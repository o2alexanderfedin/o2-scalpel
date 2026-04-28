//! `generate_member` fixture.
//!
//! `Counter` exposes its `value` field only via a direct pub access.
//! The `scalpel_generate_member` E2E test places the cursor on the
//! field name and triggers rust-analyzer's *Generate Getter* assist,
//! which adds a `pub fn value(&self) -> u64` method to the impl block.

/// A monotonically-increasing counter.
///
/// `generate_member` target: cursor on `value` field name triggers the
/// *Generate Getter* assist in rust-analyzer.
#[derive(Debug, Default)]
pub struct Counter {
    pub value: u64,
}

impl Counter {
    /// Create a new counter starting at zero.
    pub fn new() -> Self {
        Self::default()
    }

    /// Increment the counter.
    pub fn increment(&mut self) {
        self.value += 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starts_at_zero() {
        let c = Counter::new();
        assert_eq!(c.value, 0);
    }

    #[test]
    fn increments() {
        let mut c = Counter::new();
        c.increment();
        c.increment();
        assert_eq!(c.value, 2);
    }
}
