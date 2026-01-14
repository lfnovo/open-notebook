//! Document types and processing

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Source type for documents
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SourceType {
    Pdf,
    ArxivPaper,
    WebPage,
    QuestDb,
    ThetaData,
    Manual,
}

/// A document in the knowledge base
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: Uuid,
    pub title: String,
    pub content: String,
    pub source_type: SourceType,
    pub source_url: Option<String>,
    pub metadata: DocumentMetadata,
    pub chunks: Vec<DocumentChunk>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Metadata for a document
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DocumentMetadata {
    pub authors: Vec<String>,
    pub tags: Vec<String>,
    pub abstract_text: Option<String>,
    pub doi: Option<String>,
    pub arxiv_id: Option<String>,
    pub publication_date: Option<DateTime<Utc>>,
    pub page_count: Option<usize>,
    pub word_count: Option<usize>,
    pub extra: serde_json::Value,
}

/// A chunk of a document for embedding
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentChunk {
    pub id: Uuid,
    pub document_id: Uuid,
    pub content: String,
    pub chunk_index: usize,
    pub start_char: usize,
    pub end_char: usize,
    pub embedding: Option<Vec<f32>>,
}

impl Document {
    /// Create a new document
    pub fn new(title: impl Into<String>, content: impl Into<String>, source_type: SourceType) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::now_v7(),
            title: title.into(),
            content: content.into(),
            source_type,
            source_url: None,
            metadata: DocumentMetadata::default(),
            chunks: Vec::new(),
            created_at: now,
            updated_at: now,
        }
    }

    /// Set the source URL
    pub fn with_source_url(mut self, url: impl Into<String>) -> Self {
        self.source_url = Some(url.into());
        self
    }

    /// Set metadata
    pub fn with_metadata(mut self, metadata: DocumentMetadata) -> Self {
        self.metadata = metadata;
        self
    }

    /// Chunk the document content
    pub fn chunk(&mut self, chunk_size: usize, overlap: usize) {
        self.chunks = chunk_text(&self.content, chunk_size, overlap)
            .into_iter()
            .enumerate()
            .map(|(idx, (content, start, end))| DocumentChunk {
                id: Uuid::now_v7(),
                document_id: self.id,
                content,
                chunk_index: idx,
                start_char: start,
                end_char: end,
                embedding: None,
            })
            .collect();
        self.updated_at = Utc::now();
    }
}

/// Chunk text with overlap
fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<(String, usize, usize)> {
    let mut chunks = Vec::new();
    let chars: Vec<char> = text.chars().collect();
    let total = chars.len();

    if total == 0 {
        return chunks;
    }

    let step = chunk_size.saturating_sub(overlap).max(1);
    let mut start = 0;

    while start < total {
        let end = (start + chunk_size).min(total);
        let chunk: String = chars[start..end].iter().collect();

        // Try to break at sentence boundary
        let adjusted_chunk = if end < total {
            if let Some(pos) = chunk.rfind(|c| c == '.' || c == '!' || c == '?') {
                let adjusted_end = start + pos + 1;
                if adjusted_end > start {
                    chars[start..adjusted_end].iter().collect()
                } else {
                    chunk
                }
            } else {
                chunk
            }
        } else {
            chunk
        };

        let actual_end = start + adjusted_chunk.chars().count();
        chunks.push((adjusted_chunk, start, actual_end));

        start += step;
    }

    chunks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_document_creation() {
        let doc = Document::new("Test", "Content here", SourceType::Manual);
        assert_eq!(doc.title, "Test");
        assert_eq!(doc.source_type, SourceType::Manual);
    }

    #[test]
    fn test_chunking() {
        let mut doc = Document::new("Test", "Hello world. This is a test. Another sentence here.", SourceType::Manual);
        doc.chunk(20, 5);
        assert!(!doc.chunks.is_empty());
    }
}
