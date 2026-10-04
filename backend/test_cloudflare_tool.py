
from tools import search_documents


def main():
    question = "What is self-attention in the Transformer architecture?"

    print("Testing Creozen document search...")
    documents = search_documents(question)

    print("Documents found:", len(documents))

    for index, document in enumerate(documents, start=1):
        print(f"\n--- Document {index} ---")
        print("Source:", document["source"])
        print("Page:", document["page"])
        print("Similarity:", document["similarity"])
        print("Passage:", document["content"][:500])

    if documents:
        print("\nPASS: Document search is working.")
    else:
        print("\nNo relevant documents found. Check the similarity threshold.")


if __name__ == "__main__":
    main()
