//! API route configuration

use actix_web::web;

use super::handlers;

/// Configure all API routes
pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api/v1")
            // Auth routes
            .service(
                web::scope("/auth")
                    .route("/login", web::post().to(handlers::login))
            )
            // Search routes
            .service(
                web::scope("/search")
                    .route("", web::post().to(handlers::search))
                    .route("/arxiv", web::post().to(handlers::search_arxiv))
            )
            // Document routes
            .service(
                web::scope("/documents")
                    .route("", web::post().to(handlers::ingest))
            )
            // Trading data routes
            .service(
                web::scope("/trading")
                    .route("/gex", web::get().to(handlers::get_gex))
            )
    )
    .route("/health", web::get().to(handlers::health));
}
