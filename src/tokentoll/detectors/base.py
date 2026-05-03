from __future__ import annotations

import ast
from abc import ABC, abstractmethod

from tokentoll.core.models import LLMCall


class BaseDetector(ABC):
    """Base class for LLM SDK call detectors."""

    @abstractmethod
    def sdk_name(self) -> str: ...

    @abstractmethod
    def can_handle(self, tree: ast.Module, source: str) -> bool:
        """Quick check: does this file import the relevant SDK?"""
        ...

    @abstractmethod
    def detect(self, tree: ast.Module, file_path: str) -> list[LLMCall]:
        """Walk the AST and return all detected LLM API calls."""
        ...
