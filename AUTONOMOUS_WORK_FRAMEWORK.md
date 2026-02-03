# Autonomous Work Framework
**Cost-Effective AI Operations Using Free/Local Resources**
**Date:** 2026-02-02

---

## Overview

Framework for autonomous work that minimizes costs by leveraging free local LLMs (Ollama on GPU) while maintaining high-quality output. Use paid Claude API only when necessary for complex reasoning.

---

## Available Resources

### ✅ FREE LOCAL LLMs (Ollama on RTX 3060)

**Available Models:**
1. **qwen2.5:7b-32k** ⭐ PRIMARY for autonomous work
   - 32,000 token context window
   - 7.6B parameters
   - Fast inference on GPU
   - Best for: Long documents, analysis, code generation

2. **qwen2.5:14b** - Larger model for complex tasks
   - 14.8B parameters
   - Higher quality but slower
   - Use when qwen2.5:7b insufficient

3. **llama3:latest** - General purpose
   - 8.0B parameters
   - Good all-rounder

4. **gpt-oss:20b** - Largest model
   - 20.9B parameters
   - Use sparingly (slower)

5. **qwen2.5:0.5b** - Ultra-fast small model
   - For simple tasks, testing

6. **qwen2.5vl:7b** - Vision model
   - Can analyze images/screenshots

**Cost:** $0 (runs locally on GPU)
**Performance:** Excellent for most tasks

### ✅ GITHUB ACCESS

**GitHub Account:** bostonrobbie (rgorham369@gmail.com)

**Your Repositories:**
1. **AI** - Main AI workspace
   - https://github.com/bostonrobbie/AI.git

2. **PC-Agent-Claw** - OpenClaw fork
   - https://github.com/bostonrobbie/PC-Agent-Claw.git

3. **Prop-Firm-CoPilot** - Trading copilot
   - https://github.com/bostonrobbie/Prop-Firm-CoPilot.git

4. **NQ-Main-Algo** - NQ trading strategy
   - https://github.com/bostonrobbie/NQ-Main-Algo.git

5. **Inmail-gen** - LinkedIn/email tool
   - https://github.com/bostonrobbie/Inmail-gen.git

6. **Backtesting-Agent** - Backtesting framework
   - https://github.com/bostonrobbie/Backtesting-Agent.git

7. **Tradingview-Brokerage-Connector-** - Unified Bridge
   - https://github.com/bostonrobbie/Tradingview-Brokerage-Connector-.git

**Need to Find:** STS Suite (Signals, Strategies, Allocation Manager)
- Not yet located in local directories
- May be in separate repos or under different names

### ✅ BROWSER AUTOMATION (OpenClaw)

**Chrome Profile Access:** Available through OpenClaw
- Location: `C:\Users\User\Documents\AI\OpenClaw\src\browser`
- Capabilities:
  - Chrome DevTools Protocol (CDP)
  - Profile management
  - Playwright sessions
  - Screenshot/snapshot
  - Storage manipulation
  - Extension relay

**Can Access:**
- Your logged-in Chrome profile
- All your tabs and bookmarks
- Manus (if logged in via Chrome)
- Google Ads (if logged in via Chrome)

### ⚠️ NEED ACCESS TO

**Manus:**
- Deployment platform for STS suite
- Need to access via Chrome profile
- Located at: (URL to be determined)

**Google Ads Manager:**
- Need Chrome profile access
- Can build/research ads once accessed

---

## Cost-Effective Work Strategy

### Tier 1: FREE LOCAL (Use 90% of the time)

**Use qwen2.5:7b-32k for:**
- ✅ Code generation and debugging
- ✅ Documentation writing
- ✅ Data analysis
- ✅ Research and information gathering
- ✅ Report generation
- ✅ Simple Q&A
- ✅ Text processing
- ✅ Strategy planning
- ✅ Opportunity analysis

**How to use:**
```bash
# Via command line
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b-32k",
  "prompt": "Your prompt here"
}'

# Via Python
import requests
response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'qwen2.5:7b-32k',
    'prompt': 'Your prompt here'
})
```

**Cost:** $0
**Speed:** Fast (GPU-accelerated)
**Quality:** High for most tasks

### Tier 2: PAID CLAUDE (Use 10% of the time)

**Use Claude (me) only for:**
- ⚠️ Complex reasoning requiring multiple steps
- ⚠️ Critical financial decisions
- ⚠️ Novel problems without clear solutions
- ⚠️ Tasks requiring external tools (web search, file operations)
- ⚠️ High-stakes decisions needing verification

