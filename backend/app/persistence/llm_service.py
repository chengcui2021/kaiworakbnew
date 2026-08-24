"""LLM generation via AWS Bedrock (Converse API)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    """Bedrock LLM configuration (from environment / `.env`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_region: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    bedrock_llm_model_id: str = Field(
        default="qwen.qwen3-235b-a22b-2507-v1:0",
        validation_alias="BEDROCK_LLM_MODEL_ID",
    )
    bedrock_llm_max_tokens: int = Field(
        default=10000,
        validation_alias="BEDROCK_LLM_MAX_TOKENS",
    )
    bedrock_llm_temperature: float = Field(
        default=0.3,
        validation_alias="BEDROCK_LLM_TEMPERATURE",
    )


def _create_bedrock_client(region: str) -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


@dataclass(frozen=True)
class LLMUsageData:
    """Token counts from a single LLM call."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class GenerateResult:
    """Text output plus token-usage metadata."""

    text: str
    usage: LLMUsageData


class BedrockLLMService:
    """Calls an LLM through the Bedrock Converse API."""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        logger.info(
            "Bedrock LLM client: model=%s region=%s max_tokens=%s temperature=%s",
            settings.bedrock_llm_model_id,
            settings.aws_region,
            settings.bedrock_llm_max_tokens,
            settings.bedrock_llm_temperature,
        )
        self._client = _create_bedrock_client(settings.aws_region)

    async def generate(self, system_prompt: str, user_message: str) -> GenerateResult:
        """Send a system+user prompt pair to the model and return text + usage."""
        if not user_message or not user_message.strip():
            raise ValueError("user_message must be non-empty")

        def _invoke() -> GenerateResult:
            try:
                response = self._client.converse(
                    modelId=self._settings.bedrock_llm_model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": user_message}],
                        }
                    ],
                    system=[{"text": system_prompt}],
                    inferenceConfig={
                        "maxTokens": self._settings.bedrock_llm_max_tokens,
                        "temperature": self._settings.bedrock_llm_temperature,
                    },
                )
            except (ClientError, BotoCoreError) as e:
                logger.exception("Bedrock Converse call failed")
                raise RuntimeError("Bedrock LLM request failed") from e

            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            texts = [block["text"] for block in content_blocks if "text" in block]
            if not texts:
                raise RuntimeError("Bedrock Converse response contained no text")

            usage = response.get("usage", {})
            usage_data = LLMUsageData(
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
            )
            return GenerateResult(text="\n".join(texts), usage=usage_data)

        return await asyncio.to_thread(_invoke)


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()


@lru_cache(maxsize=1)
def get_llm_service() -> BedrockLLMService:
    """FastAPI dependency: Bedrock LLM (one client per process)."""
    return BedrockLLMService(get_llm_settings())
