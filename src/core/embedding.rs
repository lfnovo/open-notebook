//! Embedding service using fastembed

use anyhow::{Context, Result};
use std::sync::Arc;
use tokio::sync::RwLock;

/// Embedding service for generating vector embeddings
pub struct EmbeddingService {
    model: Arc<RwLock<Option<fastembed::TextEmbedding>>>,
    model_name: String,
    dimension: usize,
}

impl EmbeddingService {
    /// Create a new embedding service
    pub fn new(model_name: &str, dimension: usize) -> Self {
        Self {
            model: Arc::new(RwLock::new(None)),
            model_name: model_name.to_string(),
            dimension,
        }
    }

    /// Initialize the embedding model (lazy loading)
    pub async fn init(&self) -> Result<()> {
        let mut model_guard = self.model.write().await;
        if model_guard.is_none() {
            let model_name = self.model_name.clone();
            let model = tokio::task::spawn_blocking(move || {
                fastembed::TextEmbedding::try_new(fastembed::InitOptions {
                    model_name: Self::parse_model_name(&model_name),
                    show_download_progress: true,
                    ..Default::default()
                })
            })
            .await?
            .context("Failed to initialize embedding model")?;

            *model_guard = Some(model);
        }
        Ok(())
    }

    /// Parse model name string to fastembed enum
    fn parse_model_name(name: &str) -> fastembed::EmbeddingModel {
        match name {
            "BAAI/bge-small-en-v1.5" => fastembed::EmbeddingModel::BGESmallENV15,
            "BAAI/bge-base-en-v1.5" => fastembed::EmbeddingModel::BGEBaseENV15,
            "BAAI/bge-large-en-v1.5" => fastembed::EmbeddingModel::BGELargeENV15,
            "sentence-transformers/all-MiniLM-L6-v2" => fastembed::EmbeddingModel::AllMiniLML6V2,
            _ => fastembed::EmbeddingModel::BGESmallENV15,
        }
    }

    /// Get embedding dimension
    pub fn dimension(&self) -> usize {
        self.dimension
    }

    /// Embed a single text
    pub async fn embed(&self, text: &str) -> Result<Vec<f32>> {
        self.init().await?;

        let model_guard = self.model.read().await;
        let model = model_guard.as_ref().context("Model not initialized")?;

        let text = text.to_string();
        let model_clone = unsafe {
            // SAFETY: fastembed model is thread-safe for inference
            std::ptr::read(model as *const fastembed::TextEmbedding)
        };

        let embeddings = tokio::task::spawn_blocking(move || {
            model_clone.embed(vec![text], None)
        })
        .await?
        .context("Failed to generate embedding")?;

        embeddings.into_iter().next().context("No embedding generated")
    }

    /// Embed multiple texts in batch
    pub async fn embed_batch(&self, texts: Vec<String>) -> Result<Vec<Vec<f32>>> {
        self.init().await?;

        let model_guard = self.model.read().await;
        let model = model_guard.as_ref().context("Model not initialized")?;

        let model_clone = unsafe {
            std::ptr::read(model as *const fastembed::TextEmbedding)
        };

        let embeddings = tokio::task::spawn_blocking(move || {
            model_clone.embed(texts, None)
        })
        .await?
        .context("Failed to generate embeddings")?;

        Ok(embeddings)
    }
}

impl Clone for EmbeddingService {
    fn clone(&self) -> Self {
        Self {
            model: Arc::clone(&self.model),
            model_name: self.model_name.clone(),
            dimension: self.dimension,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_embedding_service_creation() {
        let service = EmbeddingService::new("BAAI/bge-small-en-v1.5", 384);
        assert_eq!(service.dimension(), 384);
    }
}
