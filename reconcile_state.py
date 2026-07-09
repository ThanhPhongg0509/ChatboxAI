"""
One-off recovery script.
 
Use this if a previous run of main.py got interrupted (e.g. Ctrl+C)
*before* state.json was being saved incrementally, so the vector store
already has files uploaded but .state/state.json doesn't know about them.
 
It rebuilds .state/state.json by:
  1. Listing every file already attached to the vector store.
  2. Matching each one back to its local data/markdown/<slug>.md file
     (by filename).
  3. Re-hashing the local file content and recording {hash, file_id, slug}
     keyed by article_id (parsed from the slug's trailing numeric id).
 
Run once:
    python reconcile_state.py
"""
import os
import re
from dotenv import load_dotenv
load_dotenv()
 
from openai import OpenAI
from scraper.state import content_hash, save_state, load_state
 
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
VECTOR_STORE_ID = os.environ["VECTOR_STORE_ID"]
MARKDOWN_DIR = "data/markdown"
 
 
def _vector_stores():
    if hasattr(client, "vector_stores"):
        return client.vector_stores
    return client.beta.vector_stores
 
 
def main():
    state = load_state()
    before = len(state)
 
    recovered = 0
    unmatched = []
 
    all_vs_files = []
    after = None
    while True:
        page = _vector_stores().files.list(vector_store_id=VECTOR_STORE_ID, limit=100, after=after)
        all_vs_files.extend(page.data)
        if not page.has_more:
            break
        after = page.data[-1].id
 
    print(f"Vector store reports {len(all_vs_files)} file(s) total.")
 
    for vs_file in all_vs_files:
        file_obj = client.files.retrieve(vs_file.id)
        filename = file_obj.filename  # e.g. "how-to-xyz-123456.md"
        local_path = os.path.join(MARKDOWN_DIR, filename)
 
        if not os.path.exists(local_path):
            unmatched.append(filename)
            continue
 
        slug = filename.rsplit(".", 1)[0]
        m = re.search(r"-(\d+)$", slug)
        if not m:
            unmatched.append(filename)
            continue
        article_id = m.group(1)
 
        with open(local_path, "r", encoding="utf-8") as f:
            h = content_hash(f.read())
 
        state[article_id] = {"hash": h, "file_id": vs_file.id, "slug": slug}
        recovered += 1
 
    save_state(state)
    print(f"Recovered {recovered} article(s) into state.json (had {before} before).")
    if unmatched:
        with open("unmatched.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(unmatched))
        print(f"{len(unmatched)} vector-store file(s) couldn't be matched to a local .md file.")
        print("Full list written to unmatched.txt -- first 5 examples:")
        for u in unmatched[:5]:
            print("  -", u)
 
 
if __name__ == "__main__":
    main()