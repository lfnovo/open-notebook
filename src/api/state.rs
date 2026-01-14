//! Application state shared across handlers

use std::sync::Arc;

use crate::core::rag::RagEngine;
use crate::security::auth::AuthService;
use crate::storage::{QuestDbClient, RedisCache};

/// Shared application state
#[derive(Clone)]
pub struct AppState {
    pub rag_engine: Arc<RagEngine>,
    pub auth_service: AuthService,
    pub questdb: Option<Arc<QuestDbClient>>,
    pub cache: Option<RedisCache>,
}

impl AppState {
    pub fn new(rag_engine: RagEngine, auth_service: AuthService) -> Self {
        Self {
            rag_engine: Arc::new(rag_engine),
            auth_service,
            questdb: None,
            cache: None,
        }
    }

    pub fn with_questdb(mut self, client: QuestDbClient) -> Self {
        self.questdb = Some(Arc::new(client));
        self
    }

    pub fn with_cache(mut self, cache: RedisCache) -> Self {
        self.cache = Some(cache);
        self
    }
}
