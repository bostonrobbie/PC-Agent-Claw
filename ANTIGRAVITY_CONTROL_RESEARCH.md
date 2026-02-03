# Antigravity Control via Telegram - Research Findings

**Date:** 2026-02-01, 3:15 PM
**Status:** RESEARCHING - Need Antigravity's Help

---

## What You Asked For

You want the Telegram bot to control **Antigravity itself** (the application), not run a separate Claude instance.

**Goal:** ONE AI (Antigravity/Gemini) accessible via Telegram with full terminal/tool capabilities.

---

## What I've Discovered

### Antigravity's Architecture

**Application Type:** VS Code fork (Electron-based)
**AI Engine:** Google Gemini via language server
**Installation:** `C:\Users\User\AppData\Local\Programs\Antigravity\`

**Active Services:**
- **HTTP API:** `http://127.0.0.1:49811` (PID 14564)
- **HTTPS API:** `https://127.0.0.1:49810` (PID 14564)
- **Extension Server:** `http://127.0.0.1:49791` (PID 18412)

### Available Control Methods

#### 1. **VSCode Command API**
Antigravity exposes commands via VSCode API:
- `antigravity.triggerAgent` - Start agent conversation
- `antigravity.prioritized.chat.open` - Open chat
- `antigravity.prioritized.command.open` - Command mode
- `antigravity.generateCommitMessage` - Git commits
- `antigravity.restartLanguageServer` - Restart AI

#### 2. **CLI Interface**
```
C:\Users\User\AppData\Local\Programs\Antigravity\bin\antigravity.cmd
```
Can open files, manage extensions, but **cannot send chat messages directly**.

#### 3. **Language Server HTTP/HTTPS**
- Running on localhost ports 49810/49811
- Tested: Servers respond but return 404 (need correct API paths)
- Likely requires authentication
- Need to reverse-engineer API endpoints

#### 4. **Extension Development**
Could build a VSCode extension that:
- Listens for external messages (HTTP server)
- Forwards to Antigravity's chat interface
- Returns responses

---

## The Challenge

**Antigravity's AI is deeply integrated into the application:**
- Chat interface is part of the Electron UI
- Communication happens via language server (Gemini backend)
- No simple "send message, get response" API exposed externally

**Not like Claude CLI where we can just run:**
```bash
node cli.js -p "message"  # Works for Claude
```

---

## Possible Solutions

### Option A: Build a Bridge Extension ⭐ **RECOMMENDED**

**How it works:**
1. Create a simple VSCode extension for Antigravity
2. Extension runs HTTP server (e.g., `http://localhost:8080`)
3. Telegram bot sends messages to this server
4. Extension forwards to Antigravity's chat interface via VSCode API
5. Extension captures responses and returns them

**Pros:**
- Clean, official approach
- Uses VSCode's built-in APIs
- Stable and maintainable

**Cons:**
- Requires extension development
- Need to package and install extension
- More complex setup

**Implementation:**
- I can write the extension code
- Antigravity can help test/refine it
- Install in Antigravity's extension directory

### Option B: Reverse-Engineer Language Server API

**How it works:**
1. Capture network traffic to find API endpoints
2. Extract authentication mechanism
3. Build direct HTTP client to language server

**Pros:**
- No extension needed
- Direct communication
- Fast

**Cons:**
- Fragile (API might change)
- Authentication may be complex
- Unofficial/unsupported approach

**Status:**
- Found servers at ports 49810/49811
- Need to discover endpoint paths
- Need authentication details

### Option C: UI Automation (Hacky)

**How it works:**
1. Use Windows automation (e.g., `pywinauto`)
2. Programmatically type into Antigravity's chat
3. Scrape responses from UI

**Pros:**
- No code changes to Antigravity
- Works immediately

**Cons:**
- Extremely fragile
- Requires Antigravity window to be visible
- Slow and unreliable
- Can break with UI updates

**Not recommended.**

### Option D: Ask Antigravity to Build It

**How it works:**
1. Antigravity (the AI) has access to its own codebase
2. Ask Antigravity to create the bridge extension
3. Antigravity knows its internal APIs better than I do

**Pros:**
- Antigravity knows the internals
- Can build optimal solution
- AI collaboration!

**Status:**
- Created `REQUEST_TO_ANTIGRAVITY.txt` with details
- Waiting for Antigravity to investigate

---

## My Recommendation

**Best approach: Option A (Bridge Extension) with Option D (Let Antigravity Build It)**

**Steps:**
1. **You paste `REQUEST_TO_ANTIGRAVITY.txt` into Antigravity's chat**
2. **Ask Antigravity to investigate and build a simple extension**
3. **Extension should:**
   - Run HTTP server on localhost:8080
   - Accept POST requests with `{message: "text"}`
   - Forward to Antigravity chat via `vscode.commands.executeCommand`
   - Return response as JSON
4. **Modify Telegram bot to call this HTTP endpoint instead of Claude CLI**
5. **Done!**

---

## What I Need From You

**Option 1: Work with Antigravity**
- Open Antigravity
- Paste `REQUEST_TO_ANTIGRAVITY.txt` into chat
- Ask Antigravity to build the bridge extension
- Antigravity has full access to VS Code APIs and can do this

**Option 2: Let me try Option B**
- Give me permission to reverse-engineer the language server API
- I'll use network sniffing to find endpoints
- Riskier but might work without extension development

**Option 3: Build extension myself**
- I can write the extension code
- You'll need to install it in Antigravity
- Less optimal than Antigravity building it (it knows its APIs better)

---

## Current Status

✅ **Researched Antigravity architecture**
✅ **Found communication endpoints**
✅ **Identified possible approaches**
✅ **Created message for Antigravity**

⏳ **Waiting for your decision on approach**

---

## Files Created

- `REQUEST_TO_ANTIGRAVITY.txt` - Message explaining the problem to Antigravity
- `ANTIGRAVITY_CONTROL_RESEARCH.md` - This file

---

## Bottom Line

**Can it be done?** YES

**Best way?** Build a simple VSCode extension that acts as a bridge

**Who should build it?** Antigravity itself (has internal knowledge) OR me (I can write the extension)

**Recommendation:** Ask Antigravity to investigate and advise on the best approach, since it has full access to its own codebase and APIs.

---

Generated by Claude AI Agent (OpenClaw)
Location: C:\Users\User\.openclaw\workspace
