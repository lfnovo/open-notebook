use serde::{Deserialize, Serialize};
use std::process::Command;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DockerStatus {
    pub available: bool,
    pub daemon_running: bool,
    pub version: Option<String>,
    pub compose_available: bool,
    pub user_in_docker_group: bool,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ContainerInfo {
    pub name: String,
    pub state: String,
    pub status: String,
    pub running: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StackStatus {
    pub running: bool,
    pub healthy: bool,
    pub containers: Vec<ContainerInfo>,
    pub message: String,
}

#[derive(Debug, Error)]
pub enum DockerError {
    #[error("{0}")]
    Message(String),
}

pub fn check_docker_status() -> DockerStatus {
    let version = run_command("docker", &["--version"]);
    let compose = run_command("docker", &["compose", "version"]);
    let daemon = run_command("docker", &["info", "--format", "{{.ServerVersion}}"]);
    let user_in_group = current_user_in_docker_group();

    let available = version.is_ok();
    let compose_available = compose.is_ok();
    let daemon_running = daemon.is_ok();
    let permission_denied = daemon
        .as_ref()
        .err()
        .is_some_and(|message| message.to_ascii_lowercase().contains("permission denied"));

    let message = if !available {
        "Docker CLI nicht gefunden. Bitte Docker Engine oder Docker Desktop installieren."
            .to_string()
    } else if !daemon_running && !user_in_group && permission_denied {
        "Docker läuft, aber dein Benutzer hat keine Berechtigung. Melde dich ab und wieder an, nachdem du in der docker-Gruppe bist.".to_string()
    } else if !daemon_running {
        "Docker ist installiert, aber der Daemon läuft nicht. Starte den Docker-Dienst.".to_string()
    } else if !compose_available {
        "Docker Compose Plugin nicht gefunden.".to_string()
    } else if !user_in_group {
        "Docker funktioniert, aber dein Benutzer ist nicht in der docker-Gruppe. Für dauerhaften Zugriff neu anmelden.".to_string()
    } else {
        "Docker ist bereit.".to_string()
    };

    DockerStatus {
        available,
        daemon_running,
        version: version.ok(),
        compose_available,
        user_in_docker_group: user_in_group,
        message,
    }
}

pub fn current_user_in_docker_group() -> bool {
    let output = Command::new("id").arg("-nG").output();
    match output {
        Ok(out) if out.status.success() => {
            let groups = String::from_utf8_lossy(&out.stdout);
            groups.split_whitespace().any(|g| g == "docker")
        }
        _ => false,
    }
}

pub fn run_command(program: &str, args: &[&str]) -> Result<String, String> {
    let output = Command::new(program)
        .args(args)
        .output()
        .map_err(|e| format!("Befehl fehlgeschlagen: {e}"))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        Err(if stderr.is_empty() {
            format!("{program} {} fehlgeschlagen", args.join(" "))
        } else {
            stderr
        })
    }
}

fn check_http_health(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{port}/");
    reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .ok()
        .and_then(|client| client.get(&url).send().ok())
        .map(|response| {
            response.status().is_success() || response.status().is_redirection()
        })
        .unwrap_or(false)
}

async fn is_ui_reachable(port: u16) -> bool {
    tokio::task::spawn_blocking(move || check_http_health(port))
        .await
        .unwrap_or(false)
}

fn is_transient_docker_error(message: &str) -> bool {
    let lower = message.to_ascii_lowercase();
    lower.contains("connection reset")
        || lower.contains("error receiving data")
        || lower.contains("broken pipe")
        || lower.contains("connection aborted")
}

async fn list_containers_with_retry() -> Result<Vec<bollard::models::ContainerSummary>, DockerError> {
    let docker = bollard::Docker::connect_with_local_defaults()
        .map_err(|e| DockerError::Message(e.to_string()))?;

    let mut last_error = None;

    for attempt in 0..3 {
        match docker
            .list_containers::<String>(Some(bollard::container::ListContainersOptions {
                all: true,
                ..Default::default()
            }))
            .await
        {
            Ok(containers) => return Ok(containers),
            Err(error) => {
                let message = error.to_string();
                if is_transient_docker_error(&message) && attempt < 2 {
                    last_error = Some(message);
                    tokio::time::sleep(std::time::Duration::from_millis(400)).await;
                    continue;
                }
                return Err(DockerError::Message(message));
            }
        }
    }

    Err(DockerError::Message(
        last_error.unwrap_or_else(|| "Docker-Verbindung fehlgeschlagen.".to_string()),
    ))
}

pub async fn get_stack_status_bollard(ui_port: u16) -> Result<StackStatus, DockerError> {
    let containers = list_containers_with_retry().await?;

    let target_names = [
        "open-notebook-desktop-surrealdb",
        "open-notebook-desktop-app",
    ];
    let mut infos = Vec::new();

    for target in target_names {
        let found = containers.iter().find(|c| {
            c.names
                .as_ref()
                .is_some_and(|names| names.iter().any(|n| n.trim_start_matches('/') == target))
        });

        if let Some(container) = found {
            let state = container.state.as_deref().unwrap_or("unknown").to_string();
            let status = container.status.as_deref().unwrap_or("unknown").to_string();
            infos.push(ContainerInfo {
                name: target.to_string(),
                running: state == "running",
                state,
                status,
            });
        } else {
            infos.push(ContainerInfo {
                name: target.to_string(),
                running: false,
                state: "missing".to_string(),
                status: "missing".to_string(),
            });
        }
    }

    let running = infos.iter().all(|c| c.running);
    let healthy = running && is_ui_reachable(ui_port).await;

    let message = if running && healthy {
        "Open Notebook läuft.".to_string()
    } else if running {
        "Container laufen, Web-UI antwortet noch nicht.".to_string()
    } else {
        "Stack ist gestoppt.".to_string()
    };

    Ok(StackStatus {
        running,
        healthy,
        containers: infos,
        message,
    })
}

pub fn compose_up(data_dir: &str) -> Result<String, DockerError> {
    let output = Command::new("docker")
        .args(["compose", "up", "-d", "--remove-orphans"])
        .current_dir(data_dir)
        .output()
        .map_err(|e| DockerError::Message(e.to_string()))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(DockerError::Message(format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )))
    }
}

