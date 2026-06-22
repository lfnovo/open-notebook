# WSL/Windows Setup für Open Notebook

Dieses Dokument beschreibt das lokale Entwicklungs-Setup auf Windows 11 mit WSL2.

## 📋 Systemkonfiguration

### Host System
- **OS**: Windows 11
- **WSL2**: Ubuntu 22.04 LTS
- **Docker**: Docker Desktop mit WSL2 Integration

### WSL2 Konfiguration (`.wslconfig`)
```ini
[wsl2]
processors=2
memory=4GB
swap=0
networkingMode=mirrored
localhostForwarding=false
```

**Hinweis**: Die `localhostForwarding=false` ist notwendig, da der mirrored Mode Konflikte verursachen kann.

### Verwaltete Services
- **Python**: 3.12.3 (system)
- **Package Manager**: `uv` (Astral)
- **Node.js**: v20.20.2 (via nvm)
- **Docker**: SurrealDB Container

## 🚀 Quick Start

### Services starten (3 Terminals)

**Terminal 1 - SurrealDB:**
```powershell
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make database"
```

**Terminal 2 - API Backend (Hot-Reload):**
```powershell
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && .venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 5055"
```

**Terminal 3 - Frontend (Hot-Reload):**
```powershell
wsl --exec bash -c "export NVM_DIR=/home/t11/.nvm && [ -s \$NVM_DIR/nvm.sh ] && . \$NVM_DIR/nvm.sh && nvm use 20 && cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend && npm run dev"
```

### Alternative: Startskripte verwenden

API starten:
```powershell
wsl --exec bash -c "/tmp/start_api.sh"
```

Frontend starten:
```powershell
wsl --exec bash -c "/tmp/start_frontend.sh"
```

## 🔍 Status prüfen

### Docker Containers
```powershell
wsl --exec bash -c "docker ps --filter 'name=open-notebook'"
```

### Laufende Prozesse
```powershell
wsl --exec bash -c "ps aux | grep -E 'uvicorn|next|node' | grep -v grep"
```

### Ports überprüfen
```powershell
wsl --exec bash -c "netstat -tlnp | grep -E '3000|5055|8000'"
```

## 🛑 Services stoppen

### Einzelne Services
```powershell
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && make stop-all"
```

### Alle WSL Prozesse beenden
```powershell
wsl --shutdown
```

## 📡 Zugriffs-URLs

| Service | URL | Beschreibung |
|---------|-----|--------------|
| Frontend | http://localhost:3000 | Next.js Dev Server |
| API | http://localhost:5055 | FastAPI Backend |
| API Docs | http://localhost:5055/docs | Swagger UI |
| Database | http://localhost:8000 | SurrealDB |

## 🔧 Troubleshooting

### WSL startet nicht
```powershell
# .wslconfig prüfen
Get-Content $env:USERPROFILE\.wslconfig

# WSL neu starten
wsl --shutdown
wsl
```

### Port bereits belegt
```powershell
# Port 5055 prüfen
netstat -ano | findstr :5055

# Prozess beenden
taskkill /PID <PID> /F
```

### Python venv nicht gefunden
```powershell
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && ls -la .venv/bin/"
```

### Node.js nicht gefunden
```powershell
wsl --exec bash -c "export NVM_DIR=/home/t11/.nvm && [ -s \$NVM_DIR/nvm.sh ] && . \$NVM_DIR/nvm.sh && nvm list"
```

## 📝 Startskripte

### `/tmp/start_api.sh`
```bash
#!/bin/bash
cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook
.venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 5055
```

### `/tmp/start_frontend.sh`
```bash
#!/bin/bash
export NVM_DIR=/home/t11/.nvm
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 20
cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend
npm run dev
```

## 🔄 Hot-Reload Verhalten

### API Backend
- **Framework**: FastAPI + uvicorn
- **Hot-Reload**: ✅ Automatisch bei Code-Änderungen
- **Konfiguration**: `--reload` Flag (standardmäßig aktiv)

### Frontend
- **Framework**: Next.js 16.2.6
- **Hot-Reload**: ✅ Automatisch bei Code-Änderungen
- **HMR**: Fast Refresh für React Komponenten

### Datenbank
- **SurrealDB**: Persistiert in `./surreal_data/`
- **Migrations**: Automatisch bei API-Start

## 📦 Abhängigkeiten

### Python (via uv)
```bash
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook && uv sync"
```

### Node.js (via npm)
```bash
wsl --exec bash -c "cd /mnt/c/Users/T11/SynologyDrive/LLM/open-notebook/frontend && npm install"
```

## 🐛 Bekannte Issues

### mirrored networking + localhostForwarding
- **Problem**: Konflikt zwischen `networkingMode=mirrored` und `localhostForwarding=true`
- **Lösung**: `localhostForwarding=false` in `.wslconfig`
- **Workaround**: Direkte Port-Mapping in Docker verwenden

### pageReporting Fehler
- **Problem**: `wsl: Unbekannter Schlüssel „wsl2.pageReporting"`
- **Lösung**: Ungültige Schlüssel aus `.wslconfig` entfernen

### guiApplications Fehler
- **Problem**: `wsl: Geschachtelte Virtualisierung wird nicht unterstützt`
- **Lösung**: `guiApplications` Schlüssel aus `.wslconfig` entfernen

## 📚 Weitere Ressourcen

- [WSL2 Dokumentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Desktop WSL2](https://docs.docker.com/desktop/wsl/)
- [Open Notebook Development Guide](./development-setup.md)
