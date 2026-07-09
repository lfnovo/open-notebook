mod config;
mod docker;
mod install;
mod menu;
mod update;

use config::{
    detect_system_locale, ensure_compose_file, generate_encryption_key, load_config, save_config,
    AppConfig,
};
use docker::{
    check_docker_status, compose_down, compose_logs, compose_pull, compose_up,
    get_stack_status_bollard, wait_for_health, wait_for_health_async,
    wait_for_health_with_progress, DockerStatus, StackStatus,
};
use install::{
    detect_distro, get_manual_install_instructions, install_docker_desktop, install_docker_engine,
    start_docker_service, verify_installation, DistroInfo,
};
use menu::menu_labels;
use update::{get_install_context, InstallContext};
use serde::Serialize;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    AppHandle, Emitter, Manager, RunEvent, State, WebviewUrl,
};
use tauri_plugin_opener::OpenerExt;

struct AppState {
    config: Mutex<AppConfig>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct LaunchProgress {
    percent: u8,
    phase: String,
}

fn emit_launch_progress(app: &AppHandle, percent: u8, phase: &str) {
    let _ = app.emit(
        "launch-progress",
        LaunchProgress {
            percent,
            phase: phase.to_string(),
        },
    );
}

fn get_config_from_state(app: &AppHandle) -> AppConfig {
    app.state::<AppState>()
        .config
        .lock()
        .map(|c| c.clone())
        .unwrap_or_default()
}

fn build_app_menu(app: &AppHandle, language: &str) -> Result<Menu<tauri::Wry>, tauri::Error> {
    let labels = menu_labels(language);

    let dashboard =
        MenuItem::with_id(app, "dashboard", labels.dashboard, true, None::<&str>)?;
    let logs = MenuItem::with_id(app, "logs", labels.logs, true, None::<&str>)?;
    let settings = MenuItem::with_id(app, "settings", labels.settings, true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let open_notebook =
        MenuItem::with_id(app, "open-notebook", labels.open_notebook, true, None::<&str>)?;
    let quit = PredefinedMenuItem::quit(app, Some(labels.quit))?;

    let app_menu = Submenu::with_items(
        app,
        labels.app_menu,
        true,
        &[&dashboard, &logs, &settings, &separator, &open_notebook, &quit],
    )?;

    Menu::with_items(app, &[&app_menu])
}

fn refresh_app_menu(app: &AppHandle, language: &str) {
    if let Ok(menu) = build_app_menu(app, language) {
        let _ = app.set_menu(menu);
    }
}

fn show_launcher(app: &AppHandle, screen: &str) {
    let _ = app.emit("navigate-screen", screen);
    if let Some(main) = app.get_webview_window("main") {
        let _ = main.show();
        let _ = main.set_focus();
        let _ = main.unminimize();
    }
}

fn focus_notebook(app: &AppHandle) {
    if let Some(notebook) = app.get_webview_window("notebook") {
        let _ = notebook.show();
        let _ = notebook.set_focus();
        let _ = notebook.unminimize();
    }
}

async fn open_notebook_window_async(app: &AppHandle, config: &AppConfig) -> Result<(), String> {
    if !wait_for_health_async(config.ui_port, 5).await {
        return Err(
            "Open Notebook antwortet noch nicht. Bitte warte, bis der Stack läuft.".to_string(),
        );
    }

    let url = format!("http://127.0.0.1:{}", config.ui_port);
    let parsed_url: url::Url = url.parse().map_err(|e: url::ParseError| e.to_string())?;

    if let Some(window) = app.get_webview_window("notebook") {
        window
            .navigate(parsed_url.clone())
            .map_err(|e| e.to_string())?;
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    tauri::WebviewWindowBuilder::new(app, "notebook", WebviewUrl::External(parsed_url))
        .title("Open Notebook")
        .inner_size(1280.0, 800.0)
        .min_inner_size(900.0, 600.0)
        .build()
        .map_err(|e| e.to_string())?;

    Ok(())
}

fn open_notebook_window_internal(app: &AppHandle, config: &AppConfig) -> Result<(), String> {
    if !wait_for_health("127.0.0.1", config.ui_port, 5) {
        return Err(
            "Open Notebook antwortet noch nicht. Bitte warte, bis der Stack läuft.".to_string(),
        );
    }

    let url = format!("http://127.0.0.1:{}", config.ui_port);
    let parsed_url: url::Url = url.parse().map_err(|e: url::ParseError| e.to_string())?;

    if let Some(window) = app.get_webview_window("notebook") {
        window
            .navigate(parsed_url.clone())
            .map_err(|e| e.to_string())?;
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    tauri::WebviewWindowBuilder::new(app, "notebook", WebviewUrl::External(parsed_url))
        .title("Open Notebook")
        .inner_size(1280.0, 800.0)
        .min_inner_size(900.0, 600.0)
        .build()
        .map_err(|e| e.to_string())?;

    Ok(())
}

async fn ensure_stack_running(app: &AppHandle, config: &AppConfig) -> Result<(), String> {
    emit_launch_progress(app, 5, "checkingDocker");

    if config.encryption_key.is_empty() {
        return Err("Verschlüsselungsschlüssel fehlt. Bitte Onboarding abschließen.".to_string());
    }

    emit_launch_progress(app, 10, "checkingStack");
    let status = get_stack_status_bollard(config.ui_port)
        .await
        .map_err(|e| e.to_string())?;

    if status.healthy {
        emit_launch_progress(app, 40, "containersStarting");
        return Ok(());
    }

    let bundled = app
        .path()
        .resource_dir()
        .ok()
        .map(|dir| dir.join("docker-compose.yml"));

    ensure_compose_file(
        PathBuf::from(&config.data_dir).as_path(),
        bundled.as_deref(),
    )
    .map_err(|e| e.to_string())?;

    let needs_pull = status.containers.iter().any(|c| c.state == "missing");
    emit_launch_progress(
        app,
        15,
        if needs_pull {
            "pullingImages"
        } else {
            "startingStack"
        },
    );

    let data_dir = config.data_dir.clone();

    tokio::task::spawn_blocking(move || {
        if needs_pull {
            compose_pull(&data_dir)?;
        }
        compose_up(&data_dir)
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| e.to_string())?;

    emit_launch_progress(app, 35, "containersStarting");
    Ok(())
}

async fn run_launch_sequence(app: AppHandle, hide_main_on_success: bool) {
    emit_launch_progress(&app, 0, "checkingDocker");
    show_launcher(&app, "splash");
    if let Some(main) = app.get_webview_window("main") {
        let _ = main.show();
        let _ = main.set_focus();
        let _ = main.unminimize();
    }

    let config = get_config_from_state(&app);

    if config.auto_start_on_launch {
        if let Err(error) = ensure_stack_running(&app, &config).await {
            show_launcher(&app, "dashboard");
            let _ = app.emit("launch-error", error);
            return;
        }

        let app_handle = app.clone();
        let ui_port = config.ui_port;
        if !wait_for_health_with_progress(ui_port, 120, |percent| {
            emit_launch_progress(&app_handle, percent, "waitingUi");
        })
        .await
        {
            show_launcher(&app, "dashboard");
            let _ = app.emit(
                "launch-error",
                "Open Notebook antwortet nicht. Bitte prüfe die Logs im Dashboard.",
            );
            return;
        }
    } else if !wait_for_health_async(config.ui_port, 5).await {
        show_launcher(&app, "dashboard");
        let _ = app.emit(
            "launch-error",
            "Open Notebook antwortet noch nicht. Bitte warte, bis der Stack läuft.",
        );
        return;
    }

    emit_launch_progress(&app, 98, "opening");
    if let Err(error) = open_notebook_window_async(&app, &config).await {
        show_launcher(&app, "dashboard");
        let _ = app.emit("launch-error", error);
        return;
    }

    emit_launch_progress(&app, 100, "ready");
    let _ = app.emit("launch-complete", ());

    if hide_main_on_success && config.open_notebook_directly {
        if let Some(main) = app.get_webview_window("main") {
            let _ = main.hide();
        }
    }
}

fn spawn_stack_only(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let config = get_config_from_state(&app);
        if let Err(error) = ensure_stack_running(&app, &config).await {
            let _ = app.emit("launch-error", error);
        }
    });
}

fn spawn_direct_launch(app: AppHandle) {
    tauri::async_runtime::spawn(async move {
        let config = get_config_from_state(&app);

        if !config.onboarding_complete || !config.open_notebook_directly {
            return;
        }

        run_launch_sequence(app, true).await;
    });
}

fn handle_menu_event(app: &AppHandle, id: &str) {
    match id {
        "dashboard" => show_launcher(app, "dashboard"),
        "logs" => show_launcher(app, "logs"),
        "settings" => show_launcher(app, "settings"),
        "open-notebook" => {
            let app_handle = app.clone();
            tauri::async_runtime::spawn(async move {
                run_launch_sequence(app_handle, true).await;
            });
        }
        _ => {}
    }
}

#[tauri::command]
fn get_config(state: State<'_, AppState>) -> Result<AppConfig, String> {
    state
        .config
        .lock()
        .map(|c| c.clone())
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn save_app_config(
    config: AppConfig,
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<(), String> {
    let was_complete = state
        .config
        .lock()
        .map(|c| c.onboarding_complete)
        .unwrap_or(false);

    save_config(&config).map_err(|e| e.to_string())?;
    *state.config.lock().map_err(|e| e.to_string())? = config.clone();
    refresh_app_menu(&app, &config.language);

    if config.onboarding_complete && !was_complete && config.open_notebook_directly {
        spawn_direct_launch(app);
    }

    Ok(())
}

#[tauri::command]
fn detect_system_language() -> String {
    detect_system_locale()
}

#[tauri::command]
fn generate_key() -> String {
    generate_encryption_key()
}

#[tauri::command]
fn check_docker() -> DockerStatus {
    check_docker_status()
}

#[tauri::command]
fn detect_linux_distro() -> DistroInfo {
    detect_distro()
}

#[tauri::command]
fn get_install_instructions() -> String {
    get_manual_install_instructions(&detect_distro())
}

#[tauri::command]
fn install_engine() -> Result<String, String> {
    install_docker_engine(&detect_distro()).map_err(|e| e.to_string())
}

#[tauri::command]
fn install_desktop() -> Result<String, String> {
    install_docker_desktop().map_err(|e| e.to_string())
}

#[tauri::command]
fn verify_docker_install() -> String {
    verify_installation()
}

#[tauri::command]
fn start_docker_daemon() -> Result<String, String> {
    start_docker_service().map_err(|e| e.to_string())
}

#[tauri::command]
fn open_docker_docs(app: AppHandle) -> Result<(), String> {
    app.opener()
        .open_url("https://docs.docker.com/engine/install/", None::<&str>)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_install_context_cmd() -> InstallContext {
    get_install_context()
}

#[tauri::command]
fn open_release_page(app: AppHandle) -> Result<(), String> {
    let context = get_install_context();
    app.opener()
        .open_url(&context.release_page_url, None::<&str>)
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_stack_status(state: State<'_, AppState>) -> Result<StackStatus, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    get_stack_status_bollard(config.ui_port)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn initialize_stack(app: AppHandle, state: State<'_, AppState>) -> Result<String, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();

    if config.encryption_key.is_empty() {
        return Err("Verschlüsselungsschlüssel fehlt. Bitte Onboarding abschließen.".to_string());
    }

    let bundled = app
        .path()
        .resource_dir()
        .ok()
        .map(|dir| dir.join("docker-compose.yml"));

    let compose_path = ensure_compose_file(
        PathBuf::from(&config.data_dir).as_path(),
        bundled.as_deref(),
    )
    .map_err(|e| e.to_string())?;

    save_config(&config).map_err(|e| e.to_string())?;
    compose_pull(&config.data_dir).map_err(|e| e.to_string())?;
    compose_up(&config.data_dir).map_err(|e| e.to_string())?;

    Ok(format!(
        "Stack initialisiert unter {}",
        compose_path.display()
    ))
}

#[tauri::command]
fn start_stack(state: State<'_, AppState>) -> Result<String, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    compose_up(&config.data_dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn stop_stack(state: State<'_, AppState>) -> Result<String, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    compose_down(&config.data_dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn restart_stack(state: State<'_, AppState>) -> Result<String, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    compose_down(&config.data_dir).map_err(|e| e.to_string())?;
    compose_up(&config.data_dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn fetch_logs(state: State<'_, AppState>, tail: Option<usize>) -> Result<String, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    compose_logs(&config.data_dir, tail.unwrap_or(200)).map_err(|e| e.to_string())
}

#[tauri::command]
fn wait_for_app_ready(
    state: State<'_, AppState>,
    timeout_secs: Option<u64>,
) -> Result<bool, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    Ok(wait_for_health(
        "127.0.0.1",
        config.ui_port,
        timeout_secs.unwrap_or(60),
    ))
}

#[tauri::command]
fn open_notebook_window(app: AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    let config = state.config.lock().map_err(|e| e.to_string())?.clone();
    open_notebook_window_internal(&app, &config)
}

#[tauri::command]
fn show_launcher_window(app: AppHandle, screen: Option<String>) -> Result<(), String> {
    show_launcher(&app, screen.as_deref().unwrap_or("dashboard"));
    Ok(())
}

fn setup_app_state() -> AppState {
    let mut config = load_config().unwrap_or_default();
    if config.encryption_key.is_empty() && config.onboarding_complete {
        config.onboarding_complete = false;
    }
    AppState {
        config: Mutex::new(config),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .manage(setup_app_state())
        .setup(|app| {
            let config = get_config_from_state(&app.handle());
            refresh_app_menu(&app.handle(), &config.language);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_config,
            save_app_config,
            detect_system_language,
            generate_key,
            get_install_context_cmd,
            open_release_page,
            check_docker,
            detect_linux_distro,
            get_install_instructions,
            install_engine,
            install_desktop,
            verify_docker_install,
            start_docker_daemon,
            open_docker_docs,
            get_stack_status,
            initialize_stack,
            start_stack,
            stop_stack,
            restart_stack,
            fetch_logs,
            wait_for_app_ready,
            open_notebook_window,
            show_launcher_window
        ])
        .on_menu_event(|app, event| {
            handle_menu_event(app, event.id().as_ref());
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let app = window.app_handle();
                let config = get_config_from_state(&app);

                match window.label() {
                    "main" => {
                        if config.open_notebook_directly && config.onboarding_complete {
                            api.prevent_close();
                            let _ = window.hide();
                            focus_notebook(&app);
                        } else if config.stop_on_exit {
                            let _ = compose_down(&config.data_dir);
                        }
                    }
                    "notebook" => {
                        if config.stop_on_exit {
                            let _ = compose_down(&config.data_dir);
                        }
                        app.exit(0);
                    }
                    _ => {}
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let RunEvent::Ready = event {
                let config = get_config_from_state(app);
                if config.onboarding_complete {
                    if config.open_notebook_directly {
                        spawn_direct_launch(app.clone());
                    } else if config.auto_start_on_launch {
                        spawn_stack_only(app.clone());
                    }
                }
            }
        });
}
