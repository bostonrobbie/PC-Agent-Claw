---
description: How to restart OpenClaw gateway with PM2
---

# Restart OpenClaw Gateway with PM2

## Prerequisites
PM2 must be installed and the gateway must already be running via PM2.

## Quick Commands

// turbo-all
### Check Status
```powershell
pm2 status
```

### Restart Gateway
```powershell
pm2 restart openclaw-gateway
```

### View Logs
```powershell
pm2 logs openclaw-gateway --lines 50
```

### Stop Gateway
```powershell
pm2 stop openclaw-gateway
```

### Start Gateway (if stopped)
```powershell
cd C:\Users\User\Documents\AI\OpenClaw
pm2 start ecosystem.config.cjs
```

## First-Time Setup
If PM2 is not yet managing the gateway:

1. Stop any running gateway:
   ```powershell
   node C:\Users\User\Documents\AI\OpenClaw\openclaw.mjs gateway stop
   taskkill /F /IM node.exe  # If needed
   ```

2. Start with PM2:
   ```powershell
   cd C:\Users\User\Documents\AI\OpenClaw
   pm2 start ecosystem.config.js
   pm2 save
   ```

3. Run admin setup (as Administrator):
   ```powershell
   powershell -ExecutionPolicy Bypass -File "C:\Users\User\Documents\AI\OpenClaw\scripts\setup-24-7-resilience.ps1"
   ```
