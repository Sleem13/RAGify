"""Run a small source/page retrieval evaluation against a running RAGify API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests


CASES_PATH = Path(__file__).with_name("retrieval_cases.json")
BASE_URL = os.getenv("RAGIFY_BACKEND_URL", "http://127.0.0.1:9999").rstrip("/")
API_KEY = os.getenv("RAGIFY_API_KEY", "")


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    headers = {"X-Api-Key": API_KEY} if API_KEY else {}
    passed = 0
    for case in cases:
        response = requests.post(
            f"{BASE_URL}/chat",
            data={"message": case["question"], "history": "[]"},
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        sources = payload.get("sources", [])
        source_hit = case["expected_source"] is None or any(
            source.get("metadata", {}).get("source") == case["expected_source"]
            for source in sources
        )
        page_hit = not case["expected_pages"] or any(
            source.get("metadata", {}).get("page") in case["expected_pages"]
            for source in sources
        )
        answer_hit = bool(payload.get("context_found")) is bool(case["must_answer"])
        ok = source_hit and page_hit and answer_hit
        passed += int(ok)
        print(f"{'PASS' if ok else 'FAIL'}: {case['question']}")
    print(f"\n{passed}/{len(cases)} cases passed")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