**Cost:** ~$0.015 per 1K tokens (Claude Sonnet)
**When:** Only when local LLM insufficient

---

## Autonomous Work Workflow

### Phase 1: Planning (Use Local LLM)

```python
# Use qwen2.5:7b-32k to plan work
prompt = f"""
I need to work on: {task_description}

Create a detailed plan with:
1. Steps to accomplish
2. Resources needed
3. Expected challenges
4. Success criteria
5. Time estimate

Be specific and actionable.
"""

plan = query_ollama('qwen2.5:7b-32k', prompt)
```

### Phase 2: Execution (Use Local LLM)

```python
# Execute each step with local LLM
for step in plan.steps:
    result = query_ollama('qwen2.5:7b-32k', f"""
    Execute this step: {step}

    Previous context: {context}

    Provide code/implementation.
    """)

    # Test locally
    if test_fails(result):
        # Retry with local LLM
        result = query_ollama('qwen2.5:14b', f"Fix this error: {error}")
```

### Phase 3: Verification (Use Local LLM or Claude)

```python
# Use local LLM for verification
verification = query_ollama('qwen2.5:7b-32k', f"""
Review this work: {result}

Check for:
1. Correctness
2. Completeness
3. Quality
4. Potential issues

Provide pass/fail and reasoning.
""")

# Only escalate to Claude if verification fails
if verification.status == 'uncertain':
    # Use Claude for complex verification
    claude_review = ask_claude(result)
```

### Phase 4: Reporting (Use Local LLM)

```python
# Generate report with local LLM
report = query_ollama('qwen2.5:7b-32k', f"""
Create a summary report:

Task: {task}
Results: {results}
Metrics: {metrics}

Format for Rob to read.
""")

send_telegram(report)
```

---

## STS Suite Work Plan

### What We Know

**STS Suite Components:**
1. **Signals** - Trading signal generation
2. **Strategies** - Strategy execution
3. **Allocation Manager** - Position sizing/risk
4. **Brokerage Connection** - (Unified Bridge?)

**Status:** Deployed on Manus
**Need:** Access to Manus to work on them

### Access Plan

**Step 1: Find STS Repos on GitHub**
```bash
# Search GitHub for STS repos
# Check if they're in bostonrobbie account
# Or private repos we haven't found yet
```

**Step 2: Access Manus via Chrome**
```typescript
// Use OpenClaw browser automation
// Access your Chrome profile
// Navigate to Manus
// Interact with deployed apps
```

**Step 3: Pull Code Locally**
```bash
# Once we find repos, clone them
git clone https://github.com/bostonrobbie/[sts-repo].git

# Then work locally using free LLM
```

### Development Workflow (Cost-Optimized)

**For Each STS Component:**

1. **Clone repo** (if accessible)
2. **Analyze with qwen2.5:7b-32k** (free)
   - Understand codebase
   - Identify improvements
   - Plan changes

3. **Implement with qwen2.5:7b-32k** (free)
   - Generate code
   - Write tests
   - Debug issues

4. **Review with qwen2.5:14b** (free, higher quality)
   - Code review
   - Quality check
   - Optimization suggestions

5. **Deploy via Manus** (once accessed)
   - Push to GitHub
   - Deploy on Manus
   - Monitor

**Cost:** ~$0 (all local LLM work)

---

## Google Ads Manager Work Plan

### Access Method

**Via Chrome Profile:**
```typescript
// Use OpenClaw browser automation
const browser = await chromium.launch({
  userDataDir: '[Your Chrome Profile Path]'
});

// Navigate to Google Ads
await page.goto('https://ads.google.com');

// Interact with interface
```

### Ad Research & Building (Cost-Optimized)

**Step 1: Research (Free Local LLM)**
```python
# Use qwen2.5:7b-32k for ad research
research = query_ollama('qwen2.5:7b-32k', """
Research Google Ads best practices for:
- SaaS products
- Trading tools
- B2B services

Provide:
1. Keyword strategies
2. Ad copy templates
3. Targeting recommendations
4. Budget allocation
5. Landing page tips
""")
```

**Step 2: Ad Copy Generation (Free Local LLM)**
```python
# Generate ad variations
for product in ['Signals', 'Strategies', 'Allocation Manager']:
    ads = query_ollama('qwen2.5:7b-32k', f"""
    Create 10 Google Ad variations for: {product}

    For each ad provide:
    - Headline (30 chars)
    - Description (90 chars)
    - Keywords
    - Target audience

    Make them compelling and high-converting.
    """)
```

