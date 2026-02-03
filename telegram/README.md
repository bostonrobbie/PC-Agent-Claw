# Telegram Intelligence Bot

Deep integration system providing natural language access to all 25 Intelligence Hub capabilities via Telegram.

## Features

### 1. Command-Based Interface (12 Commands)
- `/analyze` - Run full workspace analysis (all 25 capabilities)
- `/review [file]` - Deep code review with suggestions and security scan
- `/security` - Security vulnerability scan and report issues
- `/performance` - Show current performance metrics (CPU, memory, tasks)
- `/search [query]` - Semantic code search across workspace
- `/ask [question]` - Ask questions about the codebase
- `/learn [feedback]` - Record learning/feedback for future improvements
- `/status` - System health status (all 25 capabilities)
- `/patterns` - Show discovered patterns from code reviews
- `/improve` - Get self-improvement suggestions based on analysis
- `/test [duration]` - Start real-world test (duration in minutes)
- `/memory [query]` - Query relationship memory system
- `/help` - Show available commands

### 2. Natural Language Understanding
The bot understands natural language queries and routes them intelligently:
- "find authentication code" → Triggers semantic search
- "what is the intelligence hub?" → Triggers ask/search
- "review my latest changes" → Triggers code review
- "check for security issues" → Triggers security scan
- "show me performance metrics" → Triggers performance command
- "what patterns have you learned?" → Shows learned patterns
- "test the system for 5 minutes" → Starts real-world test
- "tell me about Python preferences" → Queries memory system

### 3. Real-Time Notifications
Proactive notifications with priority levels:
- 🚨 **Critical** - Immediate security issues, system failures
- ⚠️ **High** - Important warnings, issues requiring attention
- ℹ️ **Normal** - General updates, information
- 💬 **Low** - Background updates, minor information

### 4. Rich Formatted Responses
- Markdown formatting for readability
- Code snippets with syntax highlighting
- Emoji indicators for status and priorities
- Progress indicators for long-running operations

### 5. User Interaction Tracking
SQLite database tracking:
- User interactions and commands
- Command execution times
- Response success rates
- User satisfaction indicators
- Notification delivery statistics

## Setup

### 1. Configure Telegram Bot

Create a bot with @BotFather on Telegram:

```bash
1. Message @BotFather on Telegram
2. Send: /newbot
3. Follow prompts to create your bot
4. Copy the bot token
```

### 2. Configure Bot Token

Add to `telegram_config.json`:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "chat_id": "YOUR_CHAT_ID",
  "enabled": true
}
```

Or set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 3. Initialize Bot

```python
from telegram.intelligence_bot import TelegramIntelligenceBot

# Initialize
bot = TelegramIntelligenceBot()

# Connect to chat
bot.connect("your_chat_id")

# Handle commands
response = bot.handle_command("status", [], "your_chat_id")
print(response)

# Handle natural language
response = bot.handle_natural_language("find memory management code")
print(response)
```

## Usage Examples

### Command-Based

```python
# Analyze workspace (all 25 capabilities)
response = bot.handle_command("analyze", [], chat_id)

# Review specific file
response = bot.handle_command("review", ["src/main.py"], chat_id)

# Security scan
response = bot.handle_command("security", [], chat_id)

# Performance metrics
response = bot.handle_command("performance", [], chat_id)

# Search code
response = bot.handle_command("search", ["authentication logic"], chat_id)

# Ask questions
response = bot.handle_command("ask", ["what is the memory system"], chat_id)

# Learn from feedback
response = bot.handle_command("learn", ["Always use type hints"], chat_id)

# Get system status
response = bot.handle_command("status", [], chat_id)

# Show patterns
response = bot.handle_command("patterns", [], chat_id)

# Get improvements
response = bot.handle_command("improve", [], chat_id)

# Start test
response = bot.handle_command("test", ["5"], chat_id)  # 5 minutes

# Query memory
response = bot.handle_command("memory", ["Python preferences"], chat_id)
```

### Natural Language

```python
# Search queries
bot.handle_natural_language("find database connection code")
bot.handle_natural_language("where is the authentication handler?")

# Ask queries
bot.handle_natural_language("what is the intelligence hub?")
bot.handle_natural_language("tell me about the memory system")

# Review queries
bot.handle_natural_language("review the security module")
bot.handle_natural_language("check my latest changes")

# Status queries
bot.handle_natural_language("how's the system doing?")
bot.handle_natural_language("what's your health status?")

# Performance queries
bot.handle_natural_language("show me performance metrics")
bot.handle_natural_language("how are resources being used?")

# Learning queries
bot.handle_natural_language("what patterns have you discovered?")
bot.handle_natural_language("show me improvement suggestions")

# Memory queries
bot.handle_natural_language("what do you remember about Python?")
bot.handle_natural_language("recall my preferences")

