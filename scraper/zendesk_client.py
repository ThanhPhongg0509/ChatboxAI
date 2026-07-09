"""
Zendesk Help Center API client.

support.optisigns.com is a public Zendesk Guide instance, so no auth token
is required to read published articles. We use the standard Help Center
REST API with cursor pagination.

Docs: https://developer.zendesk.com/api-reference/help_center/help-center-api/articles/
"""
import time
import requests

BASE_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
PAGE_SIZE = 100
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5


def fetch_all_articles():
    """
    Yields every published article (as a dict) from the OptiSigns help
    center, following cursor pagination until exhausted.
    """
    url = f"{BASE_URL}?page[size]={PAGE_SIZE}"

    while url:
        payload = _get_with_retry(url)
        for article in payload.get("articles", []):
            # Skip drafts / archived items that slip through, if any.
            if article.get("draft"):
                continue
            yield article

        # Zendesk cursor pagination returns the next page's full URL,
        # or None when we've reached the end.
        url = payload.get("links", {}).get("next")


def _get_with_retry(url):
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts") from last_exc
