use serde::Serialize;

const RELEASE_PAGE_URL: &str =
    "https://github.com/lfnovo/open-notebook/releases/latest";

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct InstallContext {
    pub channel: String,
    pub current_version: String,
    pub can_self_update: bool,
    pub release_page_url: String,
    pub is_development: bool,
}

pub fn get_install_context() -> InstallContext {
    let current_version = env!("CARGO_PKG_VERSION").to_string();
    let is_development = cfg!(debug_assertions);

    if is_development {
        return InstallContext {
            channel: "development".to_string(),
            current_version,
            can_self_update: false,
            release_page_url: RELEASE_PAGE_URL.to_string(),
            is_development: true,
        };
    }

    if std::env::var("APPIMAGE").is_ok() {
        return InstallContext {
            channel: "appimage".to_string(),
            current_version,
            can_self_update: true,
            release_page_url: RELEASE_PAGE_URL.to_string(),
            is_development: false,
        };
    }

    if let Ok(exe) = std::env::current_exe() {
        let path = exe.to_string_lossy();
        if path.starts_with("/usr/") || path.starts_with("/opt/") {
            return InstallContext {
                channel: "deb".to_string(),
                current_version,
                can_self_update: false,
                release_page_url: RELEASE_PAGE_URL.to_string(),
                is_development: false,
            };
        }
    }

    InstallContext {
        channel: "unknown".to_string(),
        current_version,
        can_self_update: true,
        release_page_url: RELEASE_PAGE_URL.to_string(),
        is_development: false,
    }
}
