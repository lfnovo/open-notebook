//! Google search via SerpAPI

use anyhow::{Context, Result};
use async_trait::async_trait;
use serde::Deserialize;

use super::{ExternalSearchResult, SearchProvider};

/// Google search client using SerpAPI
pub struct GoogleSearcher {
    client: reqwest::Client,
    api_key: String,
}

#[derive(Debug, Deserialize)]
struct SerpApiResponse {
    organic_results: Option<Vec<OrganicResult>>,
}

#[derive(Debug, Deserialize)]
struct OrganicResult {
    title: String,
    link: String,
    snippet: Option<String>,
}

impl GoogleSearcher {
    pub fn new(api_key: String) -> Self {
        Self {
            client: reqwest::Client::new(),
            api_key,
        }
    }
}

#[async_trait]
impl SearchProvider for GoogleSearcher {
    async fn search(&self, query: &str, max_results: usize) -> Result<Vec<ExternalSearchResult>> {
        let url = format!(
            "https://serpapi.com/search.json?q={}&api_key={}&num={}",
            urlencoding::encode(query),
            self.api_key,
            max_results
        );

        let response: SerpApiResponse = self
            .client
            .get(&url)
            .send()
            .await
            .context("Failed to query SerpAPI")?
            .json()
            .await
            .context("Failed to parse SerpAPI response")?;

        let results = response
            .organic_results
            .unwrap_or_default()
            .into_iter()
            .map(|r| ExternalSearchResult {
                title: r.title,
                summary: r.snippet.unwrap_or_default(),
                url: r.link,
                source: "Google".to_string(),
                authors: vec![],
                published: None,
                arxiv_id: String::new(),
            })
            .collect();

        Ok(results)
    }

    fn name(&self) -> &str {
        "Google"
    }
}
