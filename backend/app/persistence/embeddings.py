"""Embedding generation via AWS Bedrock (Titan Text Embeddings V2)."""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any, Protocol
import os
import urllib.request
import urllib.error

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.persistence.constants import (
    BEDROCK_EMBEDDING_MODEL_ID_DEFAULT,
    EMBEDDING_DIMENSION,
    TITAN_EMBED_V2_DIMENSIONS,
)

logger = logging.getLogger(__name__)


class EmbeddingSettings(BaseSettings):
    """Bedrock embedding configuration (from environment / `.env`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_region: str = Field(default="us-east-1", validation_alias="AWS_REGION")
    bedrock_embedding_model_id: str = Field(
        default=BEDROCK_EMBEDDING_MODEL_ID_DEFAULT,
        validation_alias="BEDROCK_EMBEDDING_MODEL_ID",
    )
    bedrock_embedding_dimensions: int = Field(
        default=EMBEDDING_DIMENSION,
        validation_alias="BEDROCK_EMBEDDING_DIMENSIONS",
    )

    @field_validator("bedrock_embedding_dimensions")
    @classmethod
    def dimensions_must_match_db(cls, v: int) -> int:
        if v not in TITAN_EMBED_V2_DIMENSIONS:
            raise ValueError(
                f"BEDROCK_EMBEDDING_DIMENSIONS must be one of {sorted(TITAN_EMBED_V2_DIMENSIONS)} "
                f"(Titan Embed V2); got {v}"
            )
        if v != EMBEDDING_DIMENSION:
            raise ValueError(
                f"BEDROCK_EMBEDDING_DIMENSIONS must be {EMBEDDING_DIMENSION} "
                f"(matches pgvector column); got {v}"
            )
        return v


class EmbeddingService(Protocol):
    """Protocol for text embedding providers."""

    async def embed_text(self, text: str) -> list[float]: ...


def _create_bedrock_client(region: str) -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


class BedrockEmbeddingService:
    """Calls Amazon Titan Text Embeddings V2 through Bedrock Runtime."""

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._settings = settings
        logger.info(
            "Bedrock embedding client: model=%s region=%s dims=%s",
            settings.bedrock_embedding_model_id,
            settings.aws_region,
            settings.bedrock_embedding_dimensions,
        )
        self._client = _create_bedrock_client(settings.aws_region)

    async def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("content must be non-empty for embedding")

        def _invoke() -> list[float]:
            body = json.dumps(
                {
                    "inputText": text,
                    "dimensions": self._settings.bedrock_embedding_dimensions,
                    "normalize": True,
                    "embeddingTypes": ["float"],
                }
            )
            try:
                response = self._client.invoke_model(
                    modelId=self._settings.bedrock_embedding_model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
            except (ClientError, BotoCoreError) as e:
                logger.exception("Bedrock InvokeModel failed")
                raise RuntimeError("Bedrock embedding request failed") from e

            payload = json.loads(response["body"].read())
            embedding = payload.get("embedding")
            if not isinstance(embedding, list):
                by_type = payload.get("embeddingsByType") or {}
                embedding = by_type.get("float")
            if not isinstance(embedding, list):
                raise RuntimeError("Bedrock response missing float embedding vector")
            return [float(x) for x in embedding]

        result = await asyncio.to_thread(_invoke)
        if len(result) != EMBEDDING_DIMENSION:
            raise RuntimeError(
                f"expected embedding dim {EMBEDDING_DIMENSION}, got {len(result)}"
            )
        return result


class LocalEmbeddingService:
    """OpenAI-compatible local embedding endpoint for customer-controlled nodes."""

    def __init__(self) -> None:
        self.base_url = os.getenv("LOCAL_EMBEDDING_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        self.model = os.getenv("LOCAL_EMBEDDING_MODEL", "bge-m3")
        self.api_key = os.getenv("LOCAL_EMBEDDING_API_KEY", "")
        self.timeout = float(os.getenv("LOCAL_EMBEDDING_TIMEOUT_SECONDS", "60") or "60")

    async def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("content must be non-empty for embedding")

        def _invoke() -> list[float]:
            payload = json.dumps({"model": self.model, "input": text}).encode("utf-8")
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(f"{self.base_url}/embeddings", data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                raise RuntimeError("Local embedding request failed") from exc
            data = body.get("data") or []
            vector = data[0].get("embedding") if data and isinstance(data[0], dict) else None
            if not isinstance(vector, list):
                raise RuntimeError("Local embedding response missing embedding vector")
            return [float(x) for x in vector]

        result = await asyncio.to_thread(_invoke)
        if len(result) != EMBEDDING_DIMENSION:
            raise RuntimeError(
                f"expected embedding dim {EMBEDDING_DIMENSION}, got {len(result)}; "
                "configure a local embedding model that emits 1024 dimensions"
            )
        return result


@lru_cache(maxsize=1)
def get_embedding_settings() -> EmbeddingSettings:
    return EmbeddingSettings()


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """FastAPI dependency: local/private embeddings by default; Bedrock remains optional."""
    provider = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()
    if provider in {"bedrock", "aws"}:
        return BedrockEmbeddingService(get_embedding_settings())
    return LocalEmbeddingService()
