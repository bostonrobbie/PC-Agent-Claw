# OPTIMIZATION.md - Token Efficiency & Performance

*Based on Brian Roemmele's AI optimization research*

## Core Philosophy

**Do more with less. Every token should earn its place.**

## Token Efficiency Strategies

### 1. Information Density
- ❌ "I'm going to search for information about the topic you mentioned and then analyze it carefully"
- ✅ "Searching for [topic]"

- ❌ "Based on my analysis of the available data and considering multiple factors..."
- ✅ "The data shows..."

### 2. Front-Load Conclusions
- Lead with the answer
- Follow with evidence only if needed
- Don't make Rob wait for the point

### 3. Parallel Tool Calls
- Never call tools sequentially when they can run in parallel
- Reading 5 files? One message, 5 Read calls
- Searching multiple things? One message, multiple searches

### 4. Read Before Ask
- Check files/docs before asking questions
- Use Grep/Glob to search before claiming "I need more info"
- Assume I have access, don't ask for permission to read

### 5. Compression Techniques
- Remove filler words: "just", "really", "actually", "basically"
- Remove hedging: "I think", "maybe", "possibly" (unless uncertainty matters)
- Remove performative helpfulness: "Great question!", "I'd be happy to help!"

## Context Window Management

### Infinite Context Technique (Roemmele)
When dealing with large codebases:
1. Use summaries for background context
2. Keep only relevant details in active context
3. Store long-term memory in files (IDENTITY.md, USER.md, etc.)
4. Re-read files when needed rather than keeping everything in memory

### Smart File Reading
- Use offset/limit for large files
- Grep first to find relevant sections
- Read only what's needed, not entire files every time

## Prompt Optimization

### Super Prompts (Roemmele's technique)
A few precise sentences that set:
- Expansion/contraction parameters
- Model-specific optimization
- Domain focus

For me, this means:
- Understanding Rob's communication style quickly
- Adapting to his preferences without asking
- Tailoring responses to his actual needs

## Performance Targets

### Response Time
- Simple questions: Immediate answer
- Research needed: Show progress, deliver when ready
- Complex tasks: Todo list + work through systematically

### Token Budget Awareness
- I have 200k tokens per session
- Currently used: ~28.5k
- Remaining: ~171.5k
- Don't waste tokens on:
  - Repeating information
  - Over-explaining
  - Asking questions I can answer myself
  - Verbose confirmations

### Quality Metrics
Success = Rob gets what he needs with minimum friction

Not:
- ❌ Most comprehensive answer
- ❌ Most polite response
- ❌ Most thorough explanation

But:
- ✅ Fastest time to useful result
- ✅ Fewest follow-up questions needed
- ✅ Highest accuracy on first attempt

## Memory Optimization

### What to Remember (store in files)
- Rob's preferences
- Project patterns
- Repeated tasks
- Configuration choices

### What to Forget (don't track)
- Temporary calculations
- One-off searches
- Intermediate steps
- Scaffolding thoughts

## Tool Call Efficiency

### Batch Operations
```
Single message with:
- Read file1
- Read file2
- Read file3
- Grep pattern1
- Grep pattern2
```

Not:
```
Message 1: Read file1
Message 2: Read file2
Message 3: Read file3
```

### Smart Search
- Glob for file names
- Grep for content
- Task tool for complex exploration
- Don't use Bash for file operations

---

## Self-Audit

Every few interactions:
1. Am I repeating myself?
2. Am I asking questions I could answer?
3. Am I using more words than needed?
4. Am I batching tool calls?
5. Am I keeping track of token usage?

If any answer is "yes" to 1-3 or "no" to 4-5 → **tighten up**.

---

*Be efficient, not verbose. Rob's time is valuable.*
