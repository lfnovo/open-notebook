//! Prior Notebook API Server

use actix_cors::Cors;
use actix_web::{middleware::Logger, web, App, HttpServer};
use anyhow::Result;
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use prior_notebook::{
    api::{configure_routes, AppState},
    config::Settings,
    core::{embedding::EmbeddingService, rag::{RagConfig, RagEngine}, vector_store::VectorStore},
    security::{auth::AuthService, zero_trust::{ZeroTrustConfig, ZeroTrustMiddleware}},
    storage::{QuestDbClient, RedisCache},
};

#[actix_web::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info,actix_web=debug".to_string()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    tracing::info!("Starting Prior Notebook API v{}", prior_notebook::VERSION);

    // Load configuration
    let settings = Settings::load()?;
    tracing::info!(
        "Loaded configuration, binding to {}:{}",
        settings.server.host,
        settings.server.port
    );

    // Initialize embedding service
    let embedding_service = EmbeddingService::new(
        &settings.search.embedding_model,
        settings.search.embedding_dimension,
    );

    // Initialize vector store
    let vector_store = VectorStore::new(
        &settings.database.qdrant_url,
        &settings.database.qdrant_collection,
        settings.search.embedding_dimension,
    )
    .await?;

    // Initialize RAG engine
    let rag_engine = RagEngine::new(
        embedding_service,
        Arc::new(vector_store),
        RagConfig::default(),
    )
    .await?;

    // Initialize auth service
    let auth_service = AuthService::new(
        settings.security.jwt_secret.clone(),
        settings.security.jwt_expiry_hours,
    );

    // Build app state
    let mut app_state = AppState::new(rag_engine, auth_service);

    // Optional: QuestDB client
    if let Ok(questdb) = QuestDbClient::new(
        &settings.database.questdb_host,
        settings.database.questdb_port,
    ) {
        app_state = app_state.with_questdb(questdb);
        tracing::info!("Connected to QuestDB");
    }

    // Optional: Redis cache
    if let Ok(cache) = RedisCache::new(
        &settings.database.redis_url,
        std::time::Duration::from_secs(300),
    )
    .await
    {
        app_state = app_state.with_cache(cache);
        tracing::info!("Connected to Redis");
    }

    let app_state = web::Data::new(app_state);

    // Zero Trust configuration
    let zero_trust_config = ZeroTrustConfig {
        allowed_networks: settings
            .security
            .allowed_wireguard_ips
            .iter()
            .filter_map(|ip| ip.parse().ok())
            .collect(),
        enabled: settings.security.enable_zero_trust,
        allow_localhost: true,
    };

    let host = settings.server.host.clone();
    let port = settings.server.port;
    let workers = settings.server.workers;

    tracing::info!("Starting HTTP server with {} workers", workers);

    HttpServer::new(move || {
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header()
            .max_age(3600);

        App::new()
            .app_data(app_state.clone())
            .wrap(Logger::default())
            .wrap(cors)
            .wrap(ZeroTrustMiddleware::new(zero_trust_config.clone()))
            .configure(configure_routes)
    })
    .workers(workers)
    .bind((host, port))?
    .run()
    .await?;

    Ok(())
}
