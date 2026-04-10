"""Smoke tests against the live Railway deployment.

Usage:
    CHRONICLE_API_KEY=<key> uv run python scripts/smoke_test.py
    CHRONICLE_API_KEY=<key> BASE_URL=http://localhost:8000 uv run python scripts/smoke_test.py

Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.getenv("BASE_URL", "https://chronicle-production-7df6.up.railway.app").rstrip("/")
API_KEY = os.getenv("CHRONICLE_API_KEY")

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}{': ' + detail if detail else ''}")
        failures.append(name)


def test_health() -> None:
    print("\n[GET /health]")
    r = httpx.get(f"{BASE_URL}/health", timeout=10)
    check("status 200", r.status_code == 200, str(r.status_code))
    check('body == {"status": "ok"}', r.json() == {"status": "ok"}, r.text)


def test_root() -> None:
    print("\n[GET /]")
    r = httpx.get(f"{BASE_URL}/", timeout=10)
    check("status 200", r.status_code == 200, str(r.status_code))
    data = r.json()
    check("name == Chronicle", data.get("name") == "Chronicle", str(data))
    check("version present", "version" in data)
    check("description present", "description" in data)


def test_query_requires_auth() -> None:
    print("\n[POST /query — no key]")
    r = httpx.post(f"{BASE_URL}/query", json={"query": "test"}, timeout=10)
    check("status 401 without key", r.status_code == 401, str(r.status_code))


def test_query_rejects_bad_key() -> None:
    print("\n[POST /query — wrong key]")
    r = httpx.post(
        f"{BASE_URL}/query",
        json={"query": "test"},
        headers={"X-API-Key": "not-a-real-key"},
        timeout=10,
    )
    check("status 401 with wrong key", r.status_code == 401, str(r.status_code))


def test_query_end_to_end() -> None:
    print("\n[POST /query — full pipeline]")
    if not API_KEY:
        print("  ⚠  CHRONICLE_API_KEY not set — skipping live query test")
        return

    r = httpx.post(
        f"{BASE_URL}/query",
        json={"query": "How does Marx describe alienated labour?", "period": "early", "top_k": 3},
        headers={"X-API-Key": API_KEY},
        timeout=60,
    )
    check("status 200", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        data = r.json()
        check("answer is non-empty string", isinstance(data.get("answer"), str) and len(data["answer"]) > 0)
        check("citations is a list", isinstance(data.get("citations"), list))
        check("citations non-empty", len(data.get("citations", [])) > 0)
        check("chunks_used is int", isinstance(data.get("chunks_used"), int))
        check("chunks_used == len(citations)", data.get("chunks_used") == len(data.get("citations", [])))


def main() -> None:
    print(f"Smoke testing: {BASE_URL}")
    test_health()
    test_root()
    test_query_requires_auth()
    test_query_rejects_bad_key()
    test_query_end_to_end()

    print(f"\n{'='*50}")
    if failures:
        print(f"  {FAIL} {len(failures)} check(s) failed: {', '.join(failures)}")
        sys.exit(1)
    else:
        print(f"  {PASS} All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
