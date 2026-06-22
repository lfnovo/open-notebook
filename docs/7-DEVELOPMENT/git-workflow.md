# Git Workflow für Issue-Bearbeitung und PR-Erstellung

Dieses Dokument beschreibt den Workflow für die Bearbeitung von Issues und das Erstellen von Pull Requests im `D-revv/open-notebook` Fork.

## 📋 Repository-Struktur

```
Upstream:    https://github.com/lfnovo/open-notebook (main branch)
     ↑
     | (Pull Requests)
     |
Fork:        https://github.com/D-revv/open-notebook
     |
     | (Remote: origin-fork)
     ↓
Lokal:       C:\Users\T11\SynologyDrive\LLM\open-notebook
     |
     | (Remote: origin = Docker Host Git-Server)
     ↓
Docker Host: http://192.168.178.30:3000/malte/open-notebook.git
```

### Git Remotes
```bash
origin     -> Docker Host Git-Server (192.168.178.30:3000)
origin-fork -> GitHub Fork (D-revv/open-notebook)
```

## 🔄 Issue-Bearbeitungs-Workflow

### 1. Issue auswählen

**Entweder:**
- Bestehendes Issue im GitHub Fork auswählen
- Neues Issue erstellen (falls erforderlich)

### 2. Feature Branch erstellen

```bash
# Auf main updaten
git checkout main
git pull origin-fork main

# Feature Branch erstellen (benannt nach Issue)
git checkout -b fix/893-worker-max-tasks-env
# oder: git checkout -b feature/neues-feature
```

**Branch-Naming Convention:**
- `fix/<issue-number>-kurze-beschreibung` für Bugfixes
- `feature/<issue-number>-kurze-beschreibung` für neue Features
- `docs/<issue-number>-kurze-beschreibung` für Dokumentationsänderungen

### 3. Entwicklung mit Hot-Reload

**Services starten** (in separaten Terminals):

```powershell
# Terminal 1 - SurrealDB
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make database"

# Terminal 2 - API Backend (Hot-Reload)
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 5055"

# Terminal 3 - Frontend (Hot-Reload)
wsl --exec bash -c "export NVM_DIR=/home/t11/.nvm && [ -s \$NVM_DIR/nvm.sh ] && . \$NVM_DIR/nvm.sh && nvm use 20 && cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend && npm run dev"
```

