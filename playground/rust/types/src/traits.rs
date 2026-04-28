//! `generate_trait_impl_scaffold` fixture.
//!
//! `Describable` is a trait with a single required method.  `Widget`
//! declares itself as implementing `Describable` but has no `impl` block.
//! The `scalpel_generate_trait_impl_scaffold` E2E test places the cursor
//! on the type name `Widget` and triggers rust-analyzer's
//! *Implement Missing Trait Members* assist.

/// A trait requiring an object to produce a description.
///
/// `generate_trait_impl_scaffold` target: rust-analyzer's assist
/// generates an empty `impl Describable for Widget` skeleton.
pub trait Describable {
    /// Return a human-readable description.
    fn describe(&self) -> String;
}

/// A simple UI widget.
///
/// Does NOT yet implement `Describable` — that impl scaffold is generated
/// by the `scalpel_generate_trait_impl_scaffold` E2E test.
#[derive(Debug, Default)]
pub struct Widget {
    pub label: String,
}

impl Widget {
    /// Create a new widget with the given label.
    pub fn new(label: impl Into<String>) -> Self {
        Self { label: label.into() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn widget_label() {
        let w = Widget::new("button");
        assert_eq!(w.label, "button");
    }
}
