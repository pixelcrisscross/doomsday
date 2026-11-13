"""
RoadSentinel - Device Geolocation Picker Component
Module: location_picker.py

Provides a minimal, secure browser geolocation interface:
  - Clean 'Use My Current Location' button
  - Captures device latitude & longitude using the HTML5 Geolocation API on user click
  - Displays confirmation badge: 'Location captured', Latitude, Longitude, and '[ Remove ]' option
  - Handles permission denied, GPS unavailable, loading state, and retry logic
  - Returns coordinates dictionary or None
"""

from pathlib import Path
from typing import Optional, Dict, Any
import streamlit.components.v1 as components

_COMPONENT_PATH = Path(__file__).parent / "components" / "location_picker"
_location_picker_func = components.declare_component(
    "location_picker",
    path=str(_COMPONENT_PATH.resolve())
)


def render_location_picker(
    key: str,
    saved_location: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Renders the browser Geolocation picker widget.

    Returns:
        Dict with 'latitude', 'longitude', 'status' ('captured') or None.
    """
    val = _location_picker_func(
        key=key,
        saved_location=saved_location,
        default=saved_location
    )
    if isinstance(val, dict) and val.get("status") == "captured":
        try:
            lat = float(val.get("latitude"))
            lon = float(val.get("longitude"))
            return {
                "latitude": lat,
                "longitude": lon,
                "accuracy_m": val.get("accuracy_m"),
                "status": "captured"
            }
        except (TypeError, ValueError):
            return None
    return None
