//! Search providers for external data sources

pub mod arxiv;
pub mod google;
pub mod pdf;

pub use arxiv::ArxivSearcher;
pub use google::GoogleSearcher;
pub use pdf::PdfProcessor;

use anyhow::Result;
use async_trait::async_trait;
use chrono::{DateTime, Utc};

/// Generic search result
#[derive(Debug, Clone)]
pub struct ExternalSearchResult {
    pub title: String,
    pub summary: String,
    pub url: String,
    pub source: String,
    pub authors: Vec<String>,
    pub published: Option<DateTime<Utc>>,
    pub arxiv_id: String,
}

/// Search provider trait
#[async_trait]
pub trait SearchProvider: Send + Sync {
    async fn search(&self, query: &str, max_results: usize) -> Result<Vec<ExternalSearchResult>>;
    fn name(&self) -> &str;
}
