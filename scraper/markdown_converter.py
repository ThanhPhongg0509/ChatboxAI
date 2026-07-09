"""
Converts a Zendesk article (HTML body) into clean, normalized Markdown.

Design notes:
- Zendesk's `body` field already contains only the article content (no
  site nav/sidebar/ads -- those live in the HC theme template, not the
  API payload), so we don't need to strip boilerplate chrome. We do still
  strip a couple of noisy wrapper elements Zendesk sometimes injects
  (empty <div>, inline style attrs) so the Markdown stays clean.
- Headings, code blocks (<pre>/<code>), and links are preserved.
- Every file starts with a small metadata header, including a literal
  "Article URL: <url>" line. This matters: the assistant's system prompt
  requires citing "Article URL:" lines, so having that exact string
  inline in the source doc lets the model quote it verbatim & correctly.
"""
import re
from markdownify import markdownify as html_to_md

STRIP_TAGS = ["script", "style", "iframe"]


def article_to_markdown(article: dict) -> str:
    title = article.get("title", "").strip()
    url = article.get("html_url", "")
    updated_at = article.get("updated_at", "")
    body_html = article.get("body") or ""

    cleaned_html = _strip_noise(body_html)

    body_md = html_to_md(
        cleaned_html,
        heading_style="ATX",       # '#' style headings
        bullets="-",
        code_language="",
        strip=STRIP_TAGS,
    )
    body_md = _normalize_whitespace(body_md)

    frontmatter = (
        f"# {title}\n\n"
        f"Article URL: {url}\n"
        f"Last Updated: {updated_at}\n\n"
        f"---\n\n"
    )
    return frontmatter + body_md.strip() + "\n"


def _strip_noise(html: str) -> str:
    for tag in STRIP_TAGS:
        html = re.sub(rf"<{tag}.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)
    return html


def _normalize_whitespace(md: str) -> str:
    # Collapse 3+ blank lines down to 2, trim trailing spaces per line.
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def slugify(title: str, article_id: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return f"{slug}-{article_id}"
