"""News ingestion pipeline — CryptoPanic + Reddit → chunk → embed → pgvector.

Designed to run as a scheduled job (GitHub Actions hourly cron) or on-demand.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import NewsChunk
from backend.db.session import AsyncSessionLocal
from backend.rag.embedder import embed_texts

logger = logging.getLogger(__name__)

CRYPTOPANIC_PUBLIC = "https://cryptopanic.com/api/free/v1/posts/"
REDDIT_CRYPTO = "https://www.reddit.com/r/CryptoCurrency/hot.json"
REDDIT_BITCOIN = "https://www.reddit.com/r/Bitcoin/hot.json"

ASSET_KEYWORDS = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth"],
    "BNB": ["bnb", "binance"],
    "SOL": ["solana", "sol"],
    "XRP": ["xrp", "ripple"],
}


def _detect_asset(text_lower: str) -> str:
    for asset, keywords in ASSET_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return asset
    return "CRYPTO"


def _chunk_id(source: str, url: str) -> str:
    return hashlib.sha256(f"{source}:{url}".encode()).hexdigest()[:32]


async def _fetch_cryptopanic() -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(CRYPTOPANIC_PUBLIC, params={"public": "true"})
            r.raise_for_status()
            data = r.json()

        for post in data.get("results", [])[:30]:
            title = post.get("title", "")
            url = post.get("url", post.get("source", {}).get("url", ""))
            published = post.get("published_at", "")
            ts_ms = int(time.time() * 1000)
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except Exception:
                pass

            chunks.append({
                "source": "cryptopanic",
                "title": title,
                "body": title,
                "url": url,
                "asset": _detect_asset(title.lower()),
                "published_at_ms": ts_ms,
            })
    except Exception as e:
        logger.warning(f"CryptoPanic fetch failed: {e}")
    return chunks


async def _fetch_reddit(subreddit_url: str, source_name: str) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        headers = {"User-Agent": "CryptoRLBot/1.0"}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(subreddit_url, headers=headers, params={"limit": 25})
            r.raise_for_status()
            data = r.json()

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            selftext = post.get("selftext", "")[:500]
            url = f"https://reddit.com{post.get('permalink', '')}"
            ts_ms = int(post.get("created_utc", time.time()) * 1000)

            body = f"{title}. {selftext}".strip() if selftext else title
            chunks.append({
                "source": source_name,
                "title": title,
                "body": body,
                "url": url,
                "asset": _detect_asset(title.lower() + " " + selftext.lower()),
                "published_at_ms": ts_ms,
            })
    except Exception as e:
        logger.warning(f"Reddit {source_name} fetch failed: {e}")
    return chunks


async def ingest_news() -> int:
    all_chunks = await _fetch_cryptopanic()
    reddit_results = await asyncio.gather(
        _fetch_reddit(REDDIT_CRYPTO, "r/CryptoCurrency"),
        _fetch_reddit(REDDIT_BITCOIN, "r/Bitcoin"),
    )
    for result in reddit_results:
        all_chunks.extend(result)

    if not all_chunks:
        logger.info("No news chunks fetched")
        return 0

    texts = [c["body"] for c in all_chunks]
    embeddings = embed_texts(texts)

    inserted = 0
    async with AsyncSessionLocal() as session:
        for chunk, embedding in zip(all_chunks, embeddings):
            existing = await session.execute(
                select(NewsChunk.id).where(
                    NewsChunk.url == chunk["url"],
                    NewsChunk.source == chunk["source"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            session.add(NewsChunk(
                asset=chunk["asset"],
                source=chunk["source"],
                title=chunk["title"],
                body=chunk["body"],
                url=chunk["url"],
                published_at_ms=chunk["published_at_ms"],
                embedding=embedding,
            ))
            inserted += 1

        await session.commit()

    logger.info(f"Ingested {inserted} new chunks (of {len(all_chunks)} fetched)")
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = asyncio.run(ingest_news())
    print(f"Ingested {count} chunks")
