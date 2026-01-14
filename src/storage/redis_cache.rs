//! Redis caching layer

use anyhow::{Context, Result};
use redis::{aio::ConnectionManager, AsyncCommands};
use serde::{de::DeserializeOwned, Serialize};
use std::time::Duration;

/// Redis cache client
pub struct RedisCache {
    conn: ConnectionManager,
    default_ttl: Duration,
}

impl RedisCache {
    /// Connect to Redis
    pub async fn new(url: &str, default_ttl: Duration) -> Result<Self> {
        let client = redis::Client::open(url).context("Failed to create Redis client")?;
        let conn = ConnectionManager::new(client)
            .await
            .context("Failed to connect to Redis")?;

        Ok(Self { conn, default_ttl })
    }

    /// Get a cached value
    pub async fn get<T: DeserializeOwned>(&self, key: &str) -> Result<Option<T>> {
        let mut conn = self.conn.clone();
        let value: Option<String> = conn.get(key).await.context("Redis GET failed")?;

        match value {
            Some(json) => {
                let parsed = serde_json::from_str(&json).context("Failed to deserialize cached value")?;
                Ok(Some(parsed))
            }
            None => Ok(None),
        }
    }

    /// Set a cached value
    pub async fn set<T: Serialize>(&self, key: &str, value: &T) -> Result<()> {
        self.set_with_ttl(key, value, self.default_ttl).await
    }

    /// Set a cached value with custom TTL
    pub async fn set_with_ttl<T: Serialize>(&self, key: &str, value: &T, ttl: Duration) -> Result<()> {
        let mut conn = self.conn.clone();
        let json = serde_json::to_string(value).context("Failed to serialize value")?;
        conn.set_ex(key, json, ttl.as_secs())
            .await
            .context("Redis SET failed")?;
        Ok(())
    }

    /// Delete a cached value
    pub async fn delete(&self, key: &str) -> Result<bool> {
        let mut conn = self.conn.clone();
        let deleted: i32 = conn.del(key).await.context("Redis DEL failed")?;
        Ok(deleted > 0)
    }

    /// Check if key exists
    pub async fn exists(&self, key: &str) -> Result<bool> {
        let mut conn = self.conn.clone();
        let exists: bool = conn.exists(key).await.context("Redis EXISTS failed")?;
        Ok(exists)
    }

    /// Get or set (cache-aside pattern)
    pub async fn get_or_set<T, F, Fut>(&self, key: &str, f: F) -> Result<T>
    where
        T: Serialize + DeserializeOwned,
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        if let Some(cached) = self.get(key).await? {
            return Ok(cached);
        }

        let value = f().await?;
        self.set(key, &value).await?;
        Ok(value)
    }

    /// Increment a counter
    pub async fn incr(&self, key: &str) -> Result<i64> {
        let mut conn = self.conn.clone();
        let value: i64 = conn.incr(key, 1).await.context("Redis INCR failed")?;
        Ok(value)
    }

    /// Set hash field
    pub async fn hset<T: Serialize>(&self, key: &str, field: &str, value: &T) -> Result<()> {
        let mut conn = self.conn.clone();
        let json = serde_json::to_string(value)?;
        conn.hset(key, field, json).await.context("Redis HSET failed")?;
        Ok(())
    }

    /// Get hash field
    pub async fn hget<T: DeserializeOwned>(&self, key: &str, field: &str) -> Result<Option<T>> {
        let mut conn = self.conn.clone();
        let value: Option<String> = conn.hget(key, field).await.context("Redis HGET failed")?;

        match value {
            Some(json) => {
                let parsed = serde_json::from_str(&json)?;
                Ok(Some(parsed))
            }
            None => Ok(None),
        }
    }

    /// Push to list (LPUSH)
    pub async fn lpush<T: Serialize>(&self, key: &str, value: &T) -> Result<()> {
        let mut conn = self.conn.clone();
        let json = serde_json::to_string(value)?;
        conn.lpush(key, json).await.context("Redis LPUSH failed")?;
        Ok(())
    }

    /// Get list range
    pub async fn lrange<T: DeserializeOwned>(&self, key: &str, start: isize, stop: isize) -> Result<Vec<T>> {
        let mut conn = self.conn.clone();
        let values: Vec<String> = conn.lrange(key, start, stop).await.context("Redis LRANGE failed")?;

        values
            .into_iter()
            .map(|json| serde_json::from_str(&json).context("Failed to deserialize list item"))
            .collect()
    }
}

impl Clone for RedisCache {
    fn clone(&self) -> Self {
        Self {
            conn: self.conn.clone(),
            default_ttl: self.default_ttl,
        }
    }
}
