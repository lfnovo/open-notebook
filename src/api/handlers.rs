//! API request handlers

use actix_web::{web, HttpResponse};
use serde::{Deserialize, Serialize};

use super::state::AppState;
use crate::core::document::SourceType;
use crate::security::auth::UserRole;

// ============ Request/Response Types ============

#[derive(Debug, Deserialize)]
pub struct SearchRequest {
    pub query: String,
    #[serde(default = "default_limit")]
    pub limit: usize,
}

fn default_limit() -> usize {
    10
}

#[derive(Debug, Serialize)]
pub struct SearchResponse {
    pub query: String,
    pub results: Vec<SearchResultItem>,
    pub context: String,
}

#[derive(Debug, Serialize)]
pub struct SearchResultItem {
    pub content: String,
    pub score: f32,
    pub source_type: String,
    pub source_title: String,
}

#[derive(Debug, Deserialize)]
pub struct IngestRequest {
    pub title: String,
    pub content: String,
    pub source_type: String,
    pub source_url: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct IngestResponse {
    pub document_id: String,
    pub chunks: usize,
}

#[derive(Debug, Deserialize)]
pub struct ArxivSearchRequest {
    pub query: String,
    #[serde(default = "default_arxiv_limit")]
    pub max_results: usize,
    pub ingest: bool,
}

fn default_arxiv_limit() -> usize {
    20
}

#[derive(Debug, Serialize)]
pub struct ArxivSearchResponse {
    pub query: String,
    pub papers: Vec<ArxivPaper>,
    pub ingested: usize,
}

#[derive(Debug, Serialize)]
pub struct ArxivPaper {
    pub arxiv_id: String,
    pub title: String,
    pub authors: Vec<String>,
    pub summary: String,
    pub url: String,
}

#[derive(Debug, Deserialize)]
pub struct GexRequest {
    pub symbol: String,
    #[serde(default = "default_days")]
    pub days: i32,
}

fn default_days() -> i32 {
    7
}

#[derive(Debug, Serialize)]
pub struct GexResponse {
    pub symbol: String,
    pub data: Vec<GexDataPoint>,
}

#[derive(Debug, Serialize)]
pub struct GexDataPoint {
    pub timestamp: i64,
    pub strike: f64,
    pub gex: f64,
    pub net_gex: f64,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Serialize)]
pub struct LoginResponse {
    pub token: String,
    pub expires_in: i64,
}

// ============ Handlers ============

/// Health check endpoint
pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "version": crate::VERSION
    }))
}

/// Search the knowledge base
pub async fn search(
    state: web::Data<AppState>,
    req: web::Json<SearchRequest>,
) -> actix_web::Result<HttpResponse> {
    let result = state
        .rag_engine
        .query(&req.query)
        .await
        .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?;

    let context = state.rag_engine.build_context(&result);

    let results: Vec<SearchResultItem> = result
        .context_chunks
        .into_iter()
        .map(|c| SearchResultItem {
            content: c.content,
            score: c.score,
            source_type: format!("{:?}", c.source_type),
            source_title: c.source_title,
        })
        .collect();

    Ok(HttpResponse::Ok().json(SearchResponse {
        query: req.query.clone(),
        results,
        context,
    }))
}

/// Ingest a document
pub async fn ingest(
    state: web::Data<AppState>,
    req: web::Json<IngestRequest>,
) -> actix_web::Result<HttpResponse> {
    use crate::core::document::Document;

    let source_type = match req.source_type.to_lowercase().as_str() {
        "pdf" => SourceType::Pdf,
        "arxiv" => SourceType::ArxivPaper,
        "web" => SourceType::WebPage,
        "questdb" => SourceType::QuestDb,
        _ => SourceType::Manual,
    };

    let mut document = Document::new(&req.title, &req.content, source_type);
    if let Some(url) = &req.source_url {
        document = document.with_source_url(url);
    }

    let doc_id = document.id;
    state
        .rag_engine
        .ingest_document(document.clone())
        .await
        .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?;

    Ok(HttpResponse::Created().json(IngestResponse {
        document_id: doc_id.to_string(),
        chunks: document.chunks.len(),
    }))
}

/// Search arXiv
pub async fn search_arxiv(
    state: web::Data<AppState>,
    req: web::Json<ArxivSearchRequest>,
) -> actix_web::Result<HttpResponse> {
    let documents = if req.ingest {
        state
            .rag_engine
            .search_and_ingest_arxiv(&req.query, req.max_results)
            .await
            .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?
    } else {
        // Just search without ingesting
        let searcher = crate::search::ArxivSearcher::new(50);
        let results = searcher
            .search(&req.query, req.max_results)
            .await
            .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?;

        results
            .into_iter()
            .map(|r| crate::core::document::Document::new(&r.title, &r.summary, SourceType::ArxivPaper))
            .collect()
    };

    let papers: Vec<ArxivPaper> = documents
        .iter()
        .map(|d| ArxivPaper {
            arxiv_id: d.metadata.arxiv_id.clone().unwrap_or_default(),
            title: d.title.clone(),
            authors: d.metadata.authors.clone(),
            summary: d.metadata.abstract_text.clone().unwrap_or_default(),
            url: d.source_url.clone().unwrap_or_default(),
        })
        .collect();

    Ok(HttpResponse::Ok().json(ArxivSearchResponse {
        query: req.query.clone(),
        papers,
        ingested: if req.ingest { documents.len() } else { 0 },
    }))
}

/// Get GEX data
pub async fn get_gex(
    state: web::Data<AppState>,
    req: web::Query<GexRequest>,
) -> actix_web::Result<HttpResponse> {
    let questdb = state
        .questdb
        .as_ref()
        .ok_or_else(|| actix_web::error::ErrorServiceUnavailable("QuestDB not configured"))?;

    let data = questdb
        .get_gex(&req.symbol, req.days)
        .await
        .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?;

    let data_points: Vec<GexDataPoint> = data
        .into_iter()
        .map(|g| GexDataPoint {
            timestamp: g.timestamp,
            strike: g.strike,
            gex: g.gex,
            net_gex: g.net_gex,
        })
        .collect();

    Ok(HttpResponse::Ok().json(GexResponse {
        symbol: req.symbol.clone(),
        data: data_points,
    }))
}

/// Login endpoint (simplified - would use DB in production)
pub async fn login(
    state: web::Data<AppState>,
    req: web::Json<LoginRequest>,
) -> actix_web::Result<HttpResponse> {
    // In production, validate against database
    // For now, just generate token for demo
    if req.email.is_empty() || req.password.is_empty() {
        return Err(actix_web::error::ErrorBadRequest("Email and password required"));
    }

    let token = state
        .auth_service
        .generate_token("user_001", &req.email, UserRole::User)
        .map_err(|e| actix_web::error::ErrorInternalServerError(e.to_string()))?;

    Ok(HttpResponse::Ok().json(LoginResponse {
        token,
        expires_in: 24 * 3600, // 24 hours
    }))
}
