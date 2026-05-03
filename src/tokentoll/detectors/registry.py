from __future__ import annotations

from tokentoll.detectors.base import BaseDetector

_detectors: list[BaseDetector] | None = None


def get_all_detectors() -> list[BaseDetector]:
    global _detectors
    if _detectors is None:
        _detectors = _load_detectors()
    return _detectors


def _load_detectors() -> list[BaseDetector]:
    from tokentoll.detectors.anthropic_detector import AnthropicDetector
    from tokentoll.detectors.google_detector import GoogleDetector
    from tokentoll.detectors.langchain_detector import LangChainDetector
    from tokentoll.detectors.litellm_detector import LiteLLMDetector
    from tokentoll.detectors.openai_detector import OpenAIDetector

    return [
        OpenAIDetector(),
        AnthropicDetector(),
        GoogleDetector(),
        LiteLLMDetector(),
        LangChainDetector(),
    ]
