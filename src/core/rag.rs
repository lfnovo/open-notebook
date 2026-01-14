//! RAG (Retrieval Augmented Generation) Engine

use anyhow::{Context, Result};
use std::sync::Arc;

use super::document::{Document, DocumentChunk, SourceType};
use super::embedding::EmbeddingService;
use super::vector_store::{SearchResult, VectorStore};
use crate::search::{ArxivSearcher, GoogleSearcher, PdfProcessor, SearchProvider};
use crate::storage::QuestDbClient;

/// RAG engine configuration
#[derive(Debug, Clone)]
pub struct RagConfig {
    pub chunk_size: usize,
    pub chunk_overlap: usize,
    pub search_limit: usize,
    pub similarity_threshold: f32,
}

impl Default for RagConfig {
    fn default() -> Self {
        Self {
            chunk_size: 512,
            chunk_overlap: 50,
            search_limit: 10,
            similarity_threshold: 0.7,
        }
    }
}

/// Main RAG engine
pub struct RagEngine {
    embedding_service: EmbeddingService,
    vector_store: Arc<VectorStore>,
    config: RagConfig,
    arxiv_searcher: Option<ArxivSearcher>,
    google_searcher: Option<GoogleSearcher>,
    pdf_processor: PdfProcessor,
    questdb_client: Option<Arc<QuestDbClient>>,
}

/// Query result from RAG engine
#[derive(Debug, Clone)]
pub struct QueryResult {
    pub query: String,
    pub context_chunks: Vec<ContextChunk>,
    pub sources: Vec<SourceReference>,
}

/// A chunk of context retrieved for RAG
#[derive(Debug, Clone)]
pub struct ContextChunk {
    pub content: String,
    pub score: f32,
    pub source_type: SourceType,
    pub source_title: String,
}

/// Reference to a source document
#[derive(Debug, Clone)]
pub struct SourceReference {
    pub title: String,
    pub url: Option<String>,
    pub source_type: SourceType,
}

impl RagEngine {
    /// Create a new RAG engine
    pub async fn new(
        embedding_service: EmbeddingService,
        vector_store: Arc<VectorStore>,
        config: RagConfig,
    ) -> Result<Self> {
        Ok(Self {
            embedding_service,
            vector_store,
            config,
            arxiv_searcher: Some(ArxivSearcher::new(50)),
            google_searcher: None,
            pdf_processor: PdfProcessor::new(),
            questdb_client: None,
        })
    }

    /// Configure Google search (requires SerpAPI key)
    pub fn with_google_search(mut self, api_key: String) -> Self {
        self.google_searcher = Some(GoogleSearcher::new(api_key));
        self
    }

    /// Configure QuestDB client
    pub fn with_questdb(mut self, client: Arc<QuestDbClient>) -> Self {
        self.questdb_client = Some(client);
        self
    }

    /// Ingest a document into the knowledge base
    pub async fn ingest_document(&self, mut document: Document) -> Result<()> {
        // Chunk the document
        document.chunk(self.config.chunk_size, self.config.chunk_overlap);

        // Generate embeddings for chunks
        let texts: Vec<String> = document.chunks.iter().map(|c| c.content.clone()).collect();
        let embeddings = self.embedding_service.embed_batch(texts).await?;

        // Prepare batch for vector store
        let points: Vec<_> = document
            .chunks
            .iter()
            .zip(embeddings)
            .map(|(chunk, embedding)| {
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.content.clone(),
                    embedding,
                )
            })
            .collect();

        // Store in vector database
        self.vector_store.upsert_batch(points).await?;

        tracing::info!(
            document_id = %document.id,
            title = %document.title,
            chunks = document.chunks.len(),
            "Document ingested"
        );

        Ok(())
    }

    /// Ingest a PDF file
    pub async fn ingest_pdf(&self, path: &std::path::Path) -> Result<Document> {
        let document = self.pdf_processor.process(path).await?;
        self.ingest_document(document.clone()).await?;
        Ok(document)
    }

    /// Search arXiv and ingest results
    pub async fn search_and_ingest_arxiv(&self, query: &str, max_results: usize) -> Result<Vec<Document>> {
        let searcher = self.arxiv_searcher.as_ref().context("arXiv searcher not configured")?;
        let results = searcher.search(query, max_results).await?;

        let mut documents = Vec::new();
        for result in results {
            let document = Document::new(&result.title, &result.summary, SourceType::ArxivPaper)
                .with_source_url(&result.url)
                .with_metadata(super::document::DocumentMetadata {
                    authors: result.authors,
                    arxiv_id: Some(result.arxiv_id),
                    publication_date: result.published,
                    abstract_text: Some(result.summary.clone()),
                    ..Default::default()
                });

            self.ingest_document(document.clone()).await?;
            documents.push(document);
        }

        Ok(documents)
    }

    /// Query the knowledge base
    pub async fn query(&self, query: &str) -> Result<QueryResult> {
        // Generate query embedding
        let query_embedding = self.embedding_service.embed(query).await?;

        // Search vector store
        let results = self.vector_store.search(query_embedding, self.config.search_limit).await?;

        // Filter by similarity threshold
        let filtered: Vec<_> = results
            .into_iter()
            .filter(|r| r.score >= self.config.similarity_threshold)
            .collect();

        // Build context chunks (would need document metadata lookup in production)
        let context_chunks: Vec<ContextChunk> = filtered
            .iter()
            .map(|r| ContextChunk {
                content: r.content.clone(),
                score: r.score,
                source_type: SourceType::Manual, // Would lookup from document
                source_title: format!("Document {}", r.document_id),
            })
            .collect();

        // Build source references
        let sources: Vec<SourceReference> = filtered
            .iter()
            .map(|r| SourceReference {
                title: format!("Document {}", r.document_id),
                url: None,
                source_type: SourceType::Manual,
            })
            .collect();

        Ok(QueryResult {
            query: query.to_string(),
            context_chunks,
            sources,
        })
    }

    /// Build context string for LLM
    pub fn build_context(&self, result: &QueryResult) -> String {
        let mut context = String::new();
        for (i, chunk) in result.context_chunks.iter().enumerate() {
            context.push_str(&format!(
                "[Source {}] (score: {:.2})\n{}\n\n",
                i + 1,
                chunk.score,
                chunk.content
            ));
        }
        context
    }

    /// Query trading data from QuestDB
    pub async fn query_trading_data(&self, query: &str) -> Result<Vec<serde_json::Value>> {
        let client = self.questdb_client.as_ref().context("QuestDB not configured")?;
        client.query(query).await
    }
}