pub fn compose_down(data_dir: &str) -> Result<String, DockerError> {
    let output = Command::new("docker")
        .args(["compose", "down"])
        .current_dir(data_dir)
        .output()
        .map_err(|e| DockerError::Message(e.to_string()))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(DockerError::Message(format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )))
    }
}

pub fn compose_pull(data_dir: &str) -> Result<String, DockerError> {
    let output = Command::new("docker")
        .args(["compose", "pull"])
        .current_dir(data_dir)
        .output()
        .map_err(|e| DockerError::Message(e.to_string()))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(DockerError::Message(format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )))
    }
}

pub fn compose_logs(data_dir: &str, tail: usize) -> Result<String, DockerError> {
    let tail_str = tail.to_string();
    let output = Command::new("docker")
        .args(["compose", "logs", "--no-color", "--tail", &tail_str])
        .current_dir(data_dir)
        .output()
        .map_err(|e| DockerError::Message(e.to_string()))?;

    if output.status.success() {
        Ok(format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        ))
    } else {
        Err(DockerError::Message(format!(
            "{}{}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )))
    }
}

pub async fn wait_for_health_async(port: u16, timeout_secs: u64) -> bool {
    wait_for_health_with_progress(port, timeout_secs, |_| {}).await
}

pub async fn wait_for_health_with_progress<F>(
    port: u16,
    timeout_secs: u64,
    mut on_progress: F,
) -> bool
where
    F: FnMut(u8),
{
    let start = tokio::time::Instant::now();
    let timeout = std::time::Duration::from_secs(timeout_secs);
    const START_PERCENT: u8 = 45;
    const END_PERCENT: u8 = 95;

    while start.elapsed() < timeout {
        if is_ui_reachable(port).await {
            on_progress(100);
            return true;
        }

        let ratio = (start.elapsed().as_secs_f32() / timeout.as_secs_f32()).clamp(0.0, 0.98);
        let span = (END_PERCENT - START_PERCENT) as f32;
        let percent = START_PERCENT + (span * ratio) as u8;
        on_progress(percent);
        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
    }

    false
}

pub fn wait_for_health(_host: &str, port: u16, timeout_secs: u64) -> bool {
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(timeout_secs);

    while std::time::Instant::now() < deadline {
        if check_http_health(port) {
            return true;
        }
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    false
}
