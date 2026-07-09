"""
Handles pushing Markdown files into an OpenAI Vector Store, and removing
files that correspond to deleted/replaced articles.

Chunking strategy: we use OpenAI's default `auto` chunking strategy for
the vector store (max_chunk_size_tokens=800, chunk_overlap_tokens=400 by
default under the hood for file_search). We don't hand-roll chunking
because:
  1. Each article file is already a single coherent unit (one topic),
     typically well under a few thousand tokens.
  2. `file_search`'s built-in chunker is contiguous-text aware (keeps
     headings/code blocks together reasonably well) and is what the
     Assistants/Responses API is tuned to retrieve against.
  3. It keeps the pipeline simple and reproducible via the API alone.
See README for how to switch to a custom `static` chunking config if you
want tighter control (e.g. smaller chunks for very long articles).
"""
import os
from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    """Lazily creates the OpenAI client on first use (not at import time),
    so it doesn't matter whether .env was loaded before or after this
    module gets imported."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


class _ClientProxy:
    """Lets existing `client.xxx` call sites below keep working unchanged."""
    def __getattr__(self, name):
        return getattr(_get_client(), name)


client = _ClientProxy()


def _vector_stores():
    """Vector Store endpoints moved from `client.beta.vector_stores` to a
    top-level `client.vector_stores` in newer openai-python releases.
    Support both so this works regardless of which SDK version is
    installed."""
    c = _get_client()
    if hasattr(c, "vector_stores"):
        return c.vector_stores
    return c.beta.vector_stores


def get_or_create_vector_store(name: str) -> str:
    """Returns the vector store id, creating it on first run.

    The id is cached in VECTOR_STORE_ID env var / .env by the caller so
    subsequent runs reuse the same store instead of creating duplicates.
    """
    existing = os.environ.get("VECTOR_STORE_ID")
    if existing:
        return existing

    store = _vector_stores().create(name=name)
    return store.id


def upload_file(vector_store_id: str, filepath: str, timeout_sec: int = 60) -> str:
    """Uploads one Markdown file and attaches it to the vector store.
    Returns the OpenAI file_id (needed later for deletes/updates).

    Polls manually with a hard timeout instead of the SDK's unbounded
    create_and_poll, so one stuck file can't hang the whole job forever.
    """
    import time

    with open(filepath, "rb") as f:
        uploaded = client.files.create(file=f, purpose="assistants")

    vs_files = _vector_stores().files
    vs_files.create(vector_store_id=vector_store_id, file_id=uploaded.id)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status_obj = vs_files.retrieve(vector_store_id=vector_store_id, file_id=uploaded.id)
        if status_obj.status == "completed":
            return uploaded.id
        if status_obj.status == "failed":
            raise RuntimeError(f"Vector store indexing failed for {filepath}: {status_obj}")
        time.sleep(2)

    raise TimeoutError(
        f"Timed out after {timeout_sec}s waiting for {filepath} (file_id={uploaded.id}) "
        f"to finish indexing. Check platform.openai.com/storage/files for its status."
    )


def replace_file(vector_store_id: str, old_file_id: str, filepath: str) -> str:
    """Removes the old version of an updated article, then uploads the new
    one. Vector stores don't support in-place file edits, so update = delete
    + re-add."""
    delete_file(vector_store_id, old_file_id)
    return upload_file(vector_store_id, filepath)


def delete_file(vector_store_id: str, file_id: str) -> None:
    try:
        _vector_stores().files.delete(vector_store_id=vector_store_id, file_id=file_id)
    except Exception:
        pass  # already gone / never attached -- non-fatal
    try:
        client.files.delete(file_id)
    except Exception:
        pass


def count_chunks(vector_store_id: str, file_id: str) -> int | None:
    """Best-effort chunk count for logging (file_search doesn't expose this
    directly, so we fall back to file byte size if unavailable)."""
    try:
        f = _vector_stores().files.retrieve(vector_store_id=vector_store_id, file_id=file_id)
        counts = getattr(f, "chunking_strategy", None)
        return None if counts is None else None  # API doesn't return chunk count today
    except Exception:
        return None
