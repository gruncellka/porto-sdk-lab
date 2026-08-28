"""Minimal public Python SDK fixture."""

from enum import Enum


class PortoMark:
    """Purchased postage mark."""

    id: str


class ProviderClient:
    """Bound execution context for one postal provider."""

    def resolve(self, country_from: str) -> str:
        """Resolve a letter."""
        return country_from

    async def mark(self) -> PortoMark:
        """Purchase a mark."""
        return PortoMark()


class LetterType(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"


__all__ = ["ProviderClient", "PortoMark", "LetterType"]
