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
if os.environ.get("API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]
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
        if block.type == "text":
            print(block.text.value)
 
 
if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do I add a YouTube video?"
    ask(q)