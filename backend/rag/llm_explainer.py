"""LLM-grounded signal explainer using Google Gemini with Postgres-backed caching.

For each RL trading signal, retrieves relevant news via RAG, then prompts
Gemini to produce a sentiment score, rationale, and citations. Results are
cached for 10 minutes per (symbol, hour) to stay within the free-tier 15 RPM.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import LLMCache
from backend.rag.retriever import retrieve

logger = logging.getLogger(__name__)

CACHE_TTL_MS = 10 * 60 * 1000  # 10 minutes

SYSTEM_PROMPT = """You are a crypto market analyst AI. Given recent news articles and a trading signal, provide:
1. A sentiment_score from -1.0 (extremely bearish) to 1.0 (extremely bullish)
2. A concise rationale (2-3 sentences) explaining the market sentiment
3. citations: a list of the most relevant article URLs that support your analysis

Respond ONLY with valid JSON in this exact format:
{"sentiment_score": 0.5, "rationale": "...", "citations": [{"url": "...", "title": "..."}]}"""


def _cache_key(symbol: str) -> str:
    hour_bucket = int(time.time() // 3600)
    return hashlib.sha256(f"{symbol}:{hour_bucket}".encode()).hexdigest()[:32]


async def _get_cached(session: AsyncSession, key: str) -> Optional[Dict[str, Any]]:
    result = await session.execute(
        select(LLMCache).where(
            LLMCache.cache_key == key,
            LLMCache.expires_at_ms > int(time.time() * 1000),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row.response
    return None


async def _set_cache(session: AsyncSession, key: str, response: Dict[str, Any]) -> None:
    existing = await session.execute(select(LLMCache).where(LLMCache.cache_key == key))
    row = existing.scalar_one_or_none()
    if row:
        row.response = response
        row.expires_at_ms = int(time.time() * 1000) + CACHE_TTL_MS
    else:
        session.add(LLMCache(
            cache_key=key,
            response=response,
            expires_at_ms=int(time.time() * 1000) + CACHE_TTL_MS,
        ))


async def explain_signal(
    session: AsyncSession,
    symbol: str,
    signal_type: str,
    price: float,
) -> Dict[str, Any]:
    fallback = {
        "sentiment_score": 0.0,
        "rationale": "No LLM analysis available — Gemini API key not configured.",
        "citations": [],
    }

    if not settings.gemini_api_key:
        return fallback

    cache_key = _cache_key(symbol)
    cached = await _get_cached(session, cache_key)
    if cached:
        logger.info(f"LLM cache hit for {symbol}")
        return cached

    # Retrieve relevant news
    asset = symbol.split("/")[0] if "/" in symbol else symbol
    news = await retrieve(session, query=f"{asset} crypto market", asset=asset, top_k=5)

    if not news:
        news_context = "No recent news available."
    else:
        news_context = "\n\n".join(
            f"[{n['source']}] {n['title']}\n{n['body']}\nURL: {n['url']}"
            for n in news
        )

    user_prompt = f"""Trading Signal: {signal_type} {symbol} at ${price:.2f}

Recent News:
{news_context}

Analyze the market sentiment and explain this signal."""

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            [{"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]}],
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=512,
            ),
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        result["sentiment_score"] = max(-1.0, min(1.0, float(result.get("sentiment_score", 0))))
        result.setdefault("rationale", "")
        result.setdefault("citations", [])

        await _set_cache(session, cache_key, result)
        await session.commit()

        logger.info(f"LLM analysis for {symbol}: sentiment={result['sentiment_score']}")
        return result

    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return fallback
