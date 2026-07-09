from dotenv import load_dotenv
load_dotenv()
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
stores = client.beta.vector_stores.list()
for s in stores.data:
    print(s.id, "-", s.name, "-", s.file_counts.total, "files")