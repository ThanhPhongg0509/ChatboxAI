# ChatboxAI — OptiBot Knowledge Sync

Scrapes a Zendesk-powered help center, converts articles to Markdown, and
keeps an OpenAI Vector Store in sync via a daily delta job. Powers a
support Assistant ("OptiBot") backed by `file_search`.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.sample .env
```

Edit `.env` and set:
- `OPENAI_API_KEY` — your OpenAI API key
- `VECTOR_STORE_NAME` — optional custom store name (default: `optibot-kb`)

After the first run, save the printed `VECTOR_STORE_ID` into `.env`.
After running `create_assistant.py`, save the printed `ASSISTANT_ID` into `.env` too.

## Run locally

```bash
python main.py                 # scrape -> convert -> diff -> upload delta
# copy the printed VECTOR_STORE_ID into .env, then:
python create_assistant.py     # one-time: creates the Assistant + attaches the vector store
# copy the printed ASSISTANT_ID into .env, then:
python test_assistant.py "How do I add a YouTube video?"
```

Re-running `python main.py` any time after that only uploads
added/changed articles — safe to run repeatedly, will not duplicate.

## How it works

1. **Scrape** (`scraper/zendesk_client.py`) — pulls every published
   article from `support.optisigns.com` via the public Zendesk Help
   Center REST API (cursor pagination), no auth needed for public docs.
2. **Convert** (`scraper/markdown_converter.py`) — turns each article's
   HTML body into clean Markdown (`markdownify`), preserving headings,
   links, and code blocks. Each file starts with an `Article URL: ...`
   line so the Assistant can cite it verbatim per the system prompt.
3. **Delta detection** (`scraper/state.py`) — SHA-256 hashes each
   article's rendered Markdown and compares against `.state/state.json`
   from the last run to classify it `added` / `updated` / `skipped`.
   State is saved incrementally (after every article), so an interrupted
   run can be resumed without re-uploading already-synced articles.
4. **Upload** (`scraper/vector_store.py`) — only the delta is pushed to
   the OpenAI Vector Store via `files.create` + `vector_stores.files.create`,
   polled manually with a 60s timeout per file (so one stuck file can't
   hang the whole job). Updated articles are deleted and re-added (vector
   stores don't support in-place edits).
5. **Chunking strategy** — left as OpenAI's `auto` strategy (~800 token
   chunks, ~400 token overlap) rather than custom static chunking.
   Each article file is a single self-contained topic and already fairly
   short, so the built-in contiguous-text-aware chunker performs well
   without extra tuning; this also keeps the pipeline API-only and simple.
   Latest run: **406 articles fetched, 262 already up to date (skipped),
   142 newly added, 1 updated** — all successfully embedded into vector
   store `vs_6a4f76ce82808191a3f0d530eae80175`.

## Assistant system prompt

Set verbatim in `create_assistant.py`:

## Docker

```bash
docker build -t kb-sync-daemon .
docker run --rm -e OPENAI_API_KEY=sk-... -e VECTOR_STORE_ID=vs_... kb-sync-daemon
echo $?   # 0 on success
```

Each run logs a one-line summary and exits 0:
`fetched=N added=N updated=N skipped=N vector_store=vs_...`

## Daily job (scheduled deployment)

Deployed via **GitHub Actions** (`.github/workflows/daily-sync.yml`) —
runs on a cron schedule (03:00 UTC daily) plus a manual "Run workflow"
button. It builds the Docker image fresh each run and executes it with
secrets injected as env vars.

Setup:
1. Repo → **Settings → Secrets and variables → Actions** → add
   `OPENAI_API_KEY` and `VECTOR_STORE_ID` as repository secrets.
2. **Actions** tab → the workflow runs automatically daily, or trigger it
   manually via **Run workflow** to test.

Job logs: **[TODO: paste your GitHub Actions run URL here, e.g.
`https://github.com/ThanhPhongg0509/ChatboxAI/actions/runs/29089590187/job/86351488537`]**

## Screenshot

**![OptiBot test](docs/screenshot.png)**

## Notes

- No API keys are committed; see `.env.sample`.
- `.state/` and `data/markdown/*.md` are gitignored (regenerated on each run).
