# kb-sync-daemon

Scrapes a Zendesk-powered help center, converts articles to Markdown, and
keeps an OpenAI Vector Store in sync via a daily delta job. Powers a
support Assistant ("OptiBot") backed by `file_search`.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env   # fill in OPENAI_API_KEY
```

## Run locally

```bash
python main.py                 # scrape -> convert -> diff -> upload delta
# copy the printed VECTOR_STORE_ID into .env, then:
python create_assistant.py     # one-time: creates the Assistant + attaches the vector store
# copy the printed ASSISTANT_ID into .env, then:
python test_assistant.py "How do I add a YouTube video?"
```

Re-running `python main.py` any time after that only uploads
added/changed articles (see **Delta detection** below) — `docker run` does
the same thing in a container and exits 0.

## How it works

1. **Scrape** (`scraper/zendesk_client.py`) — pulls every published
   article from `support.optisigns.com` via the public Zendesk Help
   Center REST API (cursor pagination), no auth needed for public docs.
2. **Convert** (`scraper/markdown_converter.py`) — turns each article's
   HTML body into clean Markdown (`markdownify`), preserving headings,
   links, and code blocks. Each file starts with a `Article URL: ...`
   line so the Assistant can cite it verbatim per the system prompt.
3. **Delta detection** (`scraper/state.py`) — SHA-256 hashes each
   article's rendered Markdown and compares against `.state/state.json`
   from the last run to classify it `added` / `updated` / `skipped`.
4. **Upload** (`scraper/vector_store.py`) — only the delta is pushed to
   the OpenAI Vector Store via `files.create` + `vector_stores.files.create_and_poll`.
   Updated articles are deleted and re-added (vector stores don't support
   in-place edits).
5. **Chunking strategy** — left as OpenAI's `auto` strategy (~800 token
   chunks, ~400 token overlap) rather than custom static chunking.
   Each article file is a single self-contained topic and already fairly
   short, so the built-in contiguous-text-aware chunker performs well
   without extra tuning; this also keeps the pipeline API-only and simple.

## Daily job

`main.py` is Dockerized and meant to run once per day via a scheduled
job (DigitalOcean App Platform "Scheduled Job", Render Cron Job, GitHub
Actions cron, etc.):

```bash
docker build -t kb-sync-daemon .
docker run -e OPENAI_API_KEY=sk-... -e VECTOR_STORE_ID=vs_... kb-sync-daemon
```

Each run logs a one-line summary:
`fetched=N added=N updated=N skipped=N vector_store=vs_...`

Job logs: **[TODO: paste link to your scheduler's run logs here, e.g.
DigitalOcean job run URL or GitHub Actions run URL]**

## Assistant system prompt

Set verbatim in `create_assistant.py`:

```
You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

## Screenshot

**[TODO: paste screenshot of `test_assistant.py` output or Playground
answering "How do I add a YouTube video?" with Article URL citations]**

## Notes

- No API keys are committed; see `.env.sample`.
- `.state/` and `data/markdown/*.md` are gitignored (regenerated on each run).
