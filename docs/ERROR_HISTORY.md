# OpenClaw/Telegram Error History

This document tracks recurring errors to inform future resilience improvements.

---

## 2026-02-02 @ 17:15 EST: Telegram Polling Freeze

### Root Cause
- Telegram long-polling connection silently froze (no updates processed)
- Internal watchdog detected 6 minutes of inactivity and called `process.exit(1)`
- Auto-restart script (`gateway-autostart.cmd`) didn't restart in time (timing issue)

### Resolution
- Manually restarted gateway
- Gateway now running and connected

### Log Evidence
```
WATCHDOG: No Telegram activity for 6 minutes. Self-terminating for restart.
```

---

## 2026-02-02 @ 19:54 EST: Mid-Task Disconnections

### Root Cause
- Watchdog timeout was 5 minutes, but long CLI tasks (10+ min) don't update activity
- Watchdog falsely detected "no activity" during legitimate long-running tasks
- This caused repeated self-terminations during complex agent work

### Fix Applied
- **Final Update (20:30 EST):** Completely **DISABLED** the internal watchdog.
- **Reason:** For all-day agent operation, we cannot risk the watchdog killing the process during very long tasks.
- **Protection:** We now rely entirely on the external `gateway-autostart.cmd` script. If the gateway crashes (process dies), the script will restart it. If it hangs, we will have to restart manually, but this is better than it killing itself while working.

```typescript
// Internal Watchdog: DISABLED
// const watchdogInterval = setInterval(() => { ... }, 60_000);
```

---

## 2026-02-02: Zombie Gateway + Watchdog Loop

### Root Cause
1. **Gateway Process Hang**: Gateway (PID 25356) became unresponsive ("zombie") at ~13:36 UTC while keeping port 18789 open
2. **Broken Watchdog**: The `watchdog.ps1` script:
   - Checked `localhost:18789` but gateway was bound to `100.123.64.78:18789`
   - `/health` endpoint returns HTML (UI), not JSON status
   - This caused false-negative health checks, triggering restart attempts every 90s
3. **Restart Conflict**: Each restart attempt failed with `Port 18789 already in use` because the zombie still held the port

### Symptoms
- Telegram says "not connected"
- Logs show repeated `Gateway failed to start: gateway already running (pid XXXXX); lock timeout after 5000ms`
- ~100+ identical error messages in log

### Resolution
- Force killed zombie process (PID 16416 at that point)
- Restarted gateway cleanly via `npx openclaw gateway`
- Stopped the broken watchdog processes

### Improvements Needed
- [ ] Fix watchdog to use correct IP (`100.123.64.78` or check all interfaces)
- [ ] Add a proper `/api/health` JSON endpoint to OpenClaw that returns `{"status":"ok"}`
- [ ] Consider using PM2's built-in health monitoring instead of custom watchdog

---

## 2026-02-01: Silent Process Freeze

### Root Cause
- Gateway process (PID 19568) froze silently at ~22:03 EST
- No logs produced for ~1 hour
- Process still holding port but not responding to requests

### Symptoms
- Telegram messages not received
- Gateway CLI reported "not reachable"

### Resolution
- Manual restart via `gateway.cmd` detected issue and started new process
- New process (PID 22648) immediately reconnected to Telegram

### Improvements Needed
- [ ] Implement internal heartbeat/watchdog within gateway code
- [ ] Self-terminate after N seconds of failed Telegram polls

---

## Error Categories

| Category | Count | Last Seen | Status |
|----------|-------|-----------|--------|
| Zombie Process | 2 | 2026-02-02 | Recurring |
| Port Conflict | 2 | 2026-02-02 | Symptom of above |
| Watchdog False Positive | 1 | 2026-02-02 | Fixed (stopped watchdog) |
| CLI Failed | 1 | 2026-02-02 | Transient |
| Typing Timeout (10m) | 1 | 2026-02-02 | Expected behavior |