# Testing queries
bot.handle_natural_language("test the system for 5 minutes")
bot.handle_natural_language("run a benchmark")
```

### Notifications

```python
# Send notifications
bot.send_notification(
    "Security vulnerability detected!",
    priority="critical",
    category="security"
)

bot.send_notification(
    "Analysis complete",
    priority="normal",
    category="analysis"
)
```

## Integration with Intelligence Hub

The bot deeply integrates with all 25 Intelligence Hub capabilities:

### Memory & Learning
- Persistent memory for long-term learning
- Mistake learning and correction tracking
- Context management for conversations
- Code review learning from feedback

### Autonomous Systems
- Background task management
- Auto-debugging capabilities
- Proactive assistance

### Advanced Understanding
- Semantic code search
- Real-time internet access
- Mathematical computation engine

### Security & Monitoring
- Vulnerability scanning
- Resource monitoring
- Security pattern detection

### Communication
- Smart notifications
- Priority-based delivery
- User preference learning

## Database Schema

### Interactions Table
```sql
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    chat_id TEXT,
    command TEXT,
    query TEXT,
    timestamp REAL,
    response_time REAL,
    success BOOLEAN,
    error_message TEXT
);
```

### Commands Executed
```sql
CREATE TABLE commands_executed (
    id INTEGER PRIMARY KEY,
    command_type TEXT,
    args TEXT,
    execution_time REAL,
    result_size INTEGER,
    timestamp REAL
);
```

### Notifications Sent
```sql
CREATE TABLE notifications_sent (
    id INTEGER PRIMARY KEY,
    chat_id TEXT,
    message TEXT,
    priority TEXT,
    category TEXT,
    timestamp REAL,
    delivered BOOLEAN
);
```

### Satisfaction Tracking
```sql
CREATE TABLE satisfaction (
    id INTEGER PRIMARY KEY,
    interaction_id INTEGER,
    rating INTEGER,
    feedback TEXT,
    timestamp REAL
);
```

## Analytics

Get comprehensive statistics:

```python
stats = bot.get_stats()

print(f"Total interactions: {stats['total_interactions']}")
print(f"Command breakdown: {stats['command_breakdown']}")
print(f"Average response time: {stats['avg_response_time']}s")
print(f"Notification delivery rate: {stats['notifications']['delivery_rate']}")
```

Get interaction history:

```python
history = bot.get_interaction_history(limit=50)

for interaction in history:
    print(f"Command: {interaction['command']}")
    print(f"Success: {interaction['success']}")
    print(f"Response time: {interaction['response_time']}s")
```

## Testing

Run comprehensive test suite:

```bash
python tests/test_telegram_bot.py
```

Tests include:
- Command handling (all 8 commands)
- Natural language understanding
- Notification system
- Database tracking
- Intelligence Hub integration
- Error handling
- Performance testing
- Edge cases

## Architecture

```
TelegramIntelligenceBot
├── Command Handler
│   ├── /analyze → Intelligence Hub analysis
│   ├── /review → Code review + security scan
│   ├── /security → Vulnerability scanning
│   ├── /search → Semantic code search
│   ├── /learn → Memory recording
│   ├── /status → System health check
│   ├── /patterns → Pattern discovery
│   └── /improve → Improvement suggestions
│
├── Natural Language Router
│   ├── Intent detection from patterns
│   ├── Argument extraction
│   └── Route to appropriate handler
│
├── Notification System
│   ├── Priority-based delivery
│   ├── Rich formatting
│   └── Delivery tracking
│
├── Database Tracker
│   ├── Interactions logging
│   ├── Command execution metrics
│   ├── Satisfaction tracking
│   └── Analytics generation
│
└── Intelligence Hub Integration
    ├── Memory systems
    ├── Learning systems
    ├── Autonomous systems
    ├── Security systems
    └── Monitoring systems
```

## Best Practices

1. **Use Natural Language** - The bot understands intent, no need to memorize commands
2. **Monitor Notifications** - Enable notifications for proactive assistance
3. **Provide Feedback** - Use `/learn` to teach the bot your preferences
4. **Check Status Regularly** - Use `/status` to monitor system health
5. **Review Patterns** - Use `/patterns` to see what the bot has learned

## Troubleshooting

### Bot not responding
- Check bot token is valid
- Verify chat_id is correct
- Check network connectivity

### Commands timing out
- Long operations show progress indicators
- Increase timeout if needed
- Check workspace size

### Database errors
- Ensure write permissions for database file
- Check disk space
- Verify SQLite installation

## Future Enhancements

- [ ] Voice message support
- [ ] Image analysis capabilities
- [ ] Multi-user support with permissions
- [ ] Custom command creation
- [ ] Scheduled notifications
- [ ] Interactive workflows
- [ ] Inline query support
- [ ] Bot API webhook mode

## License

Part of the Intelligence Hub AI System

## Support

For issues or questions, check the main Intelligence Hub documentation.
