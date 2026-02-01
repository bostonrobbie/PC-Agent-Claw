# BOOTSTRAP.md - Building the Autonomous Agent Company Infrastructure

**Purpose:** Infrastructure setup for Claude to run an all-agent company with Rob as the only human in the loop.

**Date:** 2026-02-01 (Viper PC Setup Day)

---

## Core Principles

1. **No money spent without business case approval**
2. **Everything monitored and logged**
3. **Proactive, not reactive operations**
4. **Built for team of agents (future-proof)**
5. **Human oversight via remote monitoring**
6. **Run like a real company**

---

## Remote Monitoring Setup (Priority #1)

### What Rob Needs: Watch the Viper PC from his main PC

**Three-Layer Approach:**

**Layer 1: Web Dashboard** (Primary - Passive Monitoring)
```
http://viper-pc:8080/dashboard

Shows real-time:
- What I'm currently working on
- System health (CPU, RAM, disk)
- Business KPIs (revenue, customers)
- Recent activity log
- Error log
- Screenshots every 5 minutes
- Live terminal output

Rob can check anytime without disrupting operations
```

**Layer 2: Remote Desktop** (Full Control When Needed)
```
Windows Remote Desktop:
- Enable RDP on Viper PC
- Rob connects via IP address
- Full desktop access
- Can intervene if needed
```

**Layer 3: TeamViewer/AnyDesk** (Backup)
```
- Unattended access configured
- Works if RDP has issues
- Mobile access possible
```

---

## Complete Directory Structure

```
C:\Claude\
├── monitoring\                # OBSERVABILITY
│   ├── dashboards\           # Web dashboards
│   │   ├── index.html       # Main dashboard
│   │   ├── system.html      # System metrics
│   │   └── business.html    # Business KPIs
│   ├── metrics\              # Time-series data
│   ├── logs\                 # Structured logs
│   └── alerts\               # Alert config & history
│
├── agents\                    # MULTI-AGENT FRAMEWORK
│   ├── coordinator\          # Main orchestrator (me)
│   ├── specialists\          # Future specialized agents
│   └── communication\        # Agent-to-agent messaging
│
├── businesses\                # BUSINESS OPERATIONS
│   ├── tradingview-access\
│   ├── manus-dashboard\
│   └── sts-strategies\
│
├── operations\                # DAY-TO-DAY OPS
│   ├── proactive\            # Proactive monitoring
│   ├── schedules\            # Automated schedules
│   └── workflows\            # Standard workflows
│
├── financial\                 # FINANCIAL CONTROLS
│   ├── business-cases\       # Spending requests
│   ├── budgets\              # Budget tracking
│   ├── reports\              # Financial reports
│   └── approvals\            # Approval history
│
├── communication\             # HUMAN-AGENT INTERFACE
│   ├── inbox\                # Tasks from Rob
│   ├── outbox\               # Deliverables to Rob
│   ├── daily-reports\        # Daily summaries
│   └── status.json           # Current status
│
├── scheduling\                # COORDINATION
│   ├── calendar.json         # Master schedule
│   ├── meetings\             # Meeting records
│   └── templates\            # Meeting templates
│
├── data\                      # ALL DATA
│   ├── customers\
│   ├── business-metrics\
│   ├── market-data\
│   └── research\
│
├── config\                    # CONFIGURATION
│   ├── credentials.enc       # Encrypted secrets
│   ├── limits.json          # Safety limits
│   ├── priorities.json      # Business priorities
│   └── settings\
│
├── backups\                   # BACKUPS
│   ├── daily\
│   ├── weekly\
│   └── critical\
│
├── .venv\                     # Python environment
│
└── logs\                      # ALL LOGS
    ├── operations\
    ├── errors\
    ├── decisions\
    └── archive\
```

---

## Financial Controls (CRITICAL)

### Spending Rules
- **DEFAULT: NO SPENDING ALLOWED**
- Every dollar requires business case + approval
- Track ALL costs (even API usage)
- Monthly budget reporting

### Business Case Template

