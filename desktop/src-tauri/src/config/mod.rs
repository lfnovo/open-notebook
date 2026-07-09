use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use thiserror::Error;
use uuid::Uuid;

const APP_DIR_NAME: &str = "open-notebook-desktop";

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("failed to read config: {0}")]
    Io(#[from] std::io::Error),
    #[error("failed to parse config: {0}")]
    Parse(#[from] serde_json::Error),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppConfig {
    pub data_dir: String,
    pub encryption_key: String,
    pub stop_on_exit: bool,
    pub onboarding_complete: bool,
    pub ui_port: u16,
    pub api_port: u16,
    #[serde(default = "default_language")]
    pub language: String,
    #[serde(default = "default_auto_start_on_launch")]
    pub auto_start_on_launch: bool,
    #[serde(default = "default_open_notebook_directly")]
    pub open_notebook_directly: bool,
}

fn default_auto_start_on_launch() -> bool {
    true
}

fn default_open_notebook_directly() -> bool {
    true
}

fn default_language() -> String {
    detect_system_locale()
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            data_dir: default_data_dir().to_string_lossy().to_string(),
            encryption_key: String::new(),
            stop_on_exit: true,
            onboarding_complete: false,
            ui_port: 8502,
            api_port: 5055,
            language: detect_system_locale(),
            auto_start_on_launch: true,
            open_notebook_directly: true,
        }
    }
}

pub fn detect_system_locale() -> String {
    for key in ["LC_ALL", "LC_MESSAGES", "LANG"] {
        if let Ok(value) = std::env::var(key) {
            if let Some(language) = parse_locale_code(&value) {
                return language;
            }
        }
    }
    "en".to_string()
}

fn parse_locale_code(value: &str) -> Option<String> {
    let trimmed = value.split('.').next()?.trim();
    if trimmed.is_empty() || trimmed == "C" || trimmed == "POSIX" {
        return None;
    }

    let code = trimmed.split('_').next()?.to_lowercase();
    match code.as_str() {
        "de" => Some("de".to_string()),
        "en" => Some("en".to_string()),
        _ => None,
    }
}

pub fn default_data_dir() -> PathBuf {
    dirs::data_local_dir()
        .unwrap_or_else(|| PathBuf::from("~/.local/share"))
        .join(APP_DIR_NAME)
}

pub fn config_file_path() -> PathBuf {
    default_data_dir().join("config.json")
}

pub fn load_config() -> Result<AppConfig, ConfigError> {
    let path = config_file_path();
    if !path.exists() {
        return Ok(AppConfig::default());
    }

    let content = fs::read_to_string(path)?;
    let mut config: AppConfig = serde_json::from_str(&content)?;
    if config.language.is_empty() {
        config.language = detect_system_locale();
    }
    Ok(config)
}

pub fn save_config(config: &AppConfig) -> Result<(), ConfigError> {
    let data_dir = PathBuf::from(&config.data_dir);
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(data_dir.join("surreal_data"))?;
    fs::create_dir_all(data_dir.join("notebook_data"))?;

    let content = serde_json::to_string_pretty(config)?;
    fs::write(config_file_path(), content)?;
    write_env_file(config)?;
    Ok(())
}

pub fn generate_encryption_key() -> String {
    Uuid::new_v4().to_string()
}

pub fn write_env_file(config: &AppConfig) -> Result<(), ConfigError> {
    let env_path = PathBuf::from(&config.data_dir).join(".env");
    let content = format!(
        "OPEN_NOTEBOOK_ENCRYPTION_KEY={}\nSURREAL_USER=root\nSURREAL_PASSWORD=root\n",
        config.encryption_key
    );
    fs::write(env_path, content)?;
    Ok(())
}

pub fn ensure_compose_file(
    data_dir: &Path,
    bundled_compose: Option<&Path>,
) -> Result<PathBuf, ConfigError> {
    fs::create_dir_all(data_dir)?;
    let compose_path = data_dir.join("docker-compose.yml");

    if !compose_path.exists() {
        if let Some(source) = bundled_compose {
            if source.exists() {
                fs::copy(source, &compose_path)?;
            } else {
                fs::write(
                    &compose_path,
                    include_str!("../../../../resources/docker-compose.yml"),
                )?;
            }
        } else {
            fs::write(
                &compose_path,
                include_str!("../../../../resources/docker-compose.yml"),
            )?;
        }
    }

    Ok(compose_path)
}
