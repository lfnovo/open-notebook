//! arXiv paper search

use anyhow::{Context, Result};
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::Deserialize;

use super::{ExternalSearchResult, SearchProvider};

/// arXiv search client
pub struct ArxivSearcher {
    client: reqwest::Client,
    max_results: usize,
}

#[derive(Debug, Deserialize)]
struct ArxivFeed {
    entry: Option<Vec<ArxivEntry>>,
}

#[derive(Debug, Deserialize)]
struct ArxivEntry {
    id: String,
    title: String,
    summary: String,
    author: Vec<ArxivAuthor>,
    published: String,
    #[serde(rename = "link")]
    links: Vec<ArxivLink>,
}

#[derive(Debug, Deserialize)]
struct ArxivAuthor {
    name: String,
}

#[derive(Debug, Deserialize)]
struct ArxivLink {
    #[serde(rename = "@href")]
    href: String,
    #[serde(rename = "@type")]
    link_type: Option<String>,
}

impl ArxivSearcher {
    pub fn new(max_results: usize) -> Self {
        Self {
            client: reqwest::Client::new(),
            max_results,
        }
    }

    /// Parse arXiv ID from URL
    fn parse_arxiv_id(url: &str) -> String {
        url.rsplit('/')
            .next()
            .unwrap_or("")
            .to_string()
    }

    /// Parse datetime from arXiv format
    fn parse_datetime(s: &str) -> Option<DateTime<Utc>> {
        DateTime::parse_from_rfc3339(s)
            .ok()
            .map(|dt| dt.with_timezone(&Utc))
    }
}

#[async_trait]
impl SearchProvider for ArxivSearcher {
    async fn search(&self, query: &str, max_results: usize) -> Result<Vec<ExternalSearchResult>> {
        let limit = max_results.min(self.max_results);
        let encoded_query = urlencoding::encode(query);

        let url = format!(
            "http://export.arxiv.org/api/query?search_query=all:{}&start=0&max_results={}",
            encoded_query, limit
        );

        let response = self
            .client
            .get(&url)
            .header("User-Agent", "PriorNotebook/1.0")
            .send()
            .await
            .context("Failed to query arXiv API")?;

        let text = response.text().await.context("Failed to read arXiv response")?;

        // Parse XML response (simplified - would use quick-xml in production)
        let results = self.parse_atom_feed(&text)?;

        Ok(results)
    }

    fn name(&self) -> &str {
        "arXiv"
    }
}

impl ArxivSearcher {
    /// Parse Atom feed from arXiv (simplified parser)
    fn parse_atom_feed(&self, xml: &str) -> Result<Vec<ExternalSearchResult>> {
        let mut results = Vec::new();

        // Simple regex-based parsing for demo (use quick-xml in production)
        let entry_re = regex::Regex::new(r"<entry>(.*?)</entry>").unwrap();
        let id_re = regex::Regex::new(r"<id>(.*?)</id>").unwrap();
        let title_re = regex::Regex::new(r"<title>(.*?)</title>").unwrap();
        let summary_re = regex::Regex::new(r"<summary>(.*?)</summary>").unwrap();
        let author_re = regex::Regex::new(r"<name>(.*?)</name>").unwrap();
        let published_re = regex::Regex::new(r"<published>(.*?)</published>").unwrap();

        for entry_match in entry_re.captures_iter(xml) {
            let entry = &entry_match[1];

            let id = id_re
                .captures(entry)
                .map(|c| c[1].to_string())
                .unwrap_or_default();

            let title = title_re
                .captures(entry)
                .map(|c| c[1].trim().replace('\n', " "))
                .unwrap_or_default();

            let summary = summary_re
                .captures(entry)
                .map(|c| c[1].trim().replace('\n', " "))
                .unwrap_or_default();

            let authors: Vec<String> = author_re
                .captures_iter(entry)
                .map(|c| c[1].to_string())
                .collect();

            let published = published_re
                .captures(entry)
                .and_then(|c| Self::parse_datetime(&c[1]));

            let arxiv_id = Self::parse_arxiv_id(&id);

            results.push(ExternalSearchResult {
                title,
                summary,
                url: id.clone(),
                source: "arXiv".to_string(),
                authors,
                published,
                arxiv_id,
            });
        }

        Ok(results)
    }
}