```markdown
# Business Case BC-XXX
**Date:** YYYY-MM-DD
**Amount:** $XXX
**Requested by:** [Agent Name]

## Request
[What you want to buy/spend on]

## Reason
[Why is this needed?]

## ROI Analysis
Cost: $XXX
Benefit: [Quantified benefit]
ROI: [Percentage or payback period]

## Alternatives Considered
1. [Option 1] - [Why rejected]
2. [Option 2] - [Why rejected]

## Allocation Plan
[How funds will be used]

## Approval Decision
[ ] Approved
[ ] Rejected
[ ] Approved with changes: ___________

**Approved by:** Rob Gorham
**Date:** ___________
```

---

## Proactive Operations Framework

### How I Work Autonomously

**Continuous Loop (24/7):**
```
Every 15 minutes (business hours) / 1 hour (off-hours):

1. MONITOR
   - System health OK?
   - Any errors?
   - Customer issues?
   - Revenue trends?
   - Opportunities?

2. ANALYZE
   - Normal or anomaly?
   - Immediate action needed?
   - Pattern or one-off?

3. DECIDE
   - Within authority? → Act
   - Need approval? → Business case
   - Just FYI? → Log for report

4. ACT
   - Execute decision
   - Log action
   - Monitor result

5. REPORT
   - Update dashboard
   - Log in daily report
   - Alert if urgent
```

### Decision Authority

**I CAN do without asking:**
- Customer support responses
- Bug fixes
- Performance optimization
- Data collection
- Routine maintenance
- System monitoring
- Report generation

**I MUST ask for approval:**
- ANY spending (even $1)
- Strategic decisions
- Pricing changes
- Marketing campaigns
- Partnerships
- Legal matters
- Major architecture changes

---

## Alert System

### Priority Levels

**P0 - Critical** (Immediate Telegram)
- System down >5 min
- Revenue drop >20%
- Security incident
- Data loss

**P1 - High** (Within 1 hour)
- System degraded
- Revenue drop 10-20%
- Error spike (>10/hour)
- Failed payments

**P2 - Medium** (Daily report)
- Minor errors
- Small fluctuations
- Handled issues

**P3 - Low** (Weekly summary)
- Successful deployments
- Improvements
- General metrics

---

## Setup Checklist (Tomorrow - Feb 1)

### Phase 1: Foundation (1 hour)
- [ ] Create complete directory structure
- [ ] Set up Python virtual environment
- [ ] Install required packages
- [ ] Configure Windows (never sleep, auto-login)
- [ ] Set up Remote Desktop
- [ ] Install TeamViewer

### Phase 2: Monitoring (1 hour)
- [ ] Build logging system
- [ ] Create web dashboard
- [ ] Configure Telegram alerts
- [ ] Test alert system
- [ ] Verify Rob can access remotely

### Phase 3: Operations (1 hour)
- [ ] Set up proactive monitoring loops
- [ ] Configure scheduling system
- [ ] Build task queue
- [ ] Test autonomous operations

### Phase 4: Financial (30 min)
- [ ] Create business case templates
- [ ] Set up expense tracking
- [ ] Build approval workflows
- [ ] Configure budget reporting

### Phase 5: Testing (30 min)
- [ ] End-to-end test
- [ ] Verify monitoring
- [ ] Test alerts
- [ ] Confirm remote access
- [ ] Generate test report

**Total: ~4 hours**

---

## What I Need From You Tomorrow

### Technical
1. Viper PC specs
2. Network setup (Wi-Fi credentials)
3. Remote access preferences
4. Windows user credentials

### Communication
5. Telegram bot setup (for alerts)
6. Preferred alert times (avoid sleep hours?)
7. Dashboard URL preference

### Operational
8. Business hours definition
9. Weekend activity level
10. Reporting schedule (daily 6:30pm OK?)

---

## The Goal

**Tomorrow's outcome:**
- Complete infrastructure ready
- Rob can monitor remotely via web dashboard
- Alert system working
- Financial controls in place
- Proactive monitoring operational
- Foundation for adding businesses

**NOT doing yet:**
- Running specific businesses (add after infrastructure is solid)
- Spending money (need business cases first)
- Strategic decisions (that's Rob's role)

**This is infrastructure first, businesses second.**

---

*Build it right, build it once.*

