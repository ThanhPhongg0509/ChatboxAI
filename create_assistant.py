"""
One-time setup script: creates the OptiBot Assistant via the OpenAI API
and attaches it to the vector store built by main.py.

Run this AFTER main.py has populated the vector store at least once.
Prints the assistant_id -- save it to .env as ASSISTANT_ID.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
if os.environ.get("API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


def main():
    vector_store_id = os.environ.get("VECTOR_STORE_ID")
    if not vector_store_id:
        raise SystemExit("VECTOR_STORE_ID not set in .env. Run main.py first.")

    assistant = client.beta.assistants.create(
        name="OptiBot",
        model="gpt-4.1",
        instructions=SYSTEM_PROMPT,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )
    print(f"Created assistant: {assistant.id}")
    print("Add this to your .env as ASSISTANT_ID=" + assistant.id)


if __name__ == "__main__":
    main()
