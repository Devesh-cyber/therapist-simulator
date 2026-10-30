"""Diagnose your Grok setup:  python -m app.check_grok

Checks the key, lists the models your key can use, and sends one tiny JSON request
with the configured GROK_MODEL, printing xAI's exact error if anything fails."""
import json
import sys

import httpx

from .config import get_settings


def main() -> int:
    s = get_settings()
    base = s.grok_base_url.rstrip("/")
    key = s.grok_api_key.strip()
    print(f"Base URL : {base}\nModel    : {s.grok_model!r}\nKey      : {'set (' + key[:6] + '…)' if key else 'MISSING'}")
    if not key:
        print("\nSet GROK_API_KEY in backend/.env"); return 1
    if key != s.grok_api_key:
        print("\nWarning: GROK_API_KEY has leading/trailing spaces or a newline. Remove them.")
    h = {"Authorization": f"Bearer {key}"}

    r = httpx.get(f"{base}/models", headers=h, timeout=30)
    print(f"\nGET /models -> {r.status_code}")
    models = []
    if r.status_code == 200:
        models = [m.get("id") for m in r.json().get("data", [])]
        print("Models available to this key:\n  " + "\n  ".join(models))
        if s.grok_model not in models:
            print(f"\n!! GROK_MODEL={s.grok_model!r} is not in that list. Set GROK_MODEL to one of the ids above.")
    else:
        print(r.text[:800])

    body = {"model": s.grok_model, "max_tokens": 200, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": "Reply only with JSON."},
                         {"role": "user", "content": 'Return {"ok": true}'}]}
    r = httpx.post(f"{base}/chat/completions", headers=h, json=body, timeout=60)
    print(f"\nPOST /chat/completions (json mode) -> {r.status_code}")
    print(r.text[:1200] if r.status_code != 200 else json.dumps(r.json()["choices"][0]["message"], indent=1)[:600])
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
