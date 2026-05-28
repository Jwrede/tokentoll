from __future__ import annotations

from tokentoll.detectors.js.base import BaseJsDetector

_detectors: list[BaseJsDetector] | None = None


def get_all_js_detectors() -> list[BaseJsDetector]:
    global _detectors
    if _detectors is None:
        _detectors = _load_js_detectors()
    return _detectors


def _load_js_detectors() -> list[BaseJsDetector]:
    from tokentoll.detectors.js.anthropic import AnthropicJsDetector
    from tokentoll.detectors.js.langchain import LangChainJsDetector
    from tokentoll.detectors.js.openai import OpenAIJsDetector
    from tokentoll.detectors.js.vercel import VercelAiSdkDetector

    return [
        OpenAIJsDetector(),
        AnthropicJsDetector(),
        VercelAiSdkDetector(),
        LangChainJsDetector(),
    ]
