"""Demonstrate temporal filtering: same query, different period scopes."""

from chronicle.retrieve import search

QUERY = "What is alienated labor and how does it shape human existence?"


def show(label: str, results: list[dict]) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print("=" * 70)
    for i, hit in enumerate(results, 1):
        print(f"\n  [{i}] {hit['work']} ({hit['year']}) — score {hit['score']:.3f}")
        snippet = hit["text"][:200].replace("\n", " ")
        print(f"      {snippet}...")


if __name__ == "__main__":
    print(f"\nQuery: {QUERY}")

    show("UNFILTERED (all periods)", search(QUERY, top_k=3))
    show("EARLY ONLY (1844)", search(QUERY, period="early", top_k=3))
    show("MATURE ONLY (1867)", search(QUERY, period="mature", top_k=3))
