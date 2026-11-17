"""Small text helpers shared by data and delivery modules."""

from __future__ import annotations

def display_portfolio_name(value: str) -> str:
    """Display the workbook's CCC portfolio as C&C without changing its source value."""
    return "C&C" if value.strip().casefold() == "ccc" else value


def person_key(name: str) -> str:
    """Order-insensitive key so 'Gundimeda Swetha' matches 'Swetha Gundimeda'."""
    return " ".join(sorted(name.casefold().split()))
