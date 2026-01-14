//! Configuration management for Prior Notebook
//!
//! Supports loading from:
//! - Environment variables
//! - TOML config files
//! - CLI arguments

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Main application settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Settings {
    pub server: ServerConfig,
    pub database: DatabaseConfig,
    pub security: SecurityConfig,
    pub search: SearchConfig,
    pub llm: LlmConfig,
    pub julia: JuliaConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub workers: usize,
    pub max_connections: usize,
    pub request_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub questdb_host: String,
    pub questdb_port: u16,
    pub redis_url: String,
    pub qdrant_url: String,
    pub qdrant_collection: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub jwt_secret: String,
    pub jwt_expiry_hours: u64,
    pub allowed_wireguard_ips: Vec<String>,
    pub enable_zero_trust: bool,
    pub vault_addr: Option<String>,
    pub vault_token: Option<String>,
    pub tls_cert_path: Option<PathBuf>,
    pub tls_key_path: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchConfig {
    pub serpapi_key: Option<String>,
    pub arxiv_max_results: usize,
    pub pdf_storage_path: PathBuf,
    pub embedding_model: String,
    pub embedding_dimension: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmConfig {
    pub default_provider: LlmProvider,
    pub openai_api_key: Option<String>,
    pub anthropic_api_key: Option<String>,
    pub ollama_url: Option<String>,
    pub default_model: String,
    pub max_tokens: usize,
    pub temperature: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum LlmProvider {
    OpenAI,
    Anthropic,
    Ollama,
    Local,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JuliaConfig {
    pub enabled: bool,
    pub julia_path: Option<PathBuf>,
    pub project_path: PathBuf,
    pub num_threads: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            server: ServerConfig {
                host: "127.0.0.1".to_string(),
                port: 8080,
                workers: num_cpus::get(),
                max_connections: 10000,
                request_timeout_secs: 30,
            },
            database: DatabaseConfig {
                questdb_host: "localhost".to_string(),
                questdb_port: 9009,
                redis_url: "redis://localhost:6379".to_string(),
                qdrant_url: "http://localhost:6334".to_string(),
                qdrant_collection: "prior_notebook".to_string(),
            },
            security: SecurityConfig {
                jwt_secret: "CHANGE_ME_IN_PRODUCTION".to_string(),
                jwt_expiry_hours: 24,
                allowed_wireguard_ips: vec!["10.0.0.0/24".to_string()],
                enable_zero_trust: true,
                vault_addr: None,
                vault_token: None,
                tls_cert_path: None,
                tls_key_path: None,
            },
            search: SearchConfig {
                serpapi_key: None,
                arxiv_max_results: 50,
                pdf_storage_path: PathBuf::from("./data/pdfs"),
                embedding_model: "BAAI/bge-small-en-v1.5".to_string(),
                embedding_dimension: 384,
            },
            llm: LlmConfig {
                default_provider: LlmProvider::Anthropic,
                openai_api_key: None,
                anthropic_api_key: None,
                ollama_url: Some("http://localhost:11434".to_string()),
                default_model: "claude-sonnet-4-20250514".to_string(),
                max_tokens: 4096,
                temperature: 0.7,
            },
            julia: JuliaConfig {
                enabled: false,
                julia_path: None,
                project_path: PathBuf::from("./julia_lib"),
                num_threads: 4,
            },
        }
    }
}

impl Settings {
    /// Load settings from environment and config file
    pub fn load() -> anyhow::Result<Self> {
        dotenvy::dotenv().ok();

        let config_path = std::env::var("PRIOR_CONFIG")
            .unwrap_or_else(|_| "config.toml".to_string());

        let mut settings = if std::path::Path::new(&config_path).exists() {
            let content = std::fs::read_to_string(&config_path)?;
            toml::from_str(&content)?
        } else {
            Self::default()
        };

        // Override with environment variables
        settings.apply_env_overrides();

        Ok(settings)
    }

    fn apply_env_overrides(&mut self) {
        if let Ok(port) = std::env::var("PRIOR_PORT") {
            if let Ok(p) = port.parse() {
                self.server.port = p;
            }
        }
        if let Ok(host) = std::env::var("PRIOR_HOST") {
            self.server.host = host;
        }
        if let Ok(key) = std::env::var("OPENAI_API_KEY") {
            self.llm.openai_api_key = Some(key);
        }
        if let Ok(key) = std::env::var("ANTHROPIC_API_KEY") {
            self.llm.anthropic_api_key = Some(key);
        }
        if let Ok(key) = std::env::var("SERPAPI_KEY") {
            self.search.serpapi_key = Some(key);
        }
        if let Ok(secret) = std::env::var("JWT_SECRET") {
            self.security.jwt_secret = secret;
        }
        if let Ok(url) = std::env::var("REDIS_URL") {
            self.database.redis_url = url;
        }
        if let Ok(url) = std::env::var("QDRANT_URL") {
            self.database.qdrant_url = url;
        }
    }
}

/// Number of CPUs helper
mod num_cpus {
    pub fn get() -> usize {
        std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(4)
    }
}
