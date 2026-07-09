import type { Language } from "./languages";

export type TranslationTree = {
  [key: string]: string | TranslationTree;
};

export const translations: Record<Language, TranslationTree> = {
  de: {
    common: {
      appName: "Open Notebook Desktop",
      back: "Zurück",
      save: "Speichern",
      loading: "Lade Open Notebook Desktop...",
      success: "Erfolgreich.",
      actionSuccess: "Aktion erfolgreich.",
      yes: "Ja",
      no: "Nein",
      language: "Sprache",
      version: "Version",
      state: "Status",
      notFound: "Nicht gefunden",
    },
    welcome: {
      title: "Willkommen",
      subtitle:
        "Open Notebook als native Linux-Desktop-App. Die Anwendung verwaltet den Docker-Stack im Hintergrund und öffnet die Web-Oberfläche in einem eigenen Fenster.",
      expectedTitle: "Was dich erwartet:",
      item1: "Geführtes Onboarding für Docker und Verschlüsselung",
      item2: "Start, Stopp und Logs des Open-Notebook-Stacks",
      item3: "Native Desktop-Oberfläche ohne manuelles Terminal",
      license:
        "Open Notebook ist MIT-lizenziert. Deine Daten bleiben lokal unter ~/.local/share/open-notebook-desktop.",
      startSetup: "Einrichtung starten",
      detectedLanguage: "Erkannte Systemsprache: {{language}}",
    },
    docker: {
      title: "Docker einrichten",
      subtitle:
        "Open Notebook läuft in Containern. Zuerst prüfen wir, ob Docker auf deinem System bereit ist.",
      loadingStatus: "Lade Status...",
      cliFound: "CLI gefunden",
      cliMissing: "CLI fehlt",
      daemonActive: "Daemon aktiv",
      daemonInactive: "Daemon inaktiv",
      composeAvailable: "Compose verfügbar",
      composeMissing: "Compose fehlt",
      groupOk: "docker-Gruppe OK",
      groupMissing: "Gruppe fehlt",
      detectedSystem: "Erkanntes System: {{name}} ({{family}})",
      autoInstallTitle: "Automatische Installation",
      autoInstallHint:
        "Die Installation nutzt pkexec und fragt nach deinem Administrator-Passwort.",
      installEngine: "Docker Engine installieren",
      installDesktop: "Docker Desktop installieren",
      startDaemon: "Docker-Dienst starten",
      refreshStatus: "Status aktualisieren",
      manualTitle: "Manuelle Anleitung",
      openDocs: "Offizielle Docker-Doku öffnen",
      continue: "Weiter zur Verschlüsselung",
      daemonStarted: "Docker-Dienst gestartet.",
      stepProgress: "Schritt {{current}} von {{total}}",
      recommendedAction: "Empfohlene Aktion",
      advancedOptions: "Weitere Optionen",
      showAdvanced: "Erweiterte Optionen anzeigen",
      hideAdvanced: "Erweiterte Optionen ausblenden",
      checklistTitle: "Voraussetzungen",
      technicalDetails: "Technische Details",
      checklist: {
        cliOk: "Docker CLI installiert",
        cliMissing: "Docker CLI fehlt",
        daemonOk: "Docker-Dienst läuft",
        daemonMissing: "Docker-Dienst gestoppt",
        composeOk: "Docker Compose verfügbar",
        composeMissing: "Docker Compose fehlt",
        groupOk: "Benutzer in docker-Gruppe",
        groupMissing: "Benutzer nicht in docker-Gruppe",
      },
      guidance: {
        ready: {
          headline: "Docker ist einsatzbereit",
          description:
            "Alle Voraussetzungen sind erfüllt. Als Nächstes richtest du den Verschlüsselungsschlüssel ein — danach kann Open Notebook starten.",
          action: "Weiter zur Verschlüsselung",
        },
        cliMissing: {
          headline: "Docker muss installiert werden",
          description:
            "Auf deinem System wurde Docker noch nicht gefunden. Für Linux empfehlen wir Docker Engine — leichtgewichtig und ideal für Open Notebook.",
          action: "Docker Engine jetzt installieren",
          hint: "Die Installation fragt nach deinem Administrator-Passwort. Danach wirst du automatisch weitergeführt.",
        },
        daemonStopped: {
          headline: "Docker-Dienst starten",
          description:
            "Docker ist installiert, aber der Hintergrunddienst läuft nicht. Starte ihn mit einem Klick — danach prüfen wir den Status erneut.",
          action: "Docker-Dienst jetzt starten",
          hint: "Falls das nicht funktioniert, starte Docker manuell mit: sudo systemctl start docker",
        },
        composeMissing: {
          headline: "Docker Compose fehlt",
          description:
            "Docker ist installiert, aber das Compose-Plugin fehlt. Open Notebook benötigt Compose, um den Stack zu starten.",
          action: "Docker Engine mit Compose installieren",
          hint: "Alternativ: sudo apt install docker-compose-plugin (Debian/Ubuntu)",
        },
        groupMissing: {
          headline: "Neu anmelden erforderlich",
          description:
            "Docker läuft, aber dein Benutzer hat noch keine Berechtigung. Melde dich ab und wieder an (oder starte den PC neu), damit die docker-Gruppe wirksam wird.",
          action: "Status erneut prüfen",
          hint: "Falls du Docker gerade installiert hast: sudo usermod -aG docker $USER — danach abmelden und neu anmelden.",
        },
      },
      status: {
        cliMissing: "Docker CLI nicht gefunden. Bitte Docker Engine oder Docker Desktop installieren.",
        daemonStopped:
          "Docker ist installiert, aber der Daemon läuft nicht. Starte den Docker-Dienst.",
        composeMissing: "Docker Compose Plugin nicht gefunden.",
        groupMissing:
          "Docker läuft, aber dein Benutzer ist nicht in der docker-Gruppe. Nach der Installation neu anmelden.",
        ready: "Docker ist bereit.",
      },
      install: {
        debian:
          "Manuelle Installation (Debian/Ubuntu):\n1. sudo apt update\n2. sudo apt install -y docker.io docker-compose-plugin\n3. sudo systemctl enable --now docker\n4. sudo usermod -aG docker $USER\n5. Abmelden und neu anmelden",
        fedora:
          "Manuelle Installation (Fedora):\n1. sudo dnf install -y docker docker-compose\n2. sudo systemctl enable --now docker\n3. sudo usermod -aG docker $USER\n4. Abmelden und neu anmelden",
        arch:
          "Manuelle Installation (Arch):\n1. sudo pacman -S docker docker-compose\n2. sudo systemctl enable --now docker\n3. sudo usermod -aG docker $USER\n4. Abmelden und neu anmelden",
        unknown:
          "Allgemeine Anleitung:\nBesuche https://docs.docker.com/engine/install/ und installiere Docker Engine für deine Distribution.\nDanach: sudo usermod -aG docker $USER und neu anmelden.",
      },
    },
    splash: {
      title: "Open Notebook wird gestartet",
      subtitle: "Docker-Stack und Web-Oberfläche werden vorbereitet.",
      hint: "Beim ersten Start kann der Download der Images einige Minuten dauern.",
      phases: {
        checkingDocker: "Docker wird geprüft…",
        checkingStack: "Stack-Status wird geprüft…",
        pullingImages: "Docker-Images werden geladen…",
        startingStack: "Stack wird gestartet…",
        containersStarting: "Container starten…",
        waitingUi: "Web-Oberfläche wird vorbereitet…",
        opening: "Open Notebook wird geöffnet…",
        ready: "Fertig",
      },
    },
    encryption: {
      title: "Verschlüsselungsschlüssel",
      subtitle:
        "Dieser Schlüssel verschlüsselt gespeicherte API-Keys in der Open-Notebook-Datenbank. Bewahre ihn sicher auf.",
      keyLabel: "OPEN_NOTEBOOK_ENCRYPTION_KEY",
      generate: "Neuen Schlüssel generieren",
      save: "Speichern und Dashboard öffnen",
      dataDir: "Datenverzeichnis",
      keyRequired: "Bitte einen Verschlüsselungsschlüssel setzen.",
    },
    configError: {
      title: "Konfiguration beschädigt",
      subtitle: "Die gespeicherte Launcher-Konfiguration konnte nicht geladen werden.",
      fallback: "Die Konfiguration konnte nicht geladen werden.",
      hint: "Stelle config.json aus der Sicherungskopie wieder her, bevor du fortfährst. Ein neues Onboarding würde sonst einen neuen Verschlüsselungsschlüssel erzeugen.",
    },
    dashboard: {
      title: "Dashboard",
      subtitle: "Starte Open Notebook direkt — Verwaltung nur bei Bedarf über die Menüleiste.",
      managementSubtitle: "Verwaltung des Docker-Stacks und Status der Dienste.",
      menuHint: "Menüleiste oben: Verwaltung, Logs, Einstellungen, Open Notebook öffnen, Beenden.",
      logs: "Logs",
      settings: "Einstellungen",
      stackRunning: "Stack läuft",
      stackStopped: "Stack gestoppt",
      uiOnline: "UI erreichbar",
      uiOffline: "UI offline",
      loadingStatus: "Lade Status...",
      primaryStart: "Jetzt starten",
      primaryOpen: "Open Notebook öffnen",
      primaryRetry: "Erneut versuchen",
      autoStarting: "Stack wird automatisch gestartet...",
      servicesTitle: "Dienste",
      serviceRunning: "Läuft",
      serviceStopped: "Gestoppt",
      serviceMissing: "Nicht eingerichtet",
      advancedTitle: "Erweiterte Aktionen",
      advancedShow: "Anzeigen",
      advancedHide: "Ausblenden",
      reinitialize: "Neu einrichten",
      pullHint: "Docker-Images werden geladen — das kann beim ersten Mal einige Minuten dauern.",
      startingHint: "Container starten, bitte kurz warten...",
      readyHint: "Alles bereit. Klicke auf den Button, um Open Notebook zu öffnen.",
      stoppedHint: "Der Stack ist gestoppt. Klicke auf „Jetzt starten“, um fortzufahren.",
      missingHint: "Beim ersten Start werden die Docker-Images heruntergeladen und eingerichtet.",
      initStack: "Stack initialisieren",
      start: "Starten",
      restart: "Neustart",
      stop: "Stoppen",
      openApp: "App öffnen",
      initProgress: "Initialisiere Stack...",
      startProgress: "Starte Stack...",
      restartProgress: "Starte neu...",
      stopProgress: "Stoppe Stack...",
      waitForApp: "Warte auf Open Notebook...",
      appNotResponding: "Open Notebook antwortet nicht. Prüfe die Logs.",
      appOpened: "Open Notebook-Fenster geöffnet.",
      guidance: {
        loadingTitle: "Status wird geladen",
        loadingDescription: "Verbindung zum Docker-Stack wird geprüft.",
        missingTitle: "Ersteinrichtung nötig",
        missingDescription: "Open Notebook ist noch nicht eingerichtet.",
        stoppedTitle: "Stack ist gestoppt",
        stoppedDescription: "Starte den Stack, um Open Notebook zu nutzen.",
        startingTitle: "Fast fertig",
        startingDescription: "Die Container laufen, die Web-Oberfläche startet noch.",
        readyTitle: "Bereit",
        readyDescription: "Open Notebook läuft und ist erreichbar.",
      },
      progress: {
        initialize: "Richte Stack ein und lade Images...",
        start: "Starte Stack...",
        restart: "Starte Stack neu...",
        stop: "Stoppe Stack...",
      },
      containers: {
        surrealdb: "Datenbank (SurrealDB)",
        app: "Open Notebook",
      },
      status: {
        running: "Open Notebook läuft.",
        starting: "Container laufen, Web-UI antwortet noch nicht.",
        stopped: "Stack ist gestoppt.",
      },
    },
    logs: {
      title: "Container-Logs",
      subtitle: "Live-Ausgabe von SurrealDB und Open Notebook.",
      loading: "Lade Logs...",
      empty: "Keine Logs verfügbar.",
      refresh: "Aktualisieren",
      autoRefreshOn: "Auto-Refresh: An",
      autoRefreshOff: "Auto-Refresh: Aus",
    },
    settings: {
      title: "Einstellungen",
      subtitle: "Startverhalten, Datenpfad, Ports und Sprache.",
      dataDir: "Datenverzeichnis",
      uiPort: "UI-Port",
      apiPort: "API-Port",
      autoStartOnLaunch: "Stack beim App-Start automatisch starten",
      openNotebookDirectly: "Open Notebook direkt öffnen (Dashboard überspringen)",
      stopOnExit: "Container beim Beenden der App stoppen",
      encryptionSet: "Verschlüsselungsschlüssel ist gesetzt",
      invalidDataDir: "Bitte einen absoluten, nicht leeren Pfad für das Datenverzeichnis angeben.",
      invalidPort: "Ports müssen ganze Zahlen zwischen 1 und 65535 sein.",
      saved: "Einstellungen gespeichert.",
    },
    updates: {
      title: "App-Updates",
      subtitle: "Prüfe auf neue Versionen und installiere Updates.",
      currentVersion: "Installierte Version",
      installType: "Installationsart",
      checkNow: "Nach Updates suchen",
      installAndRestart: "Installieren & neu starten",
      openReleasePage: "Release-Seite öffnen",
      dismiss: "Später",
      debHint:
        "Bei .deb-Installationen erfolgt das Update über den Paketmanager oder durch Herunterladen der neuen Version.",
      bannerAvailable: "Update verfügbar: Version {{version}}",
      bannerAvailableHint: "Ein Klick installiert die neue Version und startet die App neu.",
      bannerManaged: "Neue Version verfügbar: {{version}}",
      bannerManagedHint:
        "Deine Installation nutzt ein .deb-Paket. Bitte lade die neue Version von der Release-Seite herunter.",
      status: {
        idle: "Noch nicht geprüft.",
        checking: "Suche nach Updates...",
        uptodate: "Du verwendest die neueste Version.",
        available: "Update verfügbar: {{version}}",
        managed: "Neue Version verfügbar: {{version}} (manuell installieren)",
        downloading: "Download läuft... {{progress}}%",
        readyRestart: "Update installiert. App wird neu gestartet...",
        error: "Update-Prüfung fehlgeschlagen.",
        unsupported: "Updates sind im Entwicklungsmodus deaktiviert.",
      },
      channel: {
        appimage: "AppImage (In-App-Update möglich)",
        deb: ".deb-Paket (Update über Release-Seite)",
        development: "Entwicklungsmodus",
        unknown: "Unbekannt",
      },
    },
  },
  en: {
    common: {
      appName: "Open Notebook Desktop",
      back: "Back",
      save: "Save",
      loading: "Loading Open Notebook Desktop...",
      success: "Success.",
      actionSuccess: "Action completed.",
      yes: "Yes",
      no: "No",
      language: "Language",
      version: "Version",
      state: "State",
      notFound: "Not found",
    },
    welcome: {
      title: "Welcome",
      subtitle:
        "Open Notebook as a native Linux desktop app. It manages the Docker stack in the background and opens the web UI in its own window.",
      expectedTitle: "What to expect:",
      item1: "Guided onboarding for Docker and encryption",
      item2: "Start, stop, and view logs for the Open Notebook stack",
      item3: "Native desktop experience without manual terminal work",
      license:
        "Open Notebook is MIT licensed. Your data stays local under ~/.local/share/open-notebook-desktop.",
      startSetup: "Start setup",
      detectedLanguage: "Detected system language: {{language}}",
    },
    docker: {
      title: "Set up Docker",
      subtitle:
        "Open Notebook runs in containers. First we check whether Docker is ready on your system.",
      loadingStatus: "Loading status...",
      cliFound: "CLI found",
      cliMissing: "CLI missing",
      daemonActive: "Daemon active",
      daemonInactive: "Daemon inactive",
      composeAvailable: "Compose available",
      composeMissing: "Compose missing",
      groupOk: "docker group OK",
      groupMissing: "Group missing",
      detectedSystem: "Detected system: {{name}} ({{family}})",
      autoInstallTitle: "Automatic installation",
      autoInstallHint:
        "Installation uses pkexec and will ask for your administrator password.",
      installEngine: "Install Docker Engine",
      installDesktop: "Install Docker Desktop",
      startDaemon: "Start Docker service",
      refreshStatus: "Refresh status",
      manualTitle: "Manual instructions",
      openDocs: "Open official Docker docs",
      continue: "Continue to encryption",
      daemonStarted: "Docker service started.",
      stepProgress: "Step {{current}} of {{total}}",
      recommendedAction: "Recommended action",
      advancedOptions: "More options",
      showAdvanced: "Show advanced options",
      hideAdvanced: "Hide advanced options",
      checklistTitle: "Requirements",
      technicalDetails: "Technical details",
      checklist: {
        cliOk: "Docker CLI installed",
        cliMissing: "Docker CLI missing",
        daemonOk: "Docker service running",
        daemonMissing: "Docker service stopped",
        composeOk: "Docker Compose available",
        composeMissing: "Docker Compose missing",
        groupOk: "User in docker group",
        groupMissing: "User not in docker group",
      },
      guidance: {
        ready: {
          headline: "Docker is ready",
          description:
            "All requirements are met. Next, set up your encryption key — then Open Notebook can start.",
          action: "Continue to encryption",
        },
        cliMissing: {
          headline: "Docker needs to be installed",
          description:
            "Docker was not found on your system. For Linux we recommend Docker Engine — lightweight and ideal for Open Notebook.",
          action: "Install Docker Engine now",
          hint: "Installation will ask for your administrator password. You will be guided through the next steps automatically.",
        },
        daemonStopped: {
          headline: "Start Docker service",
          description:
            "Docker is installed but the background service is not running. Start it with one click — we will check the status again afterwards.",
          action: "Start Docker service now",
          hint: "If that does not work, start Docker manually with: sudo systemctl start docker",
        },
        composeMissing: {
          headline: "Docker Compose is missing",
          description:
            "Docker is installed but the Compose plugin is missing. Open Notebook needs Compose to start the stack.",
          action: "Install Docker Engine with Compose",
          hint: "Alternatively: sudo apt install docker-compose-plugin (Debian/Ubuntu)",
        },
        groupMissing: {
          headline: "Log out and back in required",
          description:
            "Docker is running but your user does not have permission yet. Log out and back in (or restart your PC) so the docker group takes effect.",
          action: "Check status again",
          hint: "If you just installed Docker: sudo usermod -aG docker $USER — then log out and back in.",
        },
      },
      status: {
        cliMissing: "Docker CLI not found. Please install Docker Engine or Docker Desktop.",
        daemonStopped:
          "Docker is installed but the daemon is not running. Start the Docker service.",
        composeMissing: "Docker Compose plugin not found.",
        groupMissing:
          "Docker is running but your user is not in the docker group. Log out and back in after installation.",
        ready: "Docker is ready.",
      },
      install: {
        debian:
          "Manual installation (Debian/Ubuntu):\n1. sudo apt update\n2. sudo apt install -y docker.io docker-compose-plugin\n3. sudo systemctl enable --now docker\n4. sudo usermod -aG docker $USER\n5. Log out and back in",
        fedora:
          "Manual installation (Fedora):\n1. sudo dnf install -y docker docker-compose\n2. sudo systemctl enable --now docker\n3. sudo usermod -aG docker $USER\n4. Log out and back in",
        arch:
          "Manual installation (Arch):\n1. sudo pacman -S docker docker-compose\n2. sudo systemctl enable --now docker\n3. sudo usermod -aG docker $USER\n4. Log out and back in",
        unknown:
          "General instructions:\nVisit https://docs.docker.com/engine/install/ and install Docker Engine for your distribution.\nThen run: sudo usermod -aG docker $USER and log out and back in.",
      },
    },
    splash: {
      title: "Starting Open Notebook",
      subtitle: "Preparing the Docker stack and web interface.",
      hint: "The first start may take a few minutes while Docker images are downloaded.",
      phases: {
        checkingDocker: "Checking Docker…",
        checkingStack: "Checking stack status…",
        pullingImages: "Downloading Docker images…",
        startingStack: "Starting stack…",
        containersStarting: "Starting containers…",
        waitingUi: "Preparing web interface…",
        opening: "Opening Open Notebook…",
        ready: "Ready",
      },
    },
    encryption: {
      title: "Encryption key",
      subtitle:
        "This key encrypts stored API keys in the Open Notebook database. Keep it safe.",
      keyLabel: "OPEN_NOTEBOOK_ENCRYPTION_KEY",
      generate: "Generate new key",
      save: "Save and open dashboard",
      dataDir: "Data directory",
      keyRequired: "Please set an encryption key.",
    },
    configError: {
      title: "Configuration error",
      subtitle: "The saved launcher configuration could not be loaded.",
      fallback: "The configuration could not be loaded.",
      hint: "Restore config.json from the backup copy before continuing. A fresh onboarding would generate a new encryption key.",
    },
    dashboard: {
      title: "Dashboard",
      subtitle: "Launch Open Notebook directly — management via the menu bar when needed.",
      managementSubtitle: "Manage the Docker stack and check service status.",
      menuHint: "Menu bar: Management, Logs, Settings, Open Notebook, Quit.",
      logs: "Logs",
      settings: "Settings",
      stackRunning: "Stack running",
      stackStopped: "Stack stopped",
      uiOnline: "UI reachable",
      uiOffline: "UI offline",
      loadingStatus: "Loading status...",
      primaryStart: "Start now",
      primaryOpen: "Open Open Notebook",
      primaryRetry: "Try again",
      autoStarting: "Starting stack automatically...",
      servicesTitle: "Services",
      serviceRunning: "Running",
      serviceStopped: "Stopped",
      serviceMissing: "Not set up",
      advancedTitle: "Advanced actions",
      advancedShow: "Show",
      advancedHide: "Hide",
      reinitialize: "Set up again",
      pullHint: "Downloading Docker images — this can take a few minutes the first time.",
      startingHint: "Containers are starting, please wait a moment...",
      readyHint: "All set. Click the button to open Open Notebook.",
      stoppedHint: "The stack is stopped. Click “Start now” to continue.",
      missingHint: "The first start downloads Docker images and sets everything up.",
      initStack: "Initialize stack",
      start: "Start",
      restart: "Restart",
      stop: "Stop",
      openApp: "Open app",
      initProgress: "Initializing stack...",
      startProgress: "Starting stack...",
      restartProgress: "Restarting...",
      stopProgress: "Stopping stack...",
      waitForApp: "Waiting for Open Notebook...",
      appNotResponding: "Open Notebook is not responding. Check the logs.",
      appOpened: "Open Notebook window opened.",
      guidance: {
        loadingTitle: "Loading status",
        loadingDescription: "Checking connection to the Docker stack.",
        missingTitle: "First-time setup required",
        missingDescription: "Open Notebook has not been set up yet.",
        stoppedTitle: "Stack is stopped",
        stoppedDescription: "Start the stack to use Open Notebook.",
        startingTitle: "Almost ready",
        startingDescription: "Containers are running, the web UI is still starting.",
        readyTitle: "Ready",
        readyDescription: "Open Notebook is running and reachable.",
      },
      progress: {
        initialize: "Setting up stack and pulling images...",
        start: "Starting stack...",
        restart: "Restarting stack...",
        stop: "Stopping stack...",
      },
      containers: {
        surrealdb: "Database (SurrealDB)",
        app: "Open Notebook",
      },
      status: {
        running: "Open Notebook is running.",
        starting: "Containers are running, web UI is not responding yet.",
        stopped: "Stack is stopped.",
      },
    },
    logs: {
      title: "Container logs",
      subtitle: "Live output from SurrealDB and Open Notebook.",
      loading: "Loading logs...",
      empty: "No logs available.",
      refresh: "Refresh",
      autoRefreshOn: "Auto-refresh: On",
      autoRefreshOff: "Auto-refresh: Off",
    },
    settings: {
      title: "Settings",
      subtitle: "Launch behavior, data path, ports, and language.",
      dataDir: "Data directory",
      uiPort: "UI port",
      apiPort: "API port",
      autoStartOnLaunch: "Start stack automatically when opening the app",
      openNotebookDirectly: "Open Open Notebook directly (skip dashboard)",
      stopOnExit: "Stop containers when closing the app",
      encryptionSet: "Encryption key is set",
      invalidDataDir: "Please provide an absolute, non-empty data directory path.",
      invalidPort: "Ports must be whole numbers between 1 and 65535.",
      saved: "Settings saved.",
    },
    updates: {
      title: "App updates",
      subtitle: "Check for new versions and install updates.",
      currentVersion: "Installed version",
      installType: "Installation type",
      checkNow: "Check for updates",
      installAndRestart: "Install & restart",
      openReleasePage: "Open release page",
      dismiss: "Later",
      debHint:
        "For .deb installations, update via your package manager or by downloading the new version.",
      bannerAvailable: "Update available: version {{version}}",
      bannerAvailableHint: "One click installs the new version and restarts the app.",
      bannerManaged: "New version available: {{version}}",
      bannerManagedHint:
        "Your installation uses a .deb package. Please download the new version from the release page.",
      status: {
        idle: "Not checked yet.",
        checking: "Checking for updates...",
        uptodate: "You are on the latest version.",
        available: "Update available: {{version}}",
        managed: "New version available: {{version}} (install manually)",
        downloading: "Downloading... {{progress}}%",
        readyRestart: "Update installed. Restarting app...",
        error: "Update check failed.",
        unsupported: "Updates are disabled in development mode.",
      },
      channel: {
        appimage: "AppImage (in-app update supported)",
        deb: ".deb package (update via release page)",
        development: "Development mode",
        unknown: "Unknown",
      },
    },
  },
};

function resolve(tree: TranslationTree, key: string): string | undefined {
  const parts = key.split(".");
  let current: string | TranslationTree | undefined = tree;
  for (const part of parts) {
    if (!current || typeof current === "string") return undefined;
    current = current[part];
  }
  return typeof current === "string" ? current : undefined;
}

export function translate(
  language: Language,
  key: string,
  vars?: Record<string, string>,
): string {
  const value =
    resolve(translations[language], key) ??
    resolve(translations.en, key) ??
    key;

  if (!vars) return value;
  return Object.entries(vars).reduce((result, [name, replacement]) => {
    const pattern = new RegExp(`\\{\\{${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\}\\}`, "g");
    return result.replace(pattern, () => replacement);
  }, value);
}
