//! QuestDB client for trading data

use anyhow::{Context, Result};
use serde_json::Value;
use std::time::Duration;

/// QuestDB client for time-series trading data
pub struct QuestDbClient {
    http_client: reqwest::Client,
    base_url: String,
}

/// GEX (Gamma Exposure) data
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GexData {
    pub timestamp: i64,
    pub symbol: String,
    pub strike: f64,
    pub gex: f64,
    pub call_gex: f64,
    pub put_gex: f64,
    pub net_gex: f64,
}

/// Vanna data
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VannaData {
    pub timestamp: i64,
    pub symbol: String,
    pub strike: f64,
    pub vanna: f64,
    pub delta: f64,
    pub iv: f64,
}

impl QuestDbClient {
    /// Create a new QuestDB client
    pub fn new(host: &str, port: u16) -> Result<Self> {
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self {
            http_client,
            base_url: format!("http://{}:{}", host, port),
        })
    }

    /// Execute a SQL query
    pub async fn query(&self, sql: &str) -> Result<Vec<Value>> {
        let url = format!("{}/exec", self.base_url);

        let response = self
            .http_client
            .get(&url)
            .query(&[("query", sql)])
            .send()
            .await
            .context("Failed to execute QuestDB query")?;

        let result: Value = response.json().await.context("Failed to parse QuestDB response")?;

        // Extract dataset from response
        if let Some(dataset) = result.get("dataset").and_then(|d| d.as_array()) {
            Ok(dataset.clone())
        } else {
            Ok(vec![])
        }
    }

    /// Get GEX data for a symbol
    pub async fn get_gex(&self, symbol: &str, days: i32) -> Result<Vec<GexData>> {
        let sql = format!(
            "SELECT timestamp, symbol, strike, gex, call_gex, put_gex, net_gex \
             FROM gex_data \
             WHERE symbol = '{}' \
             AND timestamp > dateadd('d', -{}, now()) \
             ORDER BY timestamp DESC",
            symbol, days
        );

        let rows = self.query(&sql).await?;

        let gex_data: Vec<GexData> = rows
            .into_iter()
            .filter_map(|row| {
                let arr = row.as_array()?;
                Some(GexData {
                    timestamp: arr.first()?.as_i64()?,
                    symbol: arr.get(1)?.as_str()?.to_string(),
                    strike: arr.get(2)?.as_f64()?,
                    gex: arr.get(3)?.as_f64()?,
                    call_gex: arr.get(4)?.as_f64()?,
                    put_gex: arr.get(5)?.as_f64()?,
                    net_gex: arr.get(6)?.as_f64()?,
                })
            })
            .collect();

        Ok(gex_data)
    }

    /// Get Vanna data for a symbol
    pub async fn get_vanna(&self, symbol: &str, days: i32) -> Result<Vec<VannaData>> {
        let sql = format!(
            "SELECT timestamp, symbol, strike, vanna, delta, iv \
             FROM vanna_data \
             WHERE symbol = '{}' \
             AND timestamp > dateadd('d', -{}, now()) \
             ORDER BY timestamp DESC",
            symbol, days
        );

        let rows = self.query(&sql).await?;

        let vanna_data: Vec<VannaData> = rows
            .into_iter()
            .filter_map(|row| {
                let arr = row.as_array()?;
                Some(VannaData {
                    timestamp: arr.first()?.as_i64()?,
                    symbol: arr.get(1)?.as_str()?.to_string(),
                    strike: arr.get(2)?.as_f64()?,
                    vanna: arr.get(3)?.as_f64()?,
                    delta: arr.get(4)?.as_f64()?,
                    iv: arr.get(5)?.as_f64()?,
                })
            })
            .collect();

        Ok(vanna_data)
    }

    /// Get latest price for a symbol
    pub async fn get_latest_price(&self, symbol: &str) -> Result<Option<f64>> {
        let sql = format!(
            "SELECT close FROM trades WHERE symbol = '{}' ORDER BY timestamp DESC LIMIT 1",
            symbol
        );

        let rows = self.query(&sql).await?;

        Ok(rows.first().and_then(|r| r.as_array()?.first()?.as_f64()))
    }

    /// Insert GEX data
    pub async fn insert_gex(&self, data: &GexData) -> Result<()> {
        let sql = format!(
            "INSERT INTO gex_data (timestamp, symbol, strike, gex, call_gex, put_gex, net_gex) \
             VALUES ({}, '{}', {}, {}, {}, {}, {})",
            data.timestamp, data.symbol, data.strike, data.gex, data.call_gex, data.put_gex, data.net_gex
        );

        self.query(&sql).await?;
        Ok(())
    }
}
