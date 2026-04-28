//! Fixture types for the v1.3-E Stage-3 Rust facade E2E suite.
//!
//! Each sub-module is the target of one deferred facade:
//! - [`lifetimes`]  — `extract_lifetime`
//! - [`arms`]       — `complete_match_arms`
//! - [`returns`]    — `change_return_type`
//! - [`shapes`]     — `change_type_shape`
//! - [`member`]     — `generate_member`
//! - [`traits`]     — `generate_trait_impl_scaffold`
//! - [`globs`]      — `expand_glob_imports`

#![allow(dead_code)]
#![allow(unused_variables)]

pub mod arms;
pub mod globs;
pub mod lifetimes;
pub mod member;
pub mod returns;
pub mod shapes;
pub mod traits;
