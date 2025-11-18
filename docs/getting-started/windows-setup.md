# Windows Setup Guide

Complete guide for installing and running Open Notebook on Windows 10 and Windows 11, both natively and with WSL2.

## Table of Contents

1. [Windows Installation Methods](#windows-installation-methods)
2. [Prerequisites](#prerequisites)
3. [Native Windows Setup (Recommended)](#native-windows-setup-recommended)
4. [WSL2 Setup (Alternative)](#wsl2-setup-alternative)
5. [Development Setup on Windows](#development-setup-on-windows)
6. [Troubleshooting Windows Issues](#troubleshooting-windows-issues)

---

## Windows Installation Methods

Open Notebook can run on Windows in two ways:

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Native Windows + Docker Desktop** | Easy setup, full Windows integration, better performance | Requires Docker Desktop (free for personal use) | Most users, production use |
| **WSL2 + Docker** | Linux environment, familiar to Linux users | More complex setup, extra layer | Developers familiar with Linux |

**Recommendation**: For most Windows users, use the **Native Windows + Docker Desktop** method.

---

## Prerequisites

### System Requirements

- **Operating System**: Windows 10 (version 2004 or higher) or Windows 11
- **Hardware**:
  - 4GB RAM minimum (8GB+ recommended)
  - 10GB free disk space
  - 64-bit processor with virtualization support
- **Internet**: Stable connection for downloading Docker images and AI API access

### Required Software

#### For Native Windows Setup:

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Free for personal use
   - Includes Docker Compose

2. **PowerShell 5.1 or higher** (included with Windows 10/11)

3. **Git for Windows** (for development)
   - Download from: https://git-scm.com/download/win

#### For Development (Optional):

4. **Python 3.11+**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

5. **Node.js 18+** (for frontend development)
   - Download from: https://nodejs.org/

6. **uv** (Python package manager for development)
   - Install via PowerShell: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

---

## Native Windows Setup (Recommended)

### Step 1: Install Docker Desktop

1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Run the installer and follow the setup wizard
3. After installation, start Docker Desktop
4. Wait for Docker to fully start (you'll see "Docker Desktop is running" in the system tray)

**Important Settings:**
- In Docker Desktop → Settings → Resources:
  - **Memory**: Allocate at least 4GB (8GB recommended)
  - **CPUs**: Allocate at least 2 cores (4 recommended)

### Step 2: Download Open Notebook

#### Option A: Download Release (Easiest)

1. Create a folder for Open Notebook:
   ```cmd
   mkdir C:\open-notebook
   cd C:\open-notebook
   ```

2. Download the required files from GitHub:
   - `docker-compose.yml`
   - `.env.example`

3. Rename `.env.example` to `.env`:
   ```cmd
   copy .env.example .env
   ```

#### Option B: Clone Repository (For Development)

1. Open PowerShell or Command Prompt
2. Clone the repository:
   ```powershell
   git clone https://github.com/lfnovo/open-notebook.git
   cd open-notebook
   ```

3. Copy the environment template:
   ```powershell
   copy .env.example .env
   ```

### Step 3: Configure Environment

1. Open the `.env` file in your favorite text editor (Notepad, VS Code, etc.):
   ```powershell
   notepad .env
   ```

2. Add your API key(s). At minimum, you need one AI provider:
   ```env
   # Required: At least one AI provider
   OPENAI_API_KEY=sk-your-openai-key-here

   # Database Configuration (don't change these)
   SURREAL_URL=ws://localhost:8000/rpc
   SURREAL_USER=root
   SURREAL_PASSWORD=root
   SURREAL_NAMESPACE=open_notebook
   SURREAL_DATABASE=production

   # Optional: Password protection for public access
   # OPEN_NOTEBOOK_PASSWORD=your_secure_password_here
   ```

3. Save and close the file

### Step 4: Start Open Notebook

#### Using Quick Setup Script (Easiest):

If you cloned the repository:
```cmd
setup-windows.bat
```

This script will:
- Check if Docker is installed and running
- Create necessary directories
- Help you set up the `.env` file
- Provide next steps

#### Using Docker Compose:

```powershell
docker compose up -d
```

**What this does:**
- Downloads the Open Notebook Docker image
- Starts all required services
- Creates persistent storage for your data

### Step 5: Access Open Notebook

1. Wait about 30 seconds for all services to start
2. Open your web browser
3. Navigate to: http://localhost:8502

You should see the Open Notebook interface!

**Additional URLs:**
- **API Documentation**: http://localhost:5055/docs
- **Health Check**: http://localhost:5055/health

### Step 6: Verify Installation

1. Click "Create New Notebook"
2. Add a test source (text, URL, or file)
3. Try asking a question in the Chat tab

If everything works, you're all set! 🎉

---

## WSL2 Setup (Alternative)

For users who prefer Linux environment:

### Step 1: Install WSL2

1. Open PowerShell as Administrator:
   ```powershell
   wsl --install
   ```

2. Restart your computer when prompted

3. After restart, set up your Linux username and password

### Step 2: Install Docker Desktop with WSL2 Backend

1. Install Docker Desktop for Windows
2. In Docker Desktop → Settings → General:
   - Enable "Use the WSL 2 based engine"
3. In Docker Desktop → Settings → Resources → WSL Integration:
   - Enable integration with your WSL2 distro

### Step 3: Install Open Notebook in WSL2

1. Open your WSL2 terminal (Ubuntu, Debian, etc.)

2. Follow the standard Linux installation:
   ```bash
   git clone https://github.com/lfnovo/open-notebook.git
   cd open-notebook
   cp .env.example .env
   nano .env  # Add your API keys
   docker compose up -d
   ```

3. Access from Windows browser: http://localhost:8502

---

## Development Setup on Windows

For developers who want to run from source or contribute to Open Notebook:

### Prerequisites

1. Install all required software:
   - Docker Desktop
   - Git for Windows
   - Python 3.11+
   - Node.js 18+
   - uv package manager

### Setup Steps

1. **Clone the Repository**
   ```powershell
   git clone https://github.com/lfnovo/open-notebook.git
   cd open-notebook
   ```

2. **Install Python Dependencies**
   ```powershell
   # Install uv if not already installed
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Create virtual environment and install dependencies
   uv venv
   .\.venv\Scripts\activate
   uv sync
   ```

3. **Install Frontend Dependencies**
   ```powershell
   cd frontend
   npm install
   cd ..
   ```

4. **Configure Environment**
   ```powershell
   copy .env.example .env
   notepad .env  # Add your API keys
   ```

5. **Start Development Environment**

   Using PowerShell script (recommended):
   ```powershell
   .\scripts\dev.ps1 start-all
   ```

   Or start services individually:
   ```powershell
   # Terminal 1: Start database
   docker compose up -d surrealdb

   # Terminal 2: Start API
   uv run python api/main.py

   # Terminal 3: Start worker
   uv run python -m open_notebook.worker

   # Terminal 4: Start frontend
   cd frontend
   npm run dev
   ```

### PowerShell Development Script

The `scripts/dev.ps1` script provides Windows equivalents of Makefile commands:

```powershell
# Show all available commands
.\scripts\dev.ps1 help

# Start all services
.\scripts\dev.ps1 start-all

# Check service status
.\scripts\dev.ps1 status

# Stop all services
.\scripts\dev.ps1 stop-all

# Run linting
.\scripts\dev.ps1 lint

# Clean cache files
.\scripts\dev.ps1 clean-cache
```

### Development Workflow on Windows

1. **Making Changes**
   - Edit code in your preferred editor (VS Code, PyCharm, etc.)
   - Changes to Python code require API restart
   - Frontend changes hot-reload automatically

2. **Running Tests**
   ```powershell
   uv run pytest
   ```

3. **Code Formatting**
   ```powershell
   .\scripts\dev.ps1 ruff
   ```

4. **Type Checking**
   ```powershell
   .\scripts\dev.ps1 lint
   ```

---

## Troubleshooting Windows Issues

### Docker Desktop Issues

#### Docker not starting
- **Check virtualization**: Ensure virtualization is enabled in BIOS
- **Update Windows**: Ensure Windows is up to date
- **Reinstall Docker**: Sometimes a clean reinstall helps

#### "Docker is not running" error
1. Start Docker Desktop from Start Menu
2. Wait for Docker to fully start (check system tray icon)
3. Try the command again

#### WSL2 installation failed
```powershell
# Enable WSL feature
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine feature
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart computer
# Then set WSL2 as default
wsl --set-default-version 2
```

### Port Conflicts

#### Port 8502 or 5055 already in use

Find what's using the port:
```powershell
# Check what's using port 8502
netstat -ano | findstr :8502

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

Or modify Docker Compose to use different ports:
```yaml
ports:
  - "8503:8502"  # Use port 8503 instead
  - "5056:5055"  # Use port 5056 instead
```

### PowerShell Execution Policy

If you get "script execution is disabled" error:

```powershell
# Allow scripts to run (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run script with bypass
PowerShell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 start-all
```

### Python/uv Issues

#### uv not found
```powershell
# Install uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Add to PATH if needed (restart PowerShell after)
$env:Path += ";$env:USERPROFILE\.cargo\bin"
```

#### Python version issues
```powershell
# Install specific Python version with uv
uv python install 3.11

# Pin project to use Python 3.11
uv python pin 3.11
```

### File Permission Issues

If you get permission errors:

1. **Run as Administrator**: Right-click PowerShell/CMD → "Run as administrator"
2. **Check folder permissions**: Ensure you have write access to the project folder
3. **Disable antivirus temporarily**: Sometimes antivirus blocks file operations

### Docker Volume Issues

#### Data not persisting

Ensure volumes are correctly mapped in `docker-compose.yml`:
```yaml
volumes:
  - ./notebook_data:/app/data
  - ./surreal_data:/mydata
```

Check that these folders exist:
```powershell
# Create folders if they don't exist
mkdir notebook_data
mkdir surreal_data
```

### Network Issues

#### Cannot access localhost:8502

1. **Check Windows Firewall**: Ensure ports 8502 and 5055 are allowed
2. **Try 127.0.0.1**: Sometimes `http://127.0.0.1:8502` works when localhost doesn't
3. **Check Docker network**:
   ```powershell
   docker network ls
   docker network inspect open-notebook_default
   ```

#### API connection errors

Ensure both ports are exposed:
```yaml
ports:
  - "8502:8502"  # Frontend
  - "5055:5055"  # API - REQUIRED!
```

### Development Script Issues

#### Background jobs not stopping

```powershell
# Stop all PowerShell jobs
Get-Job | Stop-Job
Get-Job | Remove-Job

# Force kill processes
Get-Process *python* | Stop-Process -Force
Get-Process *node* | Stop-Process -Force
```

#### Can't see job output

```powershell
# View job output
Get-Job | Receive-Job -Keep

# View specific job
Receive-Job -Name "OpenNotebook-API" -Keep
```

---

## Windows-Specific Tips

### 1. Use PowerShell Instead of CMD

PowerShell has better scripting capabilities and is recommended for development.

### 2. Windows Terminal

Consider using Windows Terminal for better experience:
- Download from Microsoft Store
- Supports tabs, better fonts, and themes
- Integrates PowerShell, CMD, and WSL

### 3. VS Code on Windows

Best setup for development:
```powershell
# Install VS Code
winget install Microsoft.VisualStudioCode

# Recommended extensions:
# - Python
# - Pylance
# - Docker
# - PowerShell
```

### 4. Path Length Limitations

Windows has a 260-character path limit by default. To enable long paths:

1. Run as Administrator:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```

2. Or enable via Group Policy:
   - Run `gpedit.msc`
   - Navigate to: Local Computer Policy → Computer Configuration → Administrative Templates → System → Filesystem
   - Enable "Enable Win32 long paths"

### 5. Performance Tips

- **SSD Storage**: Use SSD for Docker volumes for better performance
- **Allocate Resources**: Give Docker Desktop enough RAM (8GB+) and CPU (4+ cores)
- **Exclude from Antivirus**: Add project folder to antivirus exclusions
- **Use native Docker volumes**: For better performance than bind mounts

---

## Next Steps

After successful installation:

1. **Read the User Guide**: Learn about Open Notebook features
2. **Configure AI Models**: Set up your preferred AI providers
3. **Create Your First Notebook**: Try the step-by-step tutorial
4. **Join the Community**: Discord server for help and discussions

### Useful Resources

- **Main Documentation**: [Getting Started Guide](./installation.md)
- **Docker Documentation**: https://docs.docker.com/desktop/windows/
- **WSL2 Documentation**: https://docs.microsoft.com/windows/wsl/
- **Discord Community**: https://discord.gg/37XJPXfz2w

---

**Need Help?**

- Ask on Discord: https://discord.gg/37XJPXfz2w
- Report issues: https://github.com/lfnovo/open-notebook/issues
- Check common issues: [Troubleshooting Guide](../troubleshooting/common-issues.md)

Welcome to Open Notebook on Windows! 🚀
