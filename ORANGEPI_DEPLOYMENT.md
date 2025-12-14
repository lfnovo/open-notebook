# Orange Pi Deployment Guide

## Prerequisites
- Orange Pi with Ubuntu/Armbian (ARM64)
- Docker and Docker Compose installed
- At least 4GB RAM (8GB recommended)
- 20GB+ free storage

## Installation Steps

### 1. Install Docker on Orange Pi
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Reboot
sudo reboot
```

### 2. Transfer Files to Orange Pi
```bash
# From your Windows PC, copy files:
scp -r d:\Development\open-notebook user@orangepi-ip:/home/user/

# Or use rsync:
rsync -avz d:/Development/open-notebook/ user@orangepi-ip:/home/user/open-notebook/
```

### 3. Configure for Orange Pi
```bash
# SSH into Orange Pi
ssh user@orangepi-ip

# Navigate to project
cd ~/open-notebook

# Use Orange Pi configuration
cp docker-compose.orangepi.yml docker-compose.yml
cp docker.orangepi.env docker.env

# Edit docker.env to set your Orange Pi's LAN IP (optional)
# nano docker.env
# Set: API_URL=http://192.168.1.XXX:5055 (replace XXX with your IP)
```

### 4. Start Services
```bash
# Pull ARM64 images
docker-compose pull

# Start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Access Application
- **From same network:** `http://orangepi-ip:8502`
- **Example:** `http://192.168.1.100:8502`

## Performance Optimization

### Use Lighter Models
The configuration already uses:
- Whisper: `tiny` model (fastest for ARM)
- Piper: `low` quality voice (faster processing)

### Ollama Model Recommendations
```bash
# SSH into Orange Pi
docker exec -it open-notebook-ollama-1 bash

# Install small, efficient models
ollama pull phi3:mini        # 2.3GB, fast
ollama pull gemma2:2b        # 1.6GB, very fast
ollama pull qwen2.5:1.5b     # 1GB, extremely fast

# Avoid large models like llama3:70b (too slow on Orange Pi)
```

### Limit Resources (if needed)
Add to `docker-compose.yml`:
```yaml
services:
  open_notebook_single:
    deploy:
      resources:
        limits:
          memory: 2G
  ollama:
    deploy:
      resources:
        limits:
          memory: 4G
```

## Network Options

### Option 1: LAN-Only (Current Config)
- No port forwarding needed
- Access only from local network
- Most secure, no internet exposure

### Option 2: Public HTTPS Access
1. Update DuckDNS to point to your public IP
2. Port forward 80/443 on router to Orange Pi
3. Uncomment Caddy in `docker-compose.yml`
4. Keep original `Caddyfile`

## Troubleshooting

### Check ARM64 Image Support
```bash
# If image doesn't support ARM64:
docker-compose pull  # Will show platform errors

# Solution: Build locally (slow on Orange Pi)
docker-compose build
```

### Out of Memory Issues
```bash
# Check memory usage
free -h
docker stats

# Stop heavy services temporarily
docker stop open-notebook-ollama-1
```

### Slow Performance
- Use smaller Whisper model: `base` → `tiny`
- Use smaller Ollama models
- Reduce WORKER_CONCURRENCY in docker.env
- Consider disabling services you don't use

## Architecture Differences

| Component | Windows PC | Orange Pi |
|-----------|-----------|-----------|
| CPU | x86_64 | ARM64 |
| GPU | NVIDIA (CUDA) | None (CPU only) |
| Ports | Localhost only | LAN accessible |
| HTTPS | Caddy + Let's Encrypt | Optional (LAN only) |
| Performance | Fast with GPU | Slower, CPU-bound |

## Security Notes

For LAN-only deployment:
- ✓ No public exposure
- ✓ Password still required
- ✓ Only accessible from your network
- Consider: MAC filtering on router
- Consider: VPN for remote access (WireGuard/Tailscale)

For public deployment:
- Add firewall rules: `sudo ufw allow 80,443/tcp`
- Keep rate limiting in Caddyfile
- Monitor logs: `docker-compose logs -f caddy`
- Regular updates: `docker-compose pull && docker-compose up -d`
