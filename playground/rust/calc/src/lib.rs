//! Minimal calculator library used as an E2E refactoring fixture.
//!
//! The inline modules below are intentional split_file targets: the E2E
//! test suite calls `scalpel_split_file` to carve each of `ast`, `parser`,
//! and `eval` into a separate sibling `.rs` file.
//!
//! `run` is the rename target: the E2E suite renames `parse_expr` inside
//! the parser module to `parse_expression`.
//!
//! The arithmetic in `eval::eval_add` contains an inline expression that
//! the `scalpel_extract` test pulls into a named helper.

pub mod ast {
    /// A node in the expression tree.
    #[derive(Debug, PartialEq, Eq)]
    pub enum Expr {
        /// Integer literal.
        Lit(i64),
        /// Binary addition of two sub-expressions.
        Add(Box<Expr>, Box<Expr>),
    }
}

pub mod parser {
    use super::ast::Expr;

    /// Tokenise `input` into a flat vec of tokens.
    ///
    /// Accepts only digits and `+`.  Returns `Err` on unknown characters.
    pub fn tokenize(input: &str) -> Result<Vec<String>, String> {
        let mut tokens = Vec::new();
        for ch in input.chars() {
            match ch {
                '0'..='9' => tokens.push(ch.to_string()),
                '+' => tokens.push("+".to_string()),
                ' ' | '\t' => {}
                other => return Err(format!("unexpected character: {:?}", other)),
            }
        }
        Ok(tokens)
    }

    /// Parse a flat token list into an `Expr`.
    ///
    /// This is the rename target for `scalpel_rename`: the E2E test
    /// renames `parse_expr` → `parse_expression` across the workspace.
    pub fn parse_expr(tokens: &[String]) -> Result<Expr, String> {
        let mut iter = tokens.iter().peekable();
        let lhs = parse_lit(&mut iter)?;
        if iter.peek().map(|s| s.as_str()) == Some("+") {
            iter.next(); // consume '+'
            let rhs = parse_lit(&mut iter)?;
            Ok(Expr::Add(Box::new(lhs), Box::new(rhs)))
        } else {
            Ok(lhs)
        }
    }

    fn parse_lit<'a>(
        iter: &mut impl Iterator<Item = &'a String>,
    ) -> Result<Expr, String> {
        match iter.next() {
            Some(tok) => tok
                .parse::<i64>()
                .map(Expr::Lit)
                .map_err(|_| format!("expected integer literal, got {:?}", tok)),
            None => Err("unexpected end of input".to_string()),
        }
    }
}

pub mod eval {
    use super::ast::Expr;

    /// Evaluate an `Expr` tree and return its integer value.
    pub fn eval(expr: &Expr) -> Result<i64, String> {
        match expr {
            Expr::Lit(n) => Ok(*n),
            Expr::Add(lhs, rhs) => {
                let a = eval(lhs)?;
                let b = eval(rhs)?;
                // extract candidate: the following two lines can be pulled
                // into a helper `fn add_values(a: i64, b: i64) -> i64`.
                let result = a + b;
                Ok(result)
            }
        }
    }
}

pub mod visibility;

/// Parse `input` and evaluate it, returning the integer result.
pub fn run(input: &str) -> Result<i64, String> {
    let tokens = parser::tokenize(input)?;
    let ast = parser::parse_expr(&tokens)?;
    eval::eval(&ast)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn one_plus_two() {
        assert_eq!(run("1 + 2").unwrap(), 3);
    }

    #[test]
    fn single_literal() {
        assert_eq!(run("7").unwrap(), 7);
    }

    #[test]
    fn unknown_char_errors() {
        assert!(run("1 @ 2").is_err());
    }
}
