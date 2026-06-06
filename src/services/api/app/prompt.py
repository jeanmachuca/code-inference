"""
Prompt management: filter, tag, compact, and basic PII masking before inference.
See docs/adr/0005-prompt-management-layer.md — this is a minimal first implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Chile RUT-style (loose): 12.345.678-9 or 12345678-9
_RUT_RE = re.compile(
    r"\b\d{1,2}\.?\d{3}\.?\d{3}\s*-\s*[\dkK]\b",
    re.UNICODE,
)

_TRUNC_SUFFIX = "\n…[truncated]"


@dataclass
class PromptResult:
    messages: list[dict[str, Any]]
    """Messages ready for the inference server."""
    tags: dict[str, str] = field(default_factory=dict)
    """Metadata for logging (no raw PHI by default)."""
    truncated: bool = False
    pii_masked: bool = False


def _apply_char_cap(messages: list[dict[str, Any]], max_chars: int) -> tuple[list[dict[str, Any]], bool]:
    """
    Ensure total character count of string contents does not exceed max_chars
    by truncating the last user message only.
    """
    out = [dict(m) for m in messages]
    total = sum(len(m["content"]) for m in out if isinstance(m.get("content"), str))
    if total <= max_chars:
        return out, False

    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") != "user" or not isinstance(out[i].get("content"), str):
            continue
        other = sum(
            len(m["content"])
            for j, m in enumerate(out)
            if isinstance(m.get("content"), str) and j != i
        )
        room = max_chars - other
        c = out[i]["content"]
        if room <= 0:
            out[i]["content"] = ""
            return out, True
        if room <= len(_TRUNC_SUFFIX):
            out[i]["content"] = c[:room]
            return out, True
        max_body = room - len(_TRUNC_SUFFIX)
        if len(c) > max_body:
            out[i]["content"] = c[:max_body] + _TRUNC_SUFFIX
        return out, True

    return out, True


def _mask_rut(text: str) -> tuple[str, bool]:
    masked = _RUT_RE.sub("[RUT]", text)
    return masked, masked != text


def process_messages(
    messages: list[dict[str, Any]],
    *,
    max_chars: int,
    intent_header: str | None,
) -> PromptResult:
    tags: dict[str, str] = {}
    if intent_header:
        tags["intent"] = intent_header[:128]

    msgs = [dict(m) for m in messages]
    pii_masked = False
    for m in msgs:
        if isinstance(m.get("content"), str):
            new_c, did = _mask_rut(m["content"])
            if did:
                m["content"] = new_c
                pii_masked = True

    msgs, truncated = _apply_char_cap(msgs, max_chars)

    return PromptResult(
        messages=msgs,
        tags=tags,
        truncated=truncated,
        pii_masked=pii_masked,
    )
