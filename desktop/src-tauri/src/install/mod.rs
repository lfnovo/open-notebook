use serde::{Deserialize, Serialize};
use std::fs;
use std::process::Command;
use thiserror::Error;

use crate::docker::check_docker_status;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DistroInfo {
    pub id: String,
    pub name: String,
    pub version_id: Option<String>,
    pub family: String,
}

#[derive(Debug, Error)]
pub enum InstallError {
    #[error("{0}")]
    Message(String),
}

pub fn detect_distro() -> DistroInfo {
    let content = fs::read_to_string("/etc/os-release").unwrap_or_default();
    let mut id = "linux".to_string();
    let mut name = "Linux".to_string();
    let mut version_id = None;

    for line in content.lines() {
        if let Some(value) = line.strip_prefix("ID=") {
            id = value.trim_matches('"').to_lowercase();
        } else if let Some(value) = line.strip_prefix("NAME=") {
            name = value.trim_matches('"').to_string();
        } else if let Some(value) = line.strip_prefix("VERSION_ID=") {
            version_id = Some(value.trim_matches('"').to_string());
        }
    }

    let family = match id.as_str() {
        "ubuntu" | "debian" | "linuxmint" | "pop" | "zorin" => "debian",
        "fedora" | "rhel" | "centos" | "rocky" | "almalinux" => "fedora",
        "arch" | "manjaro" | "endeavouros" => "arch",
        "opensuse-tumbleweed" | "opensuse-leap" | "suse" => "suse",
        _ => "unknown",
    }
    .to_string();

    DistroInfo {
        id,
        name,
        version_id,
        family,
    }
}

pub fn get_manual_install_instructions(distro: &DistroInfo) -> String {
    match distro.family.as_str() {
        "debian" => {
            "Manuelle Installation (Debian/Ubuntu):\n\
            1. sudo apt update\n\
            2. sudo apt install -y docker.io docker-compose-plugin\n\
            3. sudo systemctl enable --now docker\n\
            4. sudo usermod -aG docker $USER\n\
            5. Abmelden und neu anmelden"
                .to_string()
        }
        "fedora" => {
            "Manuelle Installation (Fedora):\n\
            1. sudo dnf install -y docker docker-compose\n\
            2. sudo systemctl enable --now docker\n\
            3. sudo usermod -aG docker $USER\n\
            4. Abmelden und neu anmelden"
                .to_string()
        }
        "arch" => {
            "Manuelle Installation (Arch):\n\
            1. sudo pacman -S docker docker-compose\n\
            2. sudo systemctl enable --now docker\n\
            3. sudo usermod -aG docker $USER\n\
            4. Abmelden und neu anmelden"
                .to_string()
        }
        _ => {
            "Allgemeine Anleitung:\n\
            Besuche https://docs.docker.com/engine/install/ und installiere Docker Engine für deine Distribution.\n\
            Danach: sudo usermod -aG docker $USER und neu anmelden."
                .to_string()
        }
    }
}

pub fn install_docker_engine(distro: &DistroInfo) -> Result<String, InstallError> {
    let script = match distro.family.as_str() {
        "debian" => {
            r#"#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-plugin
systemctl enable --now docker
if [ -n "${SUDO_USER:-}" ]; then
  usermod -aG docker "$SUDO_USER"
fi
echo "Docker Engine installiert.""#
        }
        "fedora" => {
            r#"#!/bin/bash
set -euo pipefail
dnf install -y docker docker-compose
systemctl enable --now docker
if [ -n "${SUDO_USER:-}" ]; then
  usermod -aG docker "$SUDO_USER"
fi
echo "Docker Engine installiert.""#
        }
        "arch" => {
            r#"#!/bin/bash
set -euo pipefail
pacman -Sy --noconfirm docker docker-compose
systemctl enable --now docker
if [ -n "${SUDO_USER:-}" ]; then
  usermod -aG docker "$SUDO_USER"
fi
echo "Docker Engine installiert.""#
        }
        _ => {
            return Err(InstallError::Message(
                "Automatische Installation für diese Distribution nicht unterstützt. Bitte manuelle Anleitung verwenden.".to_string(),
            ));
        }
    };

    run_pkexec_script(script)
}

pub fn install_docker_desktop() -> Result<String, InstallError> {
    let script = r#"#!/bin/bash
set -euo pipefail
TMP=$(mktemp -d)
cd "$TMP"
wget -q https://desktop.docker.com/linux/main/amd64/docker-desktop-amd64.deb -O docker-desktop.deb
apt-get install -y ./docker-desktop.deb || dpkg -i ./docker-desktop.deb
echo "Docker Desktop installiert.""#;

    run_pkexec_script(script)
}

fn run_pkexec_script(script: &str) -> Result<String, InstallError> {
    let script_path = std::env::temp_dir().join("open-notebook-docker-install.sh");
    fs::write(&script_path, script).map_err(|e| InstallError::Message(e.to_string()))?;

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&script_path, fs::Permissions::from_mode(0o755))
            .map_err(|e| InstallError::Message(e.to_string()))?;
    }

    let output = Command::new("pkexec")
        .arg("bash")
        .arg(&script_path)
        .output()
        .map_err(|e| InstallError::Message(format!("pkexec fehlgeschlagen: {e}")))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if output.status.success() {
        Ok(format!("{stdout}{stderr}"))
    } else {
        Err(InstallError::Message(format!(
            "Installation fehlgeschlagen:\n{stdout}{stderr}"
        )))
    }
}

pub fn verify_installation() -> String {
    let status = check_docker_status();
    if status.available && status.daemon_running && status.compose_available {
        if status.user_in_docker_group {
            "Docker wurde erfolgreich installiert und ist einsatzbereit.".to_string()
        } else {
            "Docker ist installiert. Bitte abmelden und neu anmelden, damit die docker-Gruppe wirksam wird.".to_string()
        }
    } else {
        status.message
    }
}

pub fn start_docker_service() -> Result<String, InstallError> {
    let output = Command::new("pkexec")
        .args(["systemctl", "start", "docker"])
        .output()
        .map_err(|e| InstallError::Message(e.to_string()))?;

    if output.status.success() {
        Ok("Docker-Dienst gestartet.".to_string())
    } else {
        Err(InstallError::Message(
            String::from_utf8_lossy(&output.stderr).to_string(),
        ))
    }
}
