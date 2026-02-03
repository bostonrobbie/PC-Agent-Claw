# Remote GPU Access Guide - RTX 5070 PC

## Overview

You can access the RTX 5070 PC's GPU for LLM tasks remotely using several methods. This guide covers the most practical approaches.

---

## Method 1: SSH Tunnel (RECOMMENDED - Most Secure)

This creates an encrypted tunnel from Viper PC to your RTX 5070 PC, allowing you to use Ollama remotely as if it were local.

### Prerequisites on RTX 5070 PC:
1. Ollama installed and running
2. SSH server enabled (OpenSSH)
3. Firewall allows SSH (port 22)
4. Know the PC's IP address or hostname

### Setup on RTX 5070 PC:

**Step 1: Install Ollama (if not already)**
```bash
# Download from https://ollama.com/download
# Or use winget
winget install Ollama.Ollama
```

**Step 2: Enable OpenSSH Server**
```powershell
# Run as Administrator
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Allow SSH through firewall
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

**Step 3: Get IP Address**
```bash
ipconfig | findstr IPv4
# Note the IP address (e.g., 192.168.1.100)
```

### Connect from Viper PC:

**Create SSH Tunnel:**
```bash
ssh -N -L 11434:localhost:11434 USERNAME@RTX5070_IP_ADDRESS
# Replace USERNAME with your Windows username on RTX 5070 PC
# Replace RTX5070_IP_ADDRESS with actual IP (e.g., 192.168.1.100)

# Example:
# ssh -N -L 11434:localhost:11434 User@192.168.1.100
```

**Use Ollama Through Tunnel:**
```bash
# In a new terminal while SSH tunnel is running:
ollama run qwen2.5:7b "Hello from remote GPU!"
```

The RTX 5070's GPU will process the request!

---

## Method 2: Ollama HTTP Server (Less Secure, Easier)

Expose Ollama's API over your local network.

### Setup on RTX 5070 PC:

**Step 1: Configure Ollama to Listen on Network**
```powershell
# Set environment variable
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')

# Restart Ollama service
Stop-Process -Name ollama -Force
Start-Process "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve"
```

**Step 2: Open Firewall**
```powershell
New-NetFirewallRule -Name Ollama -DisplayName 'Ollama API' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 11434
```

### Connect from Viper PC:

```bash
# Set environment variable to point to RTX 5070
export OLLAMA_HOST=http://RTX5070_IP:11434

# Use Ollama normally
ollama run qwen2.5:7b "Hello from remote GPU!"
```

**⚠️ Security Warning:** This method has NO authentication. Only use on trusted networks!

---

## Method 3: Tailscale VPN (RECOMMENDED for Internet Access)

If you want to access the RTX 5070 PC from anywhere (not just local network), use Tailscale.

### Setup:

**On Both PCs:**
1. Install Tailscale: https://tailscale.com/download
2. Sign in with same account
3. Both PCs will get Tailscale IPs (e.g., 100.x.x.x)

**On RTX 5070 PC:**
```powershell
# Configure Ollama to listen on Tailscale interface
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')
```

**From Viper PC:**
```bash
# Use Tailscale IP
export OLLAMA_HOST=http://100.x.x.x:11434
ollama run qwen2.5:7b "Hello from anywhere!"
```

Tailscale provides encrypted WireGuard VPN - secure and works from anywhere!

---

## Method 4: Remote Desktop + Local Use

Simplest but least automated.

1. Use Windows Remote Desktop to connect to RTX 5070 PC
2. Run Ollama commands directly on that machine
3. Copy results back

**Not ideal for automation but works for quick tasks.**

---

## Comparison Table

| Method | Security | Ease of Setup | Use Case |
|--------|----------|---------------|----------|
| SSH Tunnel | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Medium | Local network, automated tasks |
| HTTP Server | ⭐ Poor | ⭐⭐⭐⭐⭐ Easy | Trusted local network only |
| Tailscale VPN | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Easy | Internet access, anywhere |
| Remote Desktop | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Easy | Manual tasks, quick access |

---

## Recommended Approach

**For You:**

1. **Tailscale VPN** (if you need access from anywhere)
   - Install on both PCs
   - Most flexible and secure
   - Works over internet

2. **SSH Tunnel** (if only local network)
   - More technical but very secure
   - Good for automation

---

## Python Helper Script

I'll create a helper script that automatically uses the RTX 5070 when available and falls back to Viper PC's RTX 3060 if not.

```python
# auto_gpu_selector.py
import os
import requests

def get_best_gpu():
    """Automatically select best available GPU"""

    # Try RTX 5070 first (via Tailscale or SSH tunnel)
    rtx_5070_host = "http://100.x.x.x:11434"  # Update with actual Tailscale IP

    try:
        response = requests.get(f"{rtx_5070_host}/api/tags", timeout=2)
        if response.status_code == 200:
            os.environ['OLLAMA_HOST'] = rtx_5070_host
            return "RTX 5070 (Remote)"
    except:
        pass

    # Fallback to local RTX 3060
    os.environ['OLLAMA_HOST'] = "http://localhost:11434"
    return "RTX 3060 (Local)"

# Usage
gpu = get_best_gpu()
print(f"Using: {gpu}")
```

---

## Next Steps

1. **Check if RTX 5070 PC is on same network** as Viper PC
2. **Get RTX 5070 PC's IP address**: Run `ipconfig` on that machine
3. **Test basic connectivity**: `ping RTX5070_IP` from Viper PC
4. **Choose method** based on your needs
5. **Set up remote access** following guide above

Let me know:
- Are both PCs on the same network?
- Do you have admin access to RTX 5070 PC?
- Do you need access from outside your home/office?

I can help set up whichever method works best for your situation!

---

## Sources

- [Access remote Ollama through SSH tunnel - 4sysops](https://4sysops.com/archives/access-remote-ollama-ai-models-through-an-ssh-tunnel/)
- [Connecting to Remote Ollama Servers with SSH Tunneling](https://yhren.github.io/posts/ai/llm/ollama/connecting_to_remote_ollama_servers_with_ssh_tunneling/)
- [Remote HTTP access to Ollama - 4sysops](https://4sysops.com/archives/remote-http-access-to-self-hosted-ollama-ai-models/)
- [Ollama Network Exposure Security Guide](https://markaicode.com/ollama-network-exposure-secure-remote-access-guide/)
