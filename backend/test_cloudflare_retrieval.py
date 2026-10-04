
from rag import retrieve


def main():
    query = "What is self-attention in the Transformer architecture?"

    print("Testing Cloudflare-based research retrieval...")
    print("Query:", query)

    results = retrieve(query, k=4, min_similarity=0.0)

    print("\nResults returned:", len(results))

    for index, row in enumerate(results, start=1):
        print(f"\n--- Result {index} ---")
        print("Source:", row.get("source"))
        print("Page:", row.get("page"))
        print("Similarity:", row.get("similarity"))
        print("Content:", (row.get("content") or "")[:700])

    if not results:
        print(
            "\nNo results returned. Check the RPC function, its argument "
            "names, and whether the staging table contains embeddings."
        )
    else:
        print("\nRetrieval test completed.")


if __name__ == "__main__":
    main()
