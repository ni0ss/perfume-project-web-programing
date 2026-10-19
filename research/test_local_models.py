"""Offline smoke test for the two locally configured Ollama models.

Run from the repository root after Docker and Ollama have started:
    python research/test_local_models.py

This checks model availability and request/response connectivity only. It is
not a measure of model quality.
"""

from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


OLLAMA_URL = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434").rstrip("/")
MODELS = {
    "qwen2.5:3b": "MODEL_3B_OK",
    "qwen2.5:1.5b": "MODEL_1_5B_OK",
}
TIMEOUT = int(os.environ.get("OLLAMA_TEST_TIMEOUT_SECONDS", "180"))


def get_json(url: str, timeout: int = 10) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict, timeout: int) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        available = {item["name"] for item in get_json(f"{OLLAMA_URL}/api/tags").get("models", [])}
    except (OSError, URLError, TimeoutError, ValueError) as error:
        print(f"Could not reach Ollama at {OLLAMA_URL}: {error}", file=sys.stderr)
        return 1

    failed = False
    for model, expected in MODELS.items():
        if model not in available:
            print(json.dumps({"model": model, "ok": False, "error": "model is not installed"}))
            failed = True
            continue

        started = time.monotonic()
        try:
            result = post_json(
                f"{OLLAMA_URL}/api/chat",
                {
                    "model": model,
                    "messages": [{"role": "user", "content": f"Reply exactly: {expected}"}],
                    "stream": False,
                    "options": {"temperature": 0, "num_predict": 24},
                },
                TIMEOUT,
            )
            answer = result.get("message", {}).get("content", "").strip()
            passed = answer == expected and result.get("done") is True
            print(json.dumps({
                "model": model,
                "ok": passed,
                "expected": expected,
                "answer": answer,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            }, ensure_ascii=False))
            failed |= not passed
        except (OSError, URLError, TimeoutError, ValueError) as error:
            print(json.dumps({"model": model, "ok": False, "error": str(error)}))
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
