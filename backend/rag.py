
from llm import embed
from db import supabase


def retrieve(query, k=4, min_similarity=0.45):
    """Retrieve relevant research-paper chunks using Cloudflare embeddings."""

    if not query or not query.strip():
        return []

    # Generate a 1024-dimensional query embedding.
    vector = embed([query])[0]

    # Search only the Cloudflare staging table through its RPC function.
    result = supabase.rpc(
        "match_chunks_cloudflare",
        {
            "query_embedding": vector,
            "match_count": k,
        },
    ).execute()

    rows = result.data or []

    # Keep only results above the similarity threshold.
    relevant_rows = [
        row
        for row in rows
        if row.get("similarity") is not None
        and float(row["similarity"]) >= min_similarity
    ]

    return relevant_rows
