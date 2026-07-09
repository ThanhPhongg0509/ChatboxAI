"""
Daily job entry point.

Flow:
  1. Pull every article from support.optisigns.com via Zendesk Help Center API.
  2. Convert each to Markdown, save to disk (data/markdown/<slug>.md).
  3. Diff against .state/state.json (content hash) to classify each
     article as added / updated / skipped.
  4. Upload only the delta (added + updated) to the OpenAI Vector Store.
  5. Persist new state + print a summary log.

Run once and exit 0 (safe for `docker run` / cron / scheduled job).
"""
from dotenv import load_dotenv
load_dotenv()  # must run before any module that reads OPENAI_API_KEY at import time

import os
import sys
import logging

if os.environ.get("API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]

from scraper.zendesk_client import fetch_all_articles
from scraper.markdown_converter import article_to_markdown, slugify
from scraper.state import load_state, save_state, content_hash, classify
from scraper.vector_store import get_or_create_vector_store, upload_file, replace_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("kb-sync")

MARKDOWN_DIR = "data/markdown"
VECTOR_STORE_NAME = os.environ.get("VECTOR_STORE_NAME", "optibot-kb")


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY or API_KEY is not set. Copy .env.sample to .env and fill it in.")
        return 1

    os.makedirs(MARKDOWN_DIR, exist_ok=True)
    state = load_state()
    vector_store_id = get_or_create_vector_store(VECTOR_STORE_NAME)
    log.info("Using vector store: %s", vector_store_id)

    counts = {"added": 0, "updated": 0, "skipped": 0, "total_fetched": 0}

    for article in fetch_all_articles():
        counts["total_fetched"] += 1
        article_id = str(article["id"])
        title = article.get("title", "untitled")

        md_text = article_to_markdown(article)
        h = content_hash(md_text)
        status = classify(article_id, h, state)

        slug = slugify(title, article["id"])
        filepath = os.path.join(MARKDOWN_DIR, f"{slug}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_text)

        if status == "added":
            try:
                file_id = upload_file(vector_store_id, filepath)
                state[article_id] = {"hash": h, "file_id": file_id, "slug": slug}
                save_state(state)
                counts["added"] += 1
                log.info("ADDED   %s", title)
            except Exception as e:
                counts["failed"] = counts.get("failed", 0) + 1
                log.error("FAILED to upload %s: %s", title, e)

        elif status == "updated":
            try:
                old_file_id = state[article_id]["file_id"]
                file_id = replace_file(vector_store_id, old_file_id, filepath)
                state[article_id] = {"hash": h, "file_id": file_id, "slug": slug}
                save_state(state)
                counts["updated"] += 1
                log.info("UPDATED %s", title)
            except Exception as e:
                counts["failed"] = counts.get("failed", 0) + 1
                log.error("FAILED to update %s: %s", title, e)

        else:
            counts["skipped"] += 1

    save_state(state)

    log.info(
        "Done. fetched=%d added=%d updated=%d skipped=%d vector_store=%s",
        counts["total_fetched"], counts["added"], counts["updated"],
        counts["skipped"], vector_store_id,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
