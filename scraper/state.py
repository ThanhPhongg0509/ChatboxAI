"""
Tracks a content hash + OpenAI file_id per article across runs, so the
daily job can compute a delta (added / updated / skipped) instead of
re-uploading everything every time.

State is a flat JSON file. For a ~30-300 article knowledge base this is
plenty; swap for SQLite/Redis if the corpus grows much larger.
"""
import hashlib
import json
import os

DEFAULT_STATE_PATH = os.environ.get("STATE_PATH", ".state/state.json")


def load_state(path: str = DEFAULT_STATE_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict, path: str = DEFAULT_STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify(article_id: str, new_hash: str, state: dict) -> str:
    """Returns 'added', 'updated', or 'skipped' for a given article."""
    prev = state.get(article_id)
    if prev is None:
        return "added"
    if prev.get("hash") != new_hash:
        return "updated"
    return "skipped"
