# Deploy — 100% free, end-to-end

This file walks you through deploying the upgraded Crypto RL Trading Bot to a public URL you can drop into your resume. No credit card required for any service in this guide.

**Stack:**
- **Frontend** → Vercel
- **Backend** → HuggingFace Space (Docker)
- **Database** → Neon (serverless Postgres + pgvector)
- **Model registry** → HuggingFace Hub
- **LLM** → Google Gemini API (Phase 2)
- **Experiment tracking** → Weights & Biases (Phase 4)

Total time end-to-end: **~30 minutes** of clicking around + waiting on builds.

---

## Step 1 — Push the code to your own GitHub repo (5 min)

```bash
cd Crypto-RL-Trading-Bot-main
git add .
git commit -m "Phase 1: production-grade backend (Postgres, JWT, Docker, HF Hub)"
git remote -v   # confirm origin is your own repo
git push origin main
```

If your `origin` still points at someone else's repo, create a new repo on GitHub (e.g. `crypto-rl-trading-bot`), then:

```bash
git remote set-url origin https://github.com/<your-username>/crypto-rl-trading-bot.git
git push -u origin main
```

---

## Step 2 — Create a Neon Postgres database (5 min)

1. Go to **https://console.neon.tech/signup** → sign up with GitHub (no card).
2. Create a new project. Pick a region close to you.
3. After creation you'll see a **Connection string** panel. Pick **"Pooled connection"**.
4. Copy the URL. It looks like:
   ```
   postgresql://USER:PASS@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```
5. We need TWO env values from this one URL:
   - `DATABASE_URL` → same string but with `postgresql+asyncpg://` instead of `postgresql://`
   - `DATABASE_URL_SYNC` → the original `postgresql://...` (used by Alembic migrations)
6. **Save both strings somewhere safe** — you'll paste them into HuggingFace in Step 4.

---

## Step 3 — Create a HuggingFace account + model repo + Space (10 min)

### 3a. Sign up
- Go to **https://huggingface.co/join** → free signup, no card.

### 3b. Get an access token
- **https://huggingface.co/settings/tokens** → **Create new token**
- Name: `crypto-rl-bot`, role: **Write**
- Copy the token (`hf_...`) — save it.

### 3c. (Optional now, used Phase 4) Create a model repo
- **https://huggingface.co/new** → repository type **Model**
- Name: `crypto-rl-bot`. Public.
- Save the full id: `<your-username>/crypto-rl-bot`.

### 3d. Create the Space
- **https://huggingface.co/new-space**
- Owner: you. Space name: `crypto-rl-bot-api`. License: MIT.
- **Space SDK: Docker** (important — not Gradio/Streamlit).
- Choose: **Public** (so it never sleeps).
- Hardware: **CPU basic** (free).
- Click **Create Space**. You'll get a URL like `https://huggingface.co/spaces/<you>/crypto-rl-bot-api`.

### 3e. Replace the Space's auto-generated README
- In the Space, click **Files** → open `README.md` → click **Edit**.
- Replace its contents with the contents of `huggingface-space-README.md` from this repo (the part starting with `---` frontmatter is the important bit — it tells HF to run a Docker app on port 7860).
- Commit.

### 3f. Set Space secrets
In the Space → **Settings** → **Variables and secrets** → add each as a **Secret** (not Variable):

| Name | Value |
|---|---|
| `DATABASE_URL` | from Neon (with `postgresql+asyncpg://`) |
| `DATABASE_URL_SYNC` | from Neon (with `postgresql://`) |
| `JWT_SECRET` | run `python -c "import secrets;print(secrets.token_urlsafe(48))"` and paste output |
| `HF_TOKEN` | the token from 3b |
| `HF_MODEL_REPO` | `<your-username>/crypto-rl-bot` |
| `CORS_ORIGINS` | leave as `https://*.vercel.app` for now; we'll update after Vercel deploy |

---

## Step 4 — Wire GitHub Actions to auto-deploy to the Space (3 min)

In your GitHub repo → **Settings** → **Secrets and variables → Actions** → add three secrets:

| Name | Value |
|---|---|
| `HF_TOKEN` | the HF write token from 3b |
| `HF_USERNAME` | your HuggingFace username |
| `HF_SPACE_NAME` | `crypto-rl-bot-api` |

Now every push to `main` is mirrored to the Space and triggers a Docker rebuild there.

Trigger the first deploy:
```bash
git commit --allow-empty -m "Trigger HF Space deploy"
git push
```

Watch the build under **Actions** in GitHub, and then **Logs** in the HF Space. First build takes ~5–10 min (downloading PyTorch). Once it's green, hit `https://<you>-crypto-rl-bot-api.hf.space/healthz` — you should see `{"status":"ok",...}`.

---

## Step 5 — Deploy the frontend to Vercel (5 min)

1. **https://vercel.com/signup** → sign up with GitHub (no card).
2. **Add New Project** → Import your `crypto-rl-trading-bot` repo.
3. Framework preset: **Vite**. Build command: `npm run build` (default). Output dir: `dist`.
4. **Environment Variables** → add:
   - `VITE_API_URL` = `https://<you>-crypto-rl-bot-api.hf.space` (your Space URL, no trailing slash)
5. **Deploy**. After ~1 min you'll get a URL like `https://crypto-rl-trading-bot.vercel.app`.

### 5a. Lock down CORS
- Back in the HF Space → Settings → Secrets → edit `CORS_ORIGINS` → set to your Vercel URL exactly (e.g. `https://crypto-rl-trading-bot.vercel.app`). Commit/restart the Space.

---

## Step 6 — Verify the live demo (2 min)

Open your Vercel URL:
1. Register a new account — confirms DB connection + bcrypt + JWT all working.
2. Generate a signal — confirms RL agent loaded + bot loop running.
3. Watch the dashboard — confirms WebSocket through HTTPS/WSS works.
4. Run a backtest — confirms full request/response path.

If all four work — Phase 1 is live. You can drop the Vercel URL into your resume already; subsequent phases just make the project more impressive.

---

## Troubleshooting

- **HF Space build fails on PyTorch download** → retry; transient HF hub flakes happen.
- **Login returns 500** → check Space logs: most likely Alembic migrations didn't run because `DATABASE_URL_SYNC` is missing or wrong.
- **Vercel page loads but signals never appear** → DevTools console will show CORS errors if `CORS_ORIGINS` doesn't match the Vercel URL exactly (trailing slash, http vs https).
- **Neon connection refused** → make sure you used the **pooled** connection string, not the direct one.
