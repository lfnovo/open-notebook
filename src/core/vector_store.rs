//! Vector store implementation using Qdrant

use anyhow::{Context, Result};
use qdrant_client::qdrant::{
    CreateCollectionBuilder, Distance, PointStruct, SearchPointsBuilder,
    UpsertPointsBuilder, VectorParamsBuilder, vectors_config::Config,
    VectorsConfig, Value as QdrantValue, PointId,
};
use qdrant_client::Qdrant;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Vector store for semantic search
pub struct VectorStore {
    client: Qdrant,
    collection_name: String,
    dimension: usize,
}

/// Search result from vector store
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: Uuid,
    pub score: f32,
    pub document_id: Uuid,
    pub chunk_index: usize,
    pub content: String,
}

impl VectorStore {
    /// Connect to Qdrant
    pub async fn new(url: &str, collection_name: &str, dimension: usize) -> Result<Self> {
        let client = Qdrant::from_url(url)
            .build()
            .context("Failed to connect to Qdrant")?;

        let store = Self {
            client,
            collection_name: collection_name.to_string(),
            dimension,
        };

        // Ensure collection exists
        store.ensure_collection().await?;

        Ok(store)
    }

    /// Ensure the collection exists
    async fn ensure_collection(&self) -> Result<()> {
        let exists = self
            .client
            .collection_exists(&self.collection_name)
            .await
            .context("Failed to check collection existence")?;

        if !exists {
            let vectors_config = VectorsConfig {
                config: Some(Config::Params(
                    VectorParamsBuilder::new(self.dimension as u64, Distance::Cosine).build(),
                )),
            };

            self.client
                .create_collection(
                    CreateCollectionBuilder::new(&self.collection_name)
                        .vectors_config(vectors_config),
                )
                .await
                .context("Failed to create collection")?;

            tracing::info!(collection = %self.collection_name, "Created Qdrant collection");
        }

        Ok(())
    }

    /// Insert vectors
    pub async fn upsert(
        &self,
        id: Uuid,
        document_id: Uuid,
        chunk_index: usize,
        content: &str,
        embedding: Vec<f32>,
    ) -> Result<()> {
        let mut payload: HashMap<String, QdrantValue> = HashMap::new();
        payload.insert("document_id".to_string(), document_id.to_string().into());
        payload.insert("chunk_index".to_string(), (chunk_index as i64).into());
        payload.insert("content".to_string(), content.into());

        let point = PointStruct::new(
            PointId::from(id.to_string()),
            embedding,
            payload,
        );

        self.client
            .upsert_points(UpsertPointsBuilder::new(&self.collection_name, vec![point]))
            .await
            .context("Failed to upsert point")?;

        Ok(())
    }

    /// Batch insert vectors
    pub async fn upsert_batch(&self, points: Vec<(Uuid, Uuid, usize, String, Vec<f32>)>) -> Result<()> {
        let qdrant_points: Vec<PointStruct> = points
            .into_iter()
            .map(|(id, doc_id, chunk_idx, content, embedding)| {
                let mut payload: HashMap<String, QdrantValue> = HashMap::new();
                payload.insert("document_id".to_string(), doc_id.to_string().into());
                payload.insert("chunk_index".to_string(), (chunk_idx as i64).into());
                payload.insert("content".to_string(), content.into());

                PointStruct::new(PointId::from(id.to_string()), embedding, payload)
            })
            .collect();

        self.client
            .upsert_points(UpsertPointsBuilder::new(&self.collection_name, qdrant_points))
            .await
            .context("Failed to batch upsert points")?;

        Ok(())
    }

    /// Search for similar vectors
    pub async fn search(&self, query_embedding: Vec<f32>, limit: usize) -> Result<Vec<SearchResult>> {
        let results = self
            .client
            .search_points(
                SearchPointsBuilder::new(&self.collection_name, query_embedding, limit as u64)
                    .with_payload(true),
            )
            .await
            .context("Failed to search vectors")?;

        let search_results: Vec<SearchResult> = results
            .result
            .into_iter()
            .filter_map(|point| {
                let id = match &point.id {
                    Some(PointId { point_id_options: Some(qdrant_client::qdrant::point_id::PointIdOptions::Uuid(s)) }) => {
                        Uuid::parse_str(s).ok()?
                    }
                    _ => return None,
                };

                let payload = point.payload;
                let document_id = payload
                    .get("document_id")
                    .and_then(|v| v.as_str())
                    .and_then(|s| Uuid::parse_str(s).ok())?;
                let chunk_index = payload
                    .get("chunk_index")
                    .and_then(|v| v.as_integer())
                    .unwrap_or(0) as usize;
                let content = payload
                    .get("content")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();

                Some(SearchResult {
                    id,
                    score: point.score,
                    document_id,
                    chunk_index,
                    content,
                })
            })
            .collect();

        Ok(search_results)
    }

    /// Delete vectors by document ID
    pub async fn delete_by_document(&self, document_id: Uuid) -> Result<()> {
        use qdrant_client::qdrant::{DeletePointsBuilder, Filter, FieldCondition, Match, Condition};

        let filter = Filter::must([Condition::field(
            FieldCondition::new_match("document_id", Match::value(document_id.to_string())),
        )]);

        self.client
            .delete_points(
                DeletePointsBuilder::new(&self.collection_name)
                    .points(filter),
            )
            .await
            .context("Failed to delete points")?;

        Ok(())
    }
}
