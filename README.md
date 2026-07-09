# Chatbot sync daemon

A one-shot job that scrapes Zendesk help articles, converts them to Markdown,
and uploads only changed content to an OpenAI vector store.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
```

Edit `.env` and set:

- `API_KEY` with your OpenAI key
- `VECTOR_STORE_NAME` if you want a custom store name

After the first run, save the printed `VECTOR_STORE_ID` and `ASSISTANT_ID` into `.env`.

## Run locally

```bash
python main.py
```

Then create the assistant once:

```bash
python create_assistant.py
```

Verify the assistant with a sample query:

```bash
python test_assistant.py "How do I add a YouTube video?"
```

## Docker

Build the container:

```bash
docker build -t chatboxai-sync .
```

Run once and exit 0:

```bash
docker run --rm -e API_KEY=sk-... -e VECTOR_STORE_ID=vs-... chatboxai-sync
```

If the vector store does not exist yet, omit `VECTOR_STORE_ID` on the first run,
then save the printed ID into `.env` before future runs.

## Daily job

This project is designed to run once per day as a scheduled job on any
cloud scheduler.

Suggested flow:

1. Build the image on your platform.
2. Schedule `docker run --rm -e API_KEY=... -e VECTOR_STORE_ID=... chatboxai-sync`
   to execute daily.
3. Confirm the run logs contain counts for `added`, `updated`, and `skipped`.

Job logs: **[TODO: paste link to your scheduler's run logs here]**

## Screenshot

**[TODO: paste a screenshot of the assistant answering a sample question
with cited Article URLs]**

## Notes

- No hard-coded API keys are committed. Use `.env.sample` to bootstrap local secrets.
- `.env` is ignored by git.
- `.state/` and `data/markdown/*.md` are regenerated on each run.
