"""HuggingFace Hub model registry: load / save PPO policy as safetensors.

Versioning convention:
- Each push creates a new commit (immutable hash).
- A `production` git-tag marks the currently-deployed model.
- At startup, the runtime tries to download the file referenced by the
  `production` tag. If anything fails (no HF token, no repo, offline, etc.)
  it logs a warning and returns None so the caller can fall back to a
  freshly initialised model.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

POLICY_FILENAME = "policy.safetensors"
LOCAL_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _local_path() -> Path:
    return LOCAL_CACHE_DIR / POLICY_FILENAME


def download_production_policy(repo_id: str, hf_token: Optional[str] = None) -> Optional[str]:
    """Pull the production-tagged policy file. Returns local path, or None on failure."""
    if not repo_id:
        logger.info("HF_MODEL_REPO not set — skipping registry pull.")
        return None
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=repo_id,
            filename=POLICY_FILENAME,
            revision="production",
            token=hf_token or None,
            local_dir=str(LOCAL_CACHE_DIR),
        )
        logger.info(f"Downloaded production policy from {repo_id} → {path}")
        return path
    except Exception as e:
        logger.warning(f"Could not pull production policy from {repo_id}: {e}")
        return None


def upload_policy(
    local_path: str,
    repo_id: str,
    hf_token: str,
    commit_message: str = "update policy",
    tag_as_production: bool = False,
) -> Optional[str]:
    """Push a policy file to the hub. Optionally moves the `production` tag."""
    if not repo_id or not hf_token:
        logger.warning("upload_policy skipped — missing repo_id or token")
        return None
    try:
        from huggingface_hub import HfApi, create_repo

        api = HfApi(token=hf_token)
        create_repo(repo_id, token=hf_token, exist_ok=True, private=False)

        commit = api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=POLICY_FILENAME,
            repo_id=repo_id,
            commit_message=commit_message,
        )

        if tag_as_production:
            # Delete the old prod tag if it exists, then re-create at latest commit.
            try:
                api.delete_tag(repo_id=repo_id, tag="production")
            except Exception:
                pass
            api.create_tag(repo_id=repo_id, tag="production", revision=None, tag_message="promoted")
            logger.info(f"Tagged {repo_id} commit as production")

        logger.info(f"Uploaded policy to {repo_id}: {commit}")
        return str(commit)
    except Exception as e:
        logger.warning(f"upload_policy failed: {e}")
        return None
