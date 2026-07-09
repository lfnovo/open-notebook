pub struct MenuLabels {
    pub app_menu: &'static str,
    pub dashboard: &'static str,
    pub logs: &'static str,
    pub settings: &'static str,
    pub open_notebook: &'static str,
    pub quit: &'static str,
}

pub fn menu_labels(language: &str) -> MenuLabels {
    if language == "de" {
        MenuLabels {
            app_menu: "Open Notebook",
            dashboard: "Verwaltung…",
            logs: "Logs…",
            settings: "Einstellungen…",
            open_notebook: "Open Notebook öffnen",
            quit: "Beenden",
        }
    } else {
        MenuLabels {
            app_menu: "Open Notebook",
            dashboard: "Management…",
            logs: "Logs…",
            settings: "Settings…",
            open_notebook: "Open Notebook",
            quit: "Quit",
        }
    }
}
