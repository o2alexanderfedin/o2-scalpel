//! `change_type_shape` fixture.
//!
//! `Point` is a named struct.  The `scalpel_change_type_shape` E2E test
//! places the cursor on the struct name and triggers rust-analyzer's
//! *Convert Named Struct to Tuple Struct* assist, transforming
//! `Point { x: f64, y: f64 }` into `Point(f64, f64)`.

/// A 2-D point with named fields.
///
/// `change_type_shape` target: rust-analyzer's
/// `convert_named_fields_to_tuple_variant` assist converts this to a
/// tuple struct when the cursor lands on the struct name.
#[derive(Debug, Clone, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    /// Create a new point.
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }

    /// Euclidean distance from the origin.
    pub fn magnitude(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn origin_magnitude() {
        let p = Point::new(0.0, 0.0);
        assert_eq!(p.magnitude(), 0.0);
    }

    #[test]
    fn three_four_five() {
        let p = Point::new(3.0, 4.0);
        assert_eq!(p.magnitude(), 5.0);
    }
}
