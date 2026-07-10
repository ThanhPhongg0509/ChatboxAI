"""
Sanity check script for the Assistant.
 
Usage:
    python test_assistant.py "How do I add a YouTube video?"
 
Prints the reply text plus any file citations, so you can screenshot the
terminal output (or run the same question in the OpenAI Playground UI for
a nicer screenshot).
"""
import os
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
 
ASSISTANT_ID = os.environ["ASSISTANT_ID"]
 
 
def ask(question: str) -> None:
    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=question)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
 
    while run.status in ("queued", "in_progress"):
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
 
    if run.status != "completed":
        print(f"Run did not complete: {run.status}")
        if getattr(run, "last_error", None):
            print(f"Error code: {run.last_error.code}")
            print(f"Error message: {run.last_error.message}")
        return
 
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0]
 
    for block in reply.content:
        if block.type != "text":
            continue
 
        text = block.text.value
        annotations = block.text.annotations
 
        # Replace each inline citation marker with a numbered [1], [2]...
        # placeholder (the raw marker is often invisible on some terminals),
        # and collect the source file for each one.
        cited_files = []
        for i, ann in enumerate(annotations, start=1):
            text = text.replace(ann.text, f"[{i}]")
            if getattr(ann, "file_citation", None):
                cited_files.append(ann.file_citation.file_id)
 
        print(text)
 
        if cited_files:
            print("\nSources:")
            for i, file_id in enumerate(cited_files, start=1):
                try:
                    f = client.files.retrieve(file_id)
                    article_url = _lookup_article_url(f.filename)
                    print(f"  [{i}] {article_url or f.filename}")
                except Exception:
                    print(f"  [{i}] {file_id}")
        else:
            print("\n(No citations returned for this reply.)")
 
 
def _lookup_article_url(filename: str) -> str | None:
    """Reads the local data/markdown/<filename> and returns its
    'Article URL: ...' line, if present."""
    path = os.path.join("data", "markdown", filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Article URL:"):
                return line.strip()
    return None
 
 
if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do I add a YouTube video?"
    ask(q)