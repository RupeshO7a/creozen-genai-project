import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
 
load_dotenv()
 
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768
 
 
def embed(texts, task_type):
    """Turn a list of texts into a list of 768-number vectors.
    task_type: RETRIEVAL_DOCUMENT (for chunks) or RETRIEVAL_QUERY."""
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBED_DIM,
        ),
    )
    return [e.values for e in result.embeddings]
