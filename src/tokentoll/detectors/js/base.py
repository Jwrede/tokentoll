"""Base class for JavaScript/TypeScript LLM call detectors.

Detectors operate on a tree-sitter Node (the source file root) plus the
raw source bytes. The variables dict carries same-file constant
propagation results from js_scanner.build_variable_map.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tokentoll.core.models import LLMCall

if TYPE_CHECKING:
    from tree_sitter import Node


class BaseJsDetector(ABC):
    @abstractmethod
    def sdk_name(self) -> str: ...

    @abstractmethod
    def can_handle(self, root: Node, source: str) -> bool:
        """Quick check: does this file plausibly use the SDK?

        `source` is the raw string. Implementations typically substring-check
        for SDK package names; the root node is available for cases where
        substring is too coarse.
        """

    @abstractmethod
    def detect(
        self,
        root: Node,
        file_path: str,
        source: bytes,
        variables: dict[str, str | int],
    ) -> list[LLMCall]:
        """Walk the tree and return all detected LLM API calls."""
