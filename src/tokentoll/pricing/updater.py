from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

_LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)

_CACHE_DIR = Path.home() / ".tokentoll"
_CACHE_FILE = _CACHE_DIR / "model_prices.json"
_CACHE_META = _CACHE_DIR / "cache_meta.json"


def update_bundled_pricing(quiet: bool = False) -> None:
    """Fetch latest pricing from LiteLLM and write to local cache."""
    if not quiet:
        print("Fetching latest pricing data from LiteLLM...", file=sys.stderr)

    try:
        req = urllib.request.Request(_LITELLM_URL, headers={"User-Agent": "tokentoll"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        if not quiet:
            print(f"Error fetching pricing data: {e}", file=sys.stderr)
        raise

    filtered: dict[str, dict] = {}
    for model, info in raw.items():
        if isinstance(info, dict) and info.get("input_cost_per_token") is not None:
            filtered[model] = {
                "input_cost_per_token": info.get("input_cost_per_token"),
                "output_cost_per_token": info.get("output_cost_per_token"),
                "cache_read_input_token_cost": info.get("cache_read_input_token_cost"),
                "max_input_tokens": info.get("max_input_tokens"),
                "max_output_tokens": info.get("max_output_tokens"),
                "mode": info.get("mode", "chat"),
            }

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2)

    with open(_CACHE_META, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.time()}, f)

    if not quiet:
        print(f"Updated pricing data: {len(filtered)} models cached to {_CACHE_FILE}")