**Entwickeln:**
- Code-Änderungen werden automatisch neu geladen
- Testen Sie Ihre Änderungen live im Browser (http://localhost:3000)
- API Tests über http://localhost:5055/docs

### 4. Änderungen committen

**Vor dem Commit:**
```bash
# Status prüfen
git status

# Änderungen ansehen
git diff

# Linting/Tests laufen lassen (optional aber empfohlen)
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && uv run ruff check ."
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && uv run pytest tests/"
```

**Commit-Nachricht konventionen:**
```bash
# Format: [type] Kurze Beschreibung (Issue #XYZ)
# Types: feat, fix, docs, style, refactor, test, chore

git add .
git commit -m "[feat] Add worker concurrency control via ENV variable (Issue #893)"
```

**Commit-Typen:**
- `feat`: Neues Feature
- `fix`: Bugfix
- `docs`: Dokumentation
- `refactor`: Code-Umstrukturierung
- `test`: Tests hinzufügen/ändern
- `chore`: Build/Dependencies

### 5. Zum Fork pushen

```bash
# Zum GitHub Fork pushen
git push origin-fork fix/893-worker-max-tasks-env
```

### 6. Pull Request erstellen

**Über GitHub Web UI:**
1. Zu `https://github.com/D-revv/open-notebook` gehen
2. "Compare & pull request" für Ihren Branch klicken
3. PR-Basis wählen:
   - **Base repository**: `lfnovo/open-notebook`
   - **Base branch**: `main`
   - **Head repository**: `D-revv/open-notebook`
   - **Head branch**: `fix/893-worker-max-tasks-env`

**PR-Beschreibung:**
```markdown
## Beschreibung
Kurze Beschreibung der Änderungen

## Gelöstes Issue
Closes #893 (falls zutreffend)

## Änderungen
- [x] Feature X implementiert
- [x] Tests hinzugefügt
- [x] Dokumentation aktualisiert

## Testing
- [x] Lokale Tests bestanden
- [ ] Code Review erforderlich

## Screenshots (falls zutreffend)
[Bildschirmfotos von UI-Änderungen]
```

## 🔀 Synchronisation mit Upstream

### Upstream Änderungen holen

```bash
# Upstream remote hinzufügen (falls nicht existiert)
git remote add upstream https://github.com/lfnovo/open-notebook.git

# Upstream main aktualisieren
git fetch upstream
git checkout main
git merge upstream/main

# Lokalen Fork aktualisieren
git push origin-fork main
```

### Feature Branch mit Upstream synchron halten

```bash
# Auf Feature Branch wechseln
git checkout fix/893-worker-max-tasks-env

# Upstream main in Branch mergen/rebase
git merge upstream/main
# oder: git rebase upstream/main

# Pushen (ggf. force push bei rebase)
git push origin-fork fix/893-worker-max-tasks-env
```

## 🧹 Branch-Bereinigung

### Nach PR-Merge

```bash
# Lokalen Branch löschen
git checkout main
git branch -d fix/893-worker-max-tasks-env

# Remote Branch löschen
git push origin-fork --delete fix/893-worker-max-tasks-env
```

### Ungenutzte Branches aufräumen

```bash
# Alle gelöschten Remote-Branches nachsyncen
git fetch origin-fork --prune

# Lokale Branches nach main prüfen
git branch --merged main | grep -v "^\* main" | xargs git branch -d
```

## 📝 Beispiel-Workflow: Issue #893

```bash
# 1. Branch erstellen
git checkout main
git pull origin-fork main
git checkout -b fix/893-worker-max-tasks-env

# 2. Entwickeln (mit Hot-Reload in 3 Terminals)
# ... Code schreiben und testen ...

# 3. Committen
git add .
git commit -m "[feat] Add OPEN_NOTEBOOK_WORKER_MAX_TASKS environment variable (Issue #893)"

# 4. Tests laufen lassen
wsl --exec bash -c "uv run pytest tests/"

# 5. Pushen
git push origin-fork fix/893-worker-max-tasks-env

# 6. PR auf GitHub erstellen
# -> https://github.com/D-revv/open-notebook/compare/main...fix/893-worker-max-tasks-env

# 7. Nach Merge aufräumen
git checkout main
git branch -d fix/893-worker-max-tasks-env
git push origin-fork --delete fix/893-worker-max-tasks-env
```

## 🐛 Troubleshooting

### Push wird abgelehnt

```bash
# Remote Branch ist weiter entwickelt
git pull origin-fork <branch-name>
# Änderungen mergen, dann erneut pushen
git push origin-fork <branch-name>
```

### Conflicts beim Merge

```bash
# Conflicts auflösen
# Dateien in Editor öffnen und Konflikte markieren entfernen

# Nach Auflösung:
git add .
git commit  # Bei Merge
# oder:
git rebase --continue  # Bei Rebase
```

### Falscher Branch committed

```bash
# Commits zurücksetzen (aber behalten)
git reset --soft HEAD~1

# Auf richtigen Branch
git checkout correct-branch
git cherry-pick <commit-hash>

# Original Branch korrigieren
git checkout wrong-branch
git reset --hard HEAD~1
```

## 🔐 Git Konfiguration

**Empfohlene Einstellungen:**
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false  # Oder true für rebase workflow
git config --global merge.ff only      # Nur fast-forward merges
```

## 📚 Weitere Ressourcen

- [GitHub Pull Requests](https://docs.github.com/en/pull-requests)
- [Git Branching Workflow](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Open Notebook AGENTS.md](../AGENTS.md)
