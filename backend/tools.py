
from rag import retrieve


def search_documents(query):
    """Search uploaded research papers and return relevant passages."""

    rows = retrieve(query, k=4, min_similarity=0.45)

    return [
        {
            "content": row.get("content", ""),
            "source": row.get("source", "Unknown PDF"),
            "page": row.get("page", "Unknown"),
            "similarity": row.get("similarity"),
        }
        for row in rows
        if row.get("content")
    ]


TOOLS = {
    "search_documents": search_documents,
}
