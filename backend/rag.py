from llm import embed
from db import supabase
 
 
def retrieve(query, k=4):
    """Return the k most similar chunks for a question."""
    vector = embed([query], "RETRIEVAL_QUERY")[0]
    result = supabase.rpc(
        "match_chunks",
        {"query_embedding": vector, "match_count": k},
    ).execute()
    return result.data
