# Telegram Integration Setup Guide

Quick setup to receive all notifications on your phone via Telegram.

## Setup (5 minutes)

### 1. Create Bot
- Open Telegram, search **@BotFather**
- Send: `/newbot`
- Choose name and username
- **Save bot token**: `123456789:ABCdefGHI...`

### 2. Get Chat ID
- Search **@userinfobot** on Telegram
- Start chat
- **Save your Chat ID**: `123456789`

### 3. Set Environment Variables

Windows PowerShell:
```powershell
$env:TELEGRAM_BOT_TOKEN="your_token_here"
$env:TELEGRAM_CHAT_ID="your_chat_id_here"
```

Linux/Mac:
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 4. Test
```bash
python integrations/telegram_integration.py
```

Check Telegram for test message!

## What You Get

- 🚀 SOP execution notifications
- 📊 Daily/weekly summaries  
- ⚠️ Bottleneck alerts
- 📋 Performance reports
- 🔔 Approval requests
- 💡 Predictive alerts

All on your phone! 📱
