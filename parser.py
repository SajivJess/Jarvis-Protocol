"""Output parser for extracting patches from LLM agent responses.

Supports primary extraction via ``<patch>`` tags and fallback
extraction via Markdown triple-backtick code blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParseResult:
    """Result of parsing an agent's output.

    Attributes:
        reasoning: Extracted reasoning text, or None if not present.
        patch: Extracted patch code, or None if extraction failed.
        parse_method: Strategy that succeeded — one of
            ``"patch_tags"``, ``"markdown_fallback"``, or ``"failed"``.
    """

    reasoning: str | None
    patch: str | None
    parse_method: str  # "patch_tags", "markdown_fallback", "failed"


class OutputParser:
    """Parses structured LLM output to extract reasoning and patch code.

    Primary extraction uses ``<patch>...</patch>`` tags.
    Fallback extraction uses Markdown triple-backtick code blocks.
    """

    REASONING_RE = re.compile(r"<reasoning>(.*?)</reasoning>", re.DOTALL)
    PATCH_RE = re.compile(r"<patch>(.*?)</patch>", re.DOTALL)
    MARKDOWN_RE = re.compile(r"```(?:\w*\n)?(.*?)```", re.DOTALL)

    def parse(self, agent_output: str) -> ParseResult:
        """Parse the agent's output to extract reasoning and patch.

        Tries ``<patch>`` tags first, then falls back to Markdown code
        blocks. Returns a ``ParseResult`` indicating which strategy
        succeeded or if extraction failed entirely.

        Args:
            agent_output: The raw string output from the LLM agent.

        Returns:
            A ParseResult with the extracted reasoning, patch, and
            the method used for extraction.
        """
        reasoning_match = self.REASONING_RE.search(agent_output)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None

        # Primary: <patch> tags
        patch_match = self.PATCH_RE.search(agent_output)
        if patch_match:
            patch = patch_match.group(1).strip()
            if patch:
                return ParseResult(reasoning, patch, "patch_tags")

        # Fallback: Markdown code blocks
        md_match = self.MARKDOWN_RE.search(agent_output)
        if md_match:
            patch = md_match.group(1).strip()
            if patch:
                return ParseResult(reasoning, patch, "markdown_fallback")

        return ParseResult(reasoning, None, "failed")
