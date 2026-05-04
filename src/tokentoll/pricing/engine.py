from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from tokentoll.core.models import CostEstimate, LLMCall, ModelPricing

_CACHE_DIR = Path.home() / ".tokentoll"
_CACHE_FILE = _CACHE_DIR / "model_prices.json"
_CACHE_META = _CACHE_DIR / "cache_meta.json"
_BUNDLED_FILE = Path(__file__).parent / "data" / "model_prices.json"

_WARN_AGE_DAYS = 7
_ERROR_AGE_DAYS = 30

_DEFAULT_INPUT_TOKENS = 500
_DEFAULT_OUTPUT_RATIO = 0.25

_SDK_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "google_genai": "gemini-2.0-flash",
    "litellm": "gpt-4o",
    "langchain": "gpt-4o",
    "zai": "zai/glm-4.6",
}

_DATE_SUFFIX_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")
_DATE_SUFFIX_LONG_RE = re.compile(r"-\d{8}$")


class PricingEngine:
    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._warnings: list[str] = []
        self._load()

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def _load(self) -> None:
        cache_age_days = self._get_cache_age_days()

        if _CACHE_FILE.exists() and cache_age_days is not None:
            if cache_age_days > _ERROR_AGE_DAYS:
                print(
                    f"Error: pricing data is {cache_age_days} days old and likely inaccurate. "
                    "Run 'tokentoll update' to refresh.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if cache_age_days > _WARN_AGE_DAYS:
                self._warnings.append(
                    f"Pricing data is {cache_age_days} days old. Run 'tokentoll update' to refresh."
                )
            self._data = self._read_json(_CACHE_FILE)
            return

        if not _CACHE_FILE.exists():
            if self._try_fetch_and_cache():
                self._data = self._read_json(_CACHE_FILE)
                return

        if _BUNDLED_FILE.exists():
            self._warnings.append(
                "Using bundled pricing data (may be outdated). "
                "Run 'tokentoll update' to fetch latest prices."
            )
            self._data = self._read_json(_BUNDLED_FILE)
            return

        print(
            "Error: no pricing data available. Run 'tokentoll update' to fetch prices.",
            file=sys.stderr,
        )
        sys.exit(1)

    def _get_cache_age_days(self) -> int | None:
        if not _CACHE_META.exists():
            return None
        try:
            meta = self._read_json(_CACHE_META)
            ts = meta.get("fetched_at", 0)
            return int((time.time() - ts) / 86400)
        except (ValueError, KeyError):
            return None

    def _try_fetch_and_cache(self) -> bool:
        try:
            from tokentoll.pricing.updater import update_bundled_pricing

            update_bundled_pricing(quiet=True)
            return _CACHE_FILE.exists()
        except Exception:
            return False

    @staticmethod
    def _read_json(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def lookup(self, model_name: str, sdk: str | None = None) -> ModelPricing | None:
        entry = self._try_resolve(model_name, sdk)
        if entry is None:
            return None
        return ModelPricing(
            model_name=entry[0],
            input_cost_per_token=entry[1].get("input_cost_per_token"),
            output_cost_per_token=entry[1].get("output_cost_per_token"),
            cache_read_cost_per_token=entry[1].get("cache_read_input_token_cost"),
            max_input_tokens=entry[1].get("max_input_tokens"),
            max_output_tokens=entry[1].get("max_output_tokens"),
            mode=entry[1].get("mode", "chat"),
        )

    def _try_resolve(self, name: str, sdk: str | None) -> tuple[str, dict] | None:
        if name in self._data:
            return (name, self._data[name])

        lower = name.lower()
        for key, val in self._data.items():
            if key.lower() == lower:
                return (key, val)

        if "/" not in name and sdk:
            prefixed = f"{sdk}/{name}"
            for key, val in self._data.items():
                if key.lower() == prefixed.lower():
                    return (key, val)

        for key, val in self._data.items():
            if "/" in key and key.split("/", 1)[1].lower() == lower:
                return (key, val)

        # Strip provider prefix and try again (e.g., "bedrock/us.anthropic.X" -> "us.anthropic.X")
        if "/" in name:
            after_slash = name.split("/", 1)[1]
            result = self._try_resolve(after_slash, sdk)
            if result:
                return result

        # Strip region prefix (e.g., "us.anthropic.X" -> "anthropic.X")
        _REGION_PREFIXES = ("us.", "eu.", "apac.", "ap.")
        lower_name = name.lower()
        for prefix in _REGION_PREFIXES:
            if lower_name.startswith(prefix):
                result = self._try_resolve(name[len(prefix) :], sdk)
                if result:
                    return result

        stripped = _DATE_SUFFIX_RE.sub("", name)
        if stripped != name:
            result = self._try_resolve(stripped, sdk)
            if result:
                return result

        stripped = _DATE_SUFFIX_LONG_RE.sub("", name)
        if stripped != name:
            return self._try_resolve(stripped, sdk)

        return None

    def estimate(
        self,
        call: LLMCall,
        calls_per_month: int = 1000,
        default_model: str | None = None,
        default_models: dict[str, str] | None = None,
        skip_dynamic_models: bool = False,
    ) -> CostEstimate:
        notes: list[str] = []

        if not call.model:
            if skip_dynamic_models:
                return CostEstimate(
                    call=call,
                    pricing=None,
                    model_found=False,
                    notes=["Dynamic model, skipped per config (skip_dynamic_models)"],
                )

            resolved_default = None
            source = ""
            if default_models and call.sdk in default_models:
                resolved_default = default_models[call.sdk]
                source = "config"
            elif default_model:
                resolved_default = default_model
                source = "config"
            elif call.sdk in _SDK_DEFAULT_MODELS:
                resolved_default = _SDK_DEFAULT_MODELS[call.sdk]
                source = "built-in"

            if resolved_default:
                pricing = self.lookup(resolved_default, sdk=call.sdk)
                if pricing is None:
                    return CostEstimate(
                        call=call,
                        pricing=None,
                        model_found=False,
                        notes=[
                            f"Model is dynamic, default '{resolved_default}' "
                            "not found in pricing data"
                        ],
                    )
                notes.append(f"Model is dynamic, using {source} default '{resolved_default}'")
                return self._compute(call, pricing, notes, calls_per_month, resolved_default)
            return CostEstimate(
                call=call,
                pricing=None,
                model_found=False,
                notes=["Model is dynamic, cannot estimate cost"],
            )

        pricing = self.lookup(call.model, sdk=call.sdk)
        if pricing is None:
            self._warnings.append(
                f"Unknown model '{call.model}' at {call.file_path}:{call.line_number} "
                "-- not in pricing database. Run 'tokentoll update' or check the model name."
            )
            return CostEstimate(
                call=call,
                pricing=None,
                model_found=False,
                notes=[f"Unknown model '{call.model}'"],
            )

        return self._compute(call, pricing, notes, calls_per_month)

    def _compute(
        self,
        call: LLMCall,
        pricing: ModelPricing,
        notes: list[str],
        calls_per_month: int,
        used_default: str | None = None,
    ) -> CostEstimate:
        input_tokens = call.estimated_input_tokens
        if input_tokens is None:
            input_tokens = _DEFAULT_INPUT_TOKENS
            notes.append(f"Assumed {_DEFAULT_INPUT_TOKENS} input tokens")

        output_tokens = call.estimated_output_tokens
        if output_tokens is None:
            if pricing.max_output_tokens:
                output_tokens = int(pricing.max_output_tokens * _DEFAULT_OUTPUT_RATIO)
            else:
                output_tokens = 500
            notes.append(f"Assumed {output_tokens} output tokens")

        input_cost = (pricing.input_cost_per_token or 0) * input_tokens
        output_cost = (pricing.output_cost_per_token or 0) * output_tokens
        cost_per_call = input_cost + output_cost
        monthly = cost_per_call * calls_per_month

        return CostEstimate(
            call=call,
            pricing=pricing,
            estimated_cost_per_call=cost_per_call,
            monthly_estimate=monthly,
            model_found=True,
            used_default_model=used_default,
            notes=notes,
        )
