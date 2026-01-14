//! Actix-web API server

pub mod handlers;
pub mod middleware;
pub mod routes;
pub mod state;

pub use routes::configure_routes;
pub use state::AppState;
