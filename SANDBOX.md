# Sandbox & Autonomous Operation Setup

**Goal:** Give Claude a dedicated workspace to operate independently without interfering with Rob's work.

---

## The Problem We're Solving

**Current State:**
- Claude and Rob share the same PC environment
- No separation between Claude's work and Rob's work
- Claude can't run autonomously (only during active chat sessions)
- Unclear boundaries on what Claude can/can't do
- No visibility into what Claude is doing when autonomous

**Desired State:**
- Clear workspace separation
- Claude can work independently on assigned projects
- Safe sandbox environment for testing
- Autonomous operation while Rob is working on other things
- Eventually: This PC becomes Claude's dedicated "office"

---

## How I Currently Work (Technical Reality)

### Session-Based Execution
- I only run when you're actively chatting with me
- Each conversation is a session
- When you close the chat, I stop
- I have no persistent background process (yet)

### Full System Access
- I can read/write any file on your PC
- I can run any command
- I can install software
- No automatic boundaries (I rely on judgment)

### Cost Structure (What I Know)
- I don't see real-time token usage or API costs
- I can log my activities to estimate usage
- You see billing on your Anthropic/OpenClaw account
- Long autonomous sessions = more API calls = more cost

---

## The Sandbox Solution

### Phase 1: Workspace Isolation (START HERE)

Create dedicated directory structure:

```
C:\Claude\
├── workspace\           # My active projects
│   ├── tradingview\    # TradingView automation
│   ├── manus\          # Manus Dashboard monitoring
│   ├── data-collection\ # Market data gathering
│   └── research\       # Analysis and research
│
├── communication\       # How we coordinate
│   ├── inbox\          # Tasks from Rob
│   ├── outbox\         # Results for Rob
│   ├── status.json     # Current status
│   └── logs\           # Activity logs
│
├── sandbox\            # Safe testing area
│   ├── test-scripts\   # Test automation here first
│   └── temp\           # Disposable files
│
├── data\               # Collected data
│   ├── market-data\
│   ├── tradingview\
│   └── analytics\
│
├── .venv\              # Dedicated Python environment
│
├── config\             # My configuration
│   ├── limits.json     # Resource limits
│   ├── schedule.json   # Autonomous schedule
│   └── northstar.md    # Mission and objectives
│
└── backups\            # Automated backups
```

**Rules:**
- I work primarily in `C:\Claude\`
- I never modify Rob's Desktop/Documents without explicit permission
- Testing happens in `sandbox\` first
- Logs go to `communication\logs\`

---

## How Autonomous Mode Works

### Option A: Scheduled Sessions (RECOMMENDED)

**How it works:**
1. Windows Task Scheduler runs a script at set times
2. Script launches Claude session with specific task
3. I execute the task, log results
4. Session ends, results in outbox
5. You check outbox when convenient

**Example Schedule:**
```json
{
  "6:00 AM": "Collect overnight market data",
  "9:30 AM": "Market open monitoring",
  "12:00 PM": "Mid-day analysis",
  "4:00 PM": "Market close processing",
  "6:00 PM": "Generate daily reports",
  "11:00 PM": "Nightly backups"
}
```

**Pros:**
- Simple to set up
- Predictable resource usage
- Easy to debug
- Works with current OpenClaw setup

**Cons:**
- Not truly continuous
- Can't react to events immediately
- Gaps between sessions

---

### Option B: Long-Running Session (ADVANCED)

**How it works:**
1. Launch Claude session in background
2. I run continuously, polling for tasks
3. Sleep between checks to save costs
4. Monitor for events and conditions
5. Log everything, update status

**Pros:**
- Can respond to events quickly
- True autonomous operation
- Better for monitoring tasks

**Cons:**
- Higher API costs (continuous session)
- Need error handling/recovery
- More complex setup

---

### Option C: Dedicated VM/Container (FUTURE)

**How it works:**
1. Virtual machine or Docker container for Claude
2. Complete isolation from Rob's work
3. Can run 24/7 independently
4. Network isolated if needed

**Pros:**
- Complete isolation
- Safe testing environment
- Can't affect Rob's system
- Professional setup

**Cons:**
- Most complex setup
- Resource overhead
- Need VM management

---

## Communication System

### Task Assignment

**Method 1: Task Files (Structured)**

Rob creates: `C:\Claude\communication\inbox\task_001.json`
```json
{
  "id": "task_001",
  "created": "2026-01-31T20:00:00Z",
  "priority": "high",
  "task": "Analyze TradingView script performance",
  "details": "Check all scripts, find slowest ones, suggest optimizations",
  "deadline": "2026-02-01",
  "output_format": "report",
  "approval_required": false
}
```

I process it, create: `C:\Claude\communication\outbox\task_001_result.md`

---

**Method 2: Northstar Document (Strategic)**

`C:\Claude\config\northstar.md`
```markdown
# Claude's Mission