**Step 3: Campaign Structure (Free Local LLM)**
```python
# Plan campaign structure
campaign = query_ollama('qwen2.5:7b-32k', """
Create complete Google Ads campaign for STS Suite:

1. Campaign structure
2. Ad groups
3. Keywords (with match types)
4. Bid strategies
5. Budget allocation
6. Conversion tracking setup

Be specific and actionable.
""")
```

**Step 4: Implementation (Via Chrome + Manus)**
- Access Google Ads via Chrome profile
- Implement campaign structure
- Upload ads
- Configure tracking

**Cost:** $0 (except actual ad spend when you approve)

---

## Immediate Next Steps

### 1. GitHub Exploration ✅ (Can Do Now)

```bash
# Search GitHub for STS repos
# Method 1: Check your GitHub account online
# Method 2: Search local clones

# If repos are private, may need:
gh auth login  # (if gh CLI available)
# or
# Access via browser
```

### 2. Test Local LLM Quality ✅ (Can Do Now)

```python
# Test qwen2.5:7b-32k on real task
test_prompt = """
Analyze this trading strategy code and suggest improvements:
[paste NQ-Main-Algo code]

Focus on:
1. Risk management
2. Entry/exit logic
3. Performance optimization
4. Code quality
"""

result = query_ollama('qwen2.5:7b-32k', test_prompt)
# Evaluate quality vs Claude
```

### 3. Chrome Profile Access ⏳ (Need Help)

**Question for you:**
- What's the path to your Chrome user data directory?
- Is Manus at a specific URL I can navigate to?
- Is Google Ads already logged in?

**Default Chrome Profile Locations:**
```
Windows: C:\Users\[Username]\AppData\Local\Google\Chrome\User Data
```

### 4. Create Local LLM Wrapper ✅ (Can Do Now)

```python
# Create helper for easy Ollama access
class LocalLLM:
    def __init__(self, model='qwen2.5:7b-32k'):
        self.model = model
        self.endpoint = 'http://localhost:11434/api/generate'

    def query(self, prompt, stream=False):
        response = requests.post(self.endpoint, json={
            'model': self.model,
            'prompt': prompt,
            'stream': stream
        })
        return response.json()

    def analyze_code(self, code, focus='all'):
        # Specialized for code analysis
        pass

    def generate_ads(self, product, count=10):
        # Specialized for ad generation
        pass
```

---

## Questions Before I Start

### Access Questions:

1. **STS Suite GitHub:**
   - Are Signals/Strategies/Allocation Manager in separate repos?
   - Are they private repos I need access to?
   - Or are they part of another project?

2. **Manus Access:**
   - What's the Manus URL?
   - Is it at manus.ai or a custom deployment?
   - Do I just navigate to it via Chrome?

3. **Chrome Profile:**
   - Should I use the default Chrome profile?
   - Or a specific profile path?

4. **Google Ads:**
   - Is your Google Ads account already logged in?
   - Can I access it via your Chrome profile?

### Scope Questions:

1. **What to build first:**
   - Improve existing STS components?
   - Build new features?
   - Create ads/marketing?
   - All of the above?

2. **Priority order:**
   - Which is most important right now?
   - Signals? Strategies? Allocation? Ads?

---

## Summary

**I CAN DO NOW (Free/Local):**
- ✅ Code analysis/generation with qwen2.5:7b-32k
- ✅ Research and planning
- ✅ Documentation
- ✅ Ad copy generation
- ✅ Strategy development
- ✅ Opportunity analysis
- ✅ Work on existing GitHub repos

**I NEED ACCESS TO:**
- ⏳ STS Suite GitHub repos (need to find them)
- ⏳ Manus platform (via Chrome profile)
- ⏳ Google Ads Manager (via Chrome profile)

**I WON'T DO YET:**
- ❌ Build anything (waiting for your approval of plan)
- ❌ Deploy anything (waiting for access)
- ❌ Spend money (never without approval)

**COST PROJECTION:**
- Research/Planning: $0 (local LLM)
- Development: $0 (local LLM)
- Testing: $0 (local LLM)
- Only cost: Claude usage for complex decisions (~$1-5/day max)

---

Ready to start once you provide:
1. STS Suite GitHub repo names/locations
2. Manus URL and access method
3. Chrome profile path (if not default)
4. Priority order for what to work on first

Let me know and I'll start autonomous work using 90%+ local LLM!
