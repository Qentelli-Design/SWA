"""Shared display labels and styles for the delivery views."""

from __future__ import annotations

from common.styles import inject_css

DELIVERY_DISPLAY_COLUMNS = {"Team": "Product", "Activity / Project": "Release", "Progress (Source)": "Progress"}


def render_delivery_styles() -> None:
    inject_css("delivery.css")
