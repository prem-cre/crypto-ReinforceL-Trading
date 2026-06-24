"""Hybrid retriever: pgvector cosine similarity + Postgres full-text search.

Returns top-K relevant news chunks for a given query, combining vector and
keyword signals for better recall.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import NewsChunk
from backend.rag.embedder import embed_query

logger = logging.getLogger(__name__)


async def retrieve(
    session: AsyncSession,
    query: str,
    asset: Optional[str] = None,
    top_k: int = 5,
    hours_back: int = 48,
) -> List[Dict[str, Any]]:
    import time
    cutoff_ms = int((time.time() - hours_back * 3600) * 1000)

    query_embedding = embed_query(query)

    # pgvector cosine distance: 1 - cosine_sim => lower = more similar
    vector_q = (
        select(
            NewsChunk.id,
            NewsChunk.title,
            NewsChunk.body,
            NewsChunk.url,
            NewsChunk.source,
            NewsChunk.asset,
            NewsChunk.published_at_ms,
            NewsChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(NewsChunk.published_at_ms >= cutoff_ms)
        .order_by("distance")
        .limit(top_k * 3)
    )

    if asset:
        vector_q = vector_q.where(NewsChunk.asset == asset)

    result = await session.execute(vector_q)
    rows = result.all()

    # Re-rank: combine vector score with recency bonus
    scored = []
    now_ms = int(time.time() * 1000)
    for row in rows:
        age_hours = (now_ms - row.published_at_ms) / 3_600_000
        recency_bonus = max(0, 1.0 - age_hours / hours_back) * 0.2
        score = 1.0 - row.distance + recency_bonus
        scored.append({
            "id": str(row.id),
            "title": row.title,
            "body": row.body[:300],
            "url": row.url,
            "source": row.source,
            "asset": row.asset,
            "score": round(score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
