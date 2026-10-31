"""Small text helpers shared by data and delivery modules."""

from __future__ import annotations

import unicodedata


def person_key(name: str) -> str:
    """Order-insensitive key so 'Gundimeda Swetha' matches 'Swetha Gundimeda'."""
    return " ".join(sorted(name.casefold().split()))


def strip_format_characters(value: str) -> str:
    """Remove invisible Unicode format (Cf) characters that Excel cells can carry."""
    return "".join(character for character in value if unicodedata.category(character) != "Cf").strip()
