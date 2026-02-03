"""
Telegram Integration Package

Provides deep integration between Telegram and the Intelligence Hub,
enabling natural language access to all 25 AI capabilities.
"""

from .intelligence_bot import TelegramIntelligenceBot, CommandType

__all__ = ['TelegramIntelligenceBot', 'CommandType']
