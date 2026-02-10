"""
LLM client for agent decision-making.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with OpenAI's API."""

    def __init__(self, config: Any) -> None:
        """
        Initialize LLM client.

        Args:
            config: Configuration object with openai_api_key and openai_model
        """
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model

    async def ask(self, system_prompt: str, user_prompt: str) -> str:
        """
        Single completion call, returns text response.

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query or task description

        Returns:
            str: The LLM's text response
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM ask error: {e}", exc_info=True)
            raise

    async def ask_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        JSON mode response. Returns parsed dict.

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query or task description

        Returns:
            dict: Parsed JSON response from the LLM
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt + "\n\nRespond ONLY with valid JSON.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"LLM ask_json error: {e}", exc_info=True)
            raise
