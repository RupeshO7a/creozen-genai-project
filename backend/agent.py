
from llm import generate_response
from tools import search_documents


SYSTEM = """
You are Creozen GenAI, an AI Research Paper Assistant.

Answer questions using the research-paper passages provided.

Rules:
1. Ground factual claims in the supplied passages.
2. Never invent paper contents, results, or citations.
3. Explain technical concepts clearly.
4. Cite relevant PDF filenames and page numbers.
5. If the passages do not answer the question, say so.
6. Do not pretend to have read parts of a paper that were not retrieved.
"""


def run_agent(question, history=None, max_steps=5):
    history = history or []

    steps = [
        {
            "tool": "search_documents",
            "args": {"query": question},
        }
    ]

    try:
        documents = search_documents(question)
    except Exception as exc:
        print("Document search error:", exc)
        return (
            "I couldn't search the uploaded research papers. "
            "Please check the embedding service, database connection, "
            "and backend logs.",
            [],
            steps,
        )

    if not documents:
        return (
            "I couldn't find relevant information about this "
            "in the uploaded papers.",
            [],
            steps,
        )

    passages = []
    sources = []
    seen_sources = set()

    for document in documents:
        content = document.get("content", "")
        source = document.get("source", "Unknown PDF")
        page = document.get("page", "Unknown")

        if not content:
            continue

        passages.append(
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Passage:\n{content}"
        )

        key = (source, page)
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append({"source": source, "page": page})

    if not passages:
        return "No usable research-paper passages were found.", [], steps

    evidence = "\n\n---\n\n".join(passages)

    messages = [{"role": "system", "content": SYSTEM}]

    for item in history[-4:]:
        role = (
            "assistant"
            if item.get("role") == "assistant"
            else "user"
        )
        content = item.get("content", "")
        if content:
            messages.append({"role": role, "content": content})

    messages.append({
        "role": "user",
        "content": (
            f"QUESTION:\n{question}\n\n"
            f"RETRIEVED RESEARCH-PAPER PASSAGES:\n{evidence}\n\n"
            "Answer using the passages above. Cite the PDF filename "
            "and page number for supported claims. If the passages "
            "do not support an answer, explicitly say so."
        ),
    })

    try:
        response = generate_response(messages=messages)
        answer = response["message"].get("content", "").strip()

        if not answer:
            answer = (
                "The passages were retrieved, but the language model "
                "returned an empty answer. Please try again."
            )

    except Exception as exc:
        print("Answer generation error:", exc)
        answer = (
            "I found relevant research-paper passages, but answer "
            "generation failed. Check your OpenRouter configuration "
            "and backend logs."
        )

    return answer, sources, steps
