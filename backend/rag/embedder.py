"""Embedding service using Google text-embedding-004 (768-dim, free tier)."""
from __future__ import annotations

import logging
from typing import List

import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)

_MODEL = "models/text-embedding-004"
_DIMENSION = 768
_BATCH_SIZE = 100  # Gemini accepts up to 100 texts per request


def _configure() -> None:
    if not genai.get_default_generative_model_info:
        genai.configure(api_key=settings.gemini_api_key)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — returning zero vectors")
        return [[0.0] * _DIMENSION for _ in texts]

    _configure()
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        result = genai.embed_content(model=_MODEL, content=batch)
        all_embeddings.extend(result["embedding"])
    return all_embeddings


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
