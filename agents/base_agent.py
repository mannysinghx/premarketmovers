"""
Base agent — wraps the Anthropic client and provides a single call() helper.
All specialised agents inherit from this.
"""

import os

import anthropic
from config import MODEL


class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        # Read key at instantiation time so Railway env vars and
        # runtime sidebar inputs are both picked up correctly.
        self._client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

    def call(self, user_message: str, max_tokens: int = 1024) -> str:
        """Send a message to Claude and return the text response."""
        response = self._client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip()
