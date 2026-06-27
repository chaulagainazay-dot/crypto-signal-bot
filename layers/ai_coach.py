"""AI Coach — natural conversation about trading using Claude."""
import logging
import os
from typing import Optional
import anthropic

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert crypto trading coach and analyst. You help traders at all levels — from beginners to advanced.

Your role:
- Answer trading questions with clear, educational explanations
- Analyse specific coins when asked (but always say prices/predictions are probabilistic, not guaranteed)
- Help users understand technical analysis concepts
- Give portfolio feedback based on what users share
- Create personalised trading plans when requested
- Always include risk warnings where relevant

Guidelines:
- Be concise but thorough — use bullet points for clarity
- Always mention risk management
- Never guarantee profits or specific price targets
- Format responses for Telegram (use <b>bold</b> and <code>code</code> tags)
- When asked "should I buy X?", explain the technicals and fundamentals, then say the decision is theirs
- Keep responses under 800 words

Remember: You are a coach and educator, not a financial advisor. Always remind users to do their own research (DYOR)."""


async def ask_coach(user_message: str, history: list[dict] = None) -> str:
    """Send a message to the AI coach and get a response."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "🤖 <b>AI Coach unavailable</b>\n\n"
            "ANTHROPIC_API_KEY not configured.\n\n"
            "Please ask your bot admin to add the API key."
        )

    client = anthropic.AsyncAnthropic(api_key=api_key)

    messages = []
    if history:
        messages.extend(history[-6:])  # Keep last 3 exchanges
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
    except anthropic.AuthenticationError:
        return "❌ Invalid API key. Please check ANTHROPIC_API_KEY."
    except anthropic.RateLimitError:
        return "⚠️ Rate limit reached. Please try again in a moment."
    except Exception as e:
        log.error("AI coach error: %s", e)
        return f"❌ Coach temporarily unavailable. Error: {type(e).__name__}"
