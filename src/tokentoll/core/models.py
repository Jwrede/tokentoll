from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CallType(Enum):
    CHAT_COMPLETION = "chat_completion"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    RESPONSES = "responses"
    TRANSCRIPTION = "transcription"
    SPEECH = "speech"


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class LLMCall:
    """A single detected LLM API call site in source code."""

    file_path: str
    line_number: int
    sdk: str
    call_type: CallType
    model: str | None
    model_is_literal: bool
    max_tokens: int | None
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    raw_expression: str = ""


@dataclass
class ModelPricing:
    """Pricing info for a single model."""

    model_name: str
    input_cost_per_token: float | None
    output_cost_per_token: float | None
    cache_read_cost_per_token: float | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    mode: str = "chat"


@dataclass
class CostEstimate:
    """Cost estimate for a single LLM call site."""

    call: LLMCall
    pricing: ModelPricing | None
    estimated_cost_per_call: float | None = None
    monthly_estimate: float | None = None
    model_found: bool = False
    used_default_model: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class CallDiff:
    """A single change to an LLM call site."""

    change_type: ChangeType
    old_call: LLMCall | None = None
    new_call: LLMCall | None = None
    old_estimate: CostEstimate | None = None
    new_estimate: CostEstimate | None = None
    cost_delta_per_call: float | None = None
    monthly_delta: float | None = None


@dataclass
class DiffReport:
    """Complete diff report for a PR or commit range."""

    base_ref: str
    head_ref: str
    call_diffs: list[CallDiff]
    total_monthly_delta: float | None = None
    total_calls_added: int = 0
    total_calls_removed: int = 0
    total_calls_modified: int = 0
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class ScanReport:
    """Report from scanning files for LLM calls."""

    estimates: list[CostEstimate]
    total_monthly_estimate: float | None = None
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
