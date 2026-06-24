---
title: Crypto RL Trading Bot
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: PPO RL crypto trading bot with RAG signals
---

# Crypto RL Trading Bot — Backend API

FastAPI + PyTorch PPO + RAG (Gemini) + Postgres (Neon + pgvector).

**This file is the README that lives at the root of the HuggingFace Space.**
Copy its contents into the Space's `README.md` (replacing the auto-generated
one) before the first deploy. The frontmatter above tells the Space to run as
a Docker app on port 7860.

## Required Space secrets

In the Space → Settings → Variables and secrets:

| Name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...neon.tech/...?sslmode=require` |
| `DATABASE_URL_SYNC` | `postgresql://...neon.tech/...?sslmode=require` |
| `JWT_SECRET` | strong random string |
| `HF_TOKEN` | (optional) for model registry |
| `HF_MODEL_REPO` | (optional) `username/crypto-rl-bot` |
| `GEMINI_API_KEY` | (optional, Phase 2) |
| `WANDB_API_KEY` | (optional, Phase 4) |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://crypto-rl-bot.vercel.app` |
