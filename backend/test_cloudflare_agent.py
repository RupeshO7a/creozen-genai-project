
from agent import run_agent


def main():
    question = (
        "What is self-attention in the Transformer architecture, "
        "and how does it work?"
    )

    print("Testing the full Creozen GenAI agent...")
    print("Question:", question)

    answer, sources, steps = run_agent(question)

    print("\n--- AI ANSWER ---")
    print(answer)

    print("\n--- SOURCES ---")
    for source in sources:
        print(f"{source['source']} — page {source['page']}")

    print("\n--- EXECUTION ---")
    print(steps)


if __name__ == "__main__":
    main()
