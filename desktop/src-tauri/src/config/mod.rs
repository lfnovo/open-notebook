use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use thiserror::Error;
use uuid::Uuid;

const APP_DIR_NAME: &str = "open-notebook-desktop";
const EMBEDDED_COMPOSE: &str = include_str!("../../../resources/docker-compose.yml");

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("failed to read config: {0}")]
    Io(#[from] std::io::Error),
    #[error("failed to parse config: {0}")]
    Parse(#[from] serde_json::Error),
    #[error("config file is corrupted: {message}. backup saved to {backup_path}")]
    Corrupted {
        message: String,
        backup_path: String,
    },
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

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PublicAppConfig {
    pub data_dir: String,
    pub encryption_key_configured: bool,
    pub stop_on_exit: bool,
    pub onboarding_complete: bool,
    pub ui_port: u16,
    pub api_port: u16,
    pub language: String,
    pub auto_start_on_launch: bool,
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

impl From<&AppConfig> for PublicAppConfig {
    fn from(config: &AppConfig) -> Self {
        Self {
            data_dir: config.data_dir.clone(),
            encryption_key_configured: !config.encryption_key.is_empty(),
            stop_on_exit: config.stop_on_exit,
            onboarding_complete: config.onboarding_complete,
            ui_port: config.ui_port,
            api_port: config.api_port,
            language: config.language.clone(),
            auto_start_on_launch: config.auto_start_on_launch,
            open_notebook_directly: config.open_notebook_directly,
        }
    }
}

impl AppConfig {
    pub fn merge_public(&self, public: &PublicAppConfig, encryption_key: Option<&str>) -> Self {
        let mut next = self.clone();
        next.data_dir = public.data_dir.clone();
        next.stop_on_exit = public.stop_on_exit;
        next.onboarding_complete = public.onboarding_complete;
        next.ui_port = public.ui_port;
        next.api_port = public.api_port;
        next.language = public.language.clone();
        next.auto_start_on_launch = public.auto_start_on_launch;
        next.open_notebook_directly = public.open_notebook_directly;

        if let Some(key) = encryption_key.map(str::trim).filter(|key| !key.is_empty()) {
            next.encryption_key = key.to_string();
        }

        next
    }
}

pub fn validate_public_config(config: &PublicAppConfig) -> Result<(), String> {
    let data_dir = config.data_dir.trim();
    if data_dir.is_empty() {
        return Err("Das Datenverzeichnis darf nicht leer sein.".to_string());
    }

    let path = PathBuf::from(data_dir);
    if !path.is_absolute() {
        return Err("Das Datenverzeichnis muss ein absoluter Pfad sein.".to_string());
    }

    if config.ui_port == 0 || config.api_port == 0 {
        return Err("Ports müssen größer als 0 sein.".to_string());
    }

    Ok(())
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
    if let Some(data_local) = dirs::data_local_dir() {
        data_local.join(APP_DIR_NAME)
    } else if let Some(home) = dirs::home_dir() {
        home.join(".local").join("share").join(APP_DIR_NAME)
    } else {
        PathBuf::from(".open-notebook-desktop")
    }
}

pub fn config_file_path() -> PathBuf {
    default_data_dir().join("config.json")
}

fn backup_config_file(path: &Path) -> Result<PathBuf, ConfigError> {
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    let backup = path.with_extension(format!("json.bak.{timestamp}"));
    fs::copy(path, &backup)?;
    Ok(backup)
}

pub fn load_config() -> Result<AppConfig, ConfigError> {
    let path = config_file_path();
    if !path.exists() {
        return Ok(AppConfig::default());
    }

    let content = fs::read_to_string(&path)?;
    match serde_json::from_str::<AppConfig>(&content) {
        Ok(mut config) => {
            if config.language.is_empty() {
                config.language = detect_system_locale();
            }
            Ok(config)
        }
        Err(parse_error) => {
            let backup = backup_config_file(&path)?;
            Err(ConfigError::Corrupted {
                message: parse_error.to_string(),
                backup_path: backup.display().to_string(),
            })
        }
    }
}

fn write_secret_file(path: &Path, content: &str) -> Result<(), ConfigError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    #[cfg(unix)]
    {
        use std::fs::OpenOptions;
        use std::os::unix::fs::OpenOptionsExt;

        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(0o600)
            .open(path)?;
        file.write_all(content.as_bytes())?;
        return Ok(());
    }

    #[cfg(not(unix))]
    fs::write(path, content)
}

pub fn save_config(config: &AppConfig) -> Result<(), ConfigError> {
    let data_dir = PathBuf::from(&config.data_dir);
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(data_dir.join("surreal_data"))?;
    fs::create_dir_all(data_dir.join("notebook_data"))?;

    let config_path = config_file_path();
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent)?;
    }

    let content = serde_json::to_string_pretty(config)?;
    write_secret_file(&config_path, &content)?;
    write_env_file(config)?;
    Ok(())
}

pub fn generate_encryption_key() -> String {
    Uuid::new_v4().to_string()
}

fn read_or_create_surreal_password(env_path: &Path) -> Result<String, ConfigError> {
    if env_path.exists() {
        let content = fs::read_to_string(env_path)?;
        for line in content.lines() {
            if let Some(value) = line.strip_prefix("SURREAL_PASSWORD=") {
                if !value.trim().is_empty() {
                    return Ok(value.trim().to_string());
                }
            }
        }
    }

    Ok(Uuid::new_v4().to_string())
}

pub fn write_env_file(config: &AppConfig) -> Result<(), ConfigError> {
    let env_path = PathBuf::from(&config.data_dir).join(".env");
    let surreal_password = read_or_create_surreal_password(&env_path)?;
    let content = format!(
        "OPEN_NOTEBOOK_ENCRYPTION_KEY={}\nSURREAL_USER=root\nSURREAL_PASSWORD={}\n",
        config.encryption_key, surreal_password
    );
    write_secret_file(&env_path, &content)?;
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
                fs::write(&compose_path, EMBEDDED_COMPOSE)?;
            }
        } else {
            fs::write(&compose_path, EMBEDDED_COMPOSE)?;
        }
    }

    Ok(compose_path)
}
