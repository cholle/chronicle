"""End-to-end Q&A demo: ingest → retrieve → generate with citations."""

from chronicle.generate import answer

QUERIES = [
    {
        "query": "What does Marx mean by alienated labor?",
        "period": "early",
        "label": "EARLY MARX (1844)",
    },
    {
        "query": "How does Marx describe the labor process under capitalism?",
        "period": "mature",
        "label": "MATURE MARX (1867)",
    },
    {
        "query": "What is Marx's critique of equal rights and bourgeois law?",
        "period": "late",
        "label": "LATE MARX (1875)",
    },
]


def show(item: dict) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {item['label']}")
    print(f"  Q: {item['query']}")
    print("=" * 72)

    result = answer(item["query"], period=item["period"], top_k=4)

    print(f"\n{result['answer']}\n")
    print(f"--- Sources ({result['chunks_used']} passages) ---")
    for i, c in enumerate(result["citations"], 1):
        print(f"  [{i}] {c['work']} ({c['year']}) — score {c['score']:.3f}")


if __name__ == "__main__":
    for item in QUERIES:
        show(item)