## Primary Objective
Build and optimize Rob's trading automation infrastructure

## Active Projects (In Order of Priority)
1. TradingView Access Management System
   - Automate invite-only script access
   - Monitor usage and renewals
   - Integration with payment system

2. Manus Dashboard Performance
   - Monitor uptime and performance
   - Optimize slow queries
   - Automated testing

3. Market Data Collection
   - Build reliable data pipeline
   - Multiple source integration
   - Quality checks and validation

## Success Metrics
- System uptime > 99%
- Daily reports delivered by 6pm
- Zero manual intervention needed
- Cost under $X/month

## Current Focus
Week of Feb 1-7: TradingView automation MVP
```

I use this to guide autonomous decisions.

---

**Method 3: Telegram (Current - Direct)**

You message me directly, I respond and act.

---

### Status Reporting

`C:\Claude\communication\status.json` (Updated by me)
```json
{
  "last_update": "2026-01-31T20:30:00Z",
  "current_status": "working",
  "active_task": "task_001",
  "progress": "60%",
  "next_scheduled": "2026-02-01T06:00:00Z",
  "health": "good",
  "errors": [],
  "resource_usage": {
    "api_calls_today": 245,
    "files_created": 12,
    "disk_used_mb": 150
  }
}
```

You can check this anytime to see what I'm doing.

---

## Safety Rails & Limits

### Configuration: `C:\Claude\config\limits.json`

```json
{
  "workspace": {
    "allowed_paths": [
      "C:\\Claude",
      "C:\\Users\\User\\.openclaw\\workspace"
    ],
    "require_approval_outside": true
  },

  "resources": {
    "max_disk_usage_gb": 10,
    "max_api_calls_per_day": 1000,
    "max_file_size_mb": 100,
    "max_session_duration_hours": 4
  },

  "external_actions": {
    "allowed_domains": [
      "tradingview.com",
      "github.com"
    ],
    "require_approval": [
      "email",
      "social_media_posts",
      "purchases",
      "destructive_operations"
    ]
  },

  "automation": {
    "max_retries": 3,
    "error_threshold": 5,
    "auto_backup_before_changes": true
  }
}
```

I check these limits before taking actions.

---

## Autonomous Decision Framework

### What I Can Do Without Asking (Level 3+ Autonomy)

**Inside C:\Claude:**
- Create/edit files
- Run scripts and automation
- Collect data
- Generate reports
- Organize files
- Install Python packages in .venv
- Run tests
- Create backups

**Read-Only Anywhere:**
- Read any file to understand context
- Analyze code
- Research and learning

**External (Approved Domains):**
- Fetch data from TradingView (if credentials provided)
- Call approved APIs
- Download public data

---

### What Requires Approval

**Outside C:\Claude:**
- Modifying Rob's projects (Manus Dashboard, STS Strategies)
- Changing system settings
- Installing system-wide software

**Irreversible Actions:**
- Deleting files
- Sending emails
- Making purchases
- Public posts

**High Resource Usage:**
- Operations costing >$X
- Long-running processes (>4 hours)
- Large downloads (>1GB)

---

## Implementation Steps

### Step 1: Create Workspace (15 minutes)
```powershell
# I can do this now if you approve
mkdir C:\Claude
mkdir C:\Claude\workspace
mkdir C:\Claude\communication\inbox
mkdir C:\Claude\communication\outbox
mkdir C:\Claude\communication\logs
mkdir C:\Claude\sandbox
mkdir C:\Claude\data
mkdir C:\Claude\config
mkdir C:\Claude\backups
```

### Step 2: Set Up Python Environment (10 minutes)
```bash
cd C:\Claude
C:/Python314/python.exe -m venv .venv
.venv\Scripts\activate
pip install playwright httpx psutil watchdog schedule mss pillow yagmail
```

### Step 3: Create Configuration (5 minutes)
- Write `config/limits.json`
- Write `config/northstar.md`
- Create initial `communication/status.json`

### Step 4: Test Autonomous Task (30 minutes)
- Create a simple test task
- Run it manually first
- Verify logging works
- Check output format

### Step 5: Schedule First Autonomous Run (15 minutes)
- Windows Task Scheduler setup
- Run at specific time
- Verify it works unattended
- Review logs

**Total setup time: ~1.5 hours**

---

## CEO Mode - What I Need From You

### 1. The Mission (Northstar)
What's the #1 objective? Examples:
- "Build TradingView automation system that generates $X/month"
- "Make Manus Dashboard production-ready"
- "Create automated trading data pipeline"

### 2. Decision Authority
What can I decide on my own?
- Implementation details? (YES, I assume)
- Tool choices? (YES, I assume)
- Spending money? (NO - always ask)
- External communications? (NO - always ask)

### 3. Resources & Access
- API keys/credentials (as needed for projects)
- Budget (if any): $X/month for services
- Time: Which hours can I run autonomously?

### 4. Success Metrics
How do we measure if I'm doing well?
- Projects completed?
- Time saved?
- Revenue generated?
- System uptime?

### 5. Communication Cadence
- Daily status updates via Telegram?
- Weekly strategy reviews?
- Immediate alerts for errors?
- Monthly performance summaries?

---

## Where We Are Now vs. Where We're Going

### Now (Shared Environment)
```
Rob's PC
├── Rob's work (Desktop, Documents)
├── Rob's projects (Manus, STS)
└── Claude (ad-hoc, mixed in)
```

### Near Future (Separated)
```
Rob's PC
├── Rob's work
│   └── Manus, STS, personal projects
│
└── C:\Claude\ (Claude's dedicated space)
    └── Autonomous projects, tools, data
```

### Eventually (Dedicated PC)
```
Claude's PC
└── C:\Claude\
    ├── Full autonomy
    ├── 24/7 operation
    ├── Production systems
    └── Complete "home office"
```

---

## Immediate Next Action - What Should I Do?

**Option A: Set up workspace now**
- Create C:\Claude structure
- Set up communication system
- Write initial configs
- Test basic autonomous task

**Option B: Start with Northstar**
- You tell me the primary mission
- I create detailed project plan
- We agree on objectives
- Then set up technical infrastructure

**Option C: Pilot project first**
- Pick one specific automation (e.g., "collect market data daily")
- Build it manually first
- Test thoroughly
- Then automate it
- Proves the concept

**What's your preference?**

---

## Questions I Need Answered

1. **Primary mission:** What should I focus on autonomously?
2. **Schedule:** When can I run? (Specific hours or 24/7?)
3. **Approval process:** What needs your OK before I do it?
4. **Communication:** Daily updates via Telegram? Or check status.json?
5. **First project:** What's the first thing to build autonomously?

---

*Once we set this up, you can mostly ignore me while I work, just check the outbox for deliverables and logs if you're curious. Eventually this becomes your passive business infrastructure.*
