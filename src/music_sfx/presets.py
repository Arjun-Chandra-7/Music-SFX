"""Curated processing presets and parameter metadata."""

from __future__ import annotations

from copy import deepcopy

PARAMETERS = {
    "low_gain": {"label": "Low", "unit": "dB", "min": -12.0, "max": 12.0, "step": 0.5},
    "presence": {"label": "Presence", "unit": "dB", "min": -12.0, "max": 12.0, "step": 0.5},
    "air": {"label": "Air", "unit": "dB", "min": -12.0, "max": 12.0, "step": 0.5},
    "compression": {"label": "Control", "unit": "%", "min": 0.0, "max": 100.0, "step": 1.0},
    "space": {"label": "Space", "unit": "%", "min": 0.0, "max": 100.0, "step": 1.0},
    "width": {"label": "Width", "unit": "%", "min": 0.0, "max": 200.0, "step": 1.0},
    "wet": {"label": "Wet", "unit": "%", "min": 0.0, "max": 100.0, "step": 1.0},
    "output_gain": {"label": "Output", "unit": "dB", "min": -18.0, "max": 6.0, "step": 0.5},
}

_PRESETS = {
    "broadcast_voice": {
        "name": "Broadcast Voice",
        "category": "Voice & Podcast",
        "description": "Tight, intelligible narration with controlled dynamics and a clean noise floor.",
        "values": {"low_gain": -1, "presence": 3, "air": 2, "compression": 62, "space": 0, "width": 100, "wet": 100, "output_gain": -1},
    },
    "cinematic_trailer": {
        "name": "Cinematic Trailer",
        "category": "Music",
        "description": "Weight, polish and controlled width for high-impact cinematic beds.",
        "values": {"low_gain": 4, "presence": 1.5, "air": 2, "compression": 48, "space": 18, "width": 125, "wet": 100, "output_gain": -1},
    },
    "shorts_punch": {
        "name": "Shorts Punch",
        "category": "Social",
        "description": "Fast, bright and compact processing designed to translate on phone speakers.",
        "values": {"low_gain": 2, "presence": 4, "air": 2.5, "compression": 72, "space": 3, "width": 108, "wet": 100, "output_gain": -1},
    },
    "clean_master": {
        "name": "Clean Master",
        "category": "Mastering",
        "description": "Subtle tonal balance and gentle glue without changing the source character.",
        "values": {"low_gain": 0.5, "presence": 0.5, "air": 1, "compression": 30, "space": 0, "width": 105, "wet": 100, "output_gain": -1},
    },
    "dream_space": {
        "name": "Dream Space",
        "category": "Creative FX",
        "description": "Wide ambient echoes for transitions, intros and atmospheric sound design.",
        "values": {"low_gain": -2, "presence": -1, "air": 4, "compression": 18, "space": 72, "width": 155, "wet": 76, "output_gain": -2},
    },
    "vintage_radio": {
        "name": "Vintage Radio",
        "category": "Creative FX",
        "description": "Band-limited, compressed radio tone for narrative inserts and transitions.",
        "values": {"low_gain": -10, "presence": 6, "air": -10, "compression": 78, "space": 4, "width": 35, "wet": 100, "output_gain": -2},
        "special": "radio",
    },
    "transparent": {
        "name": "Transparent",
        "category": "Utility",
        "description": "Unity settings for precise manual work.",
        "values": {"low_gain": 0, "presence": 0, "air": 0, "compression": 0, "space": 0, "width": 100, "wet": 100, "output_gain": 0},
    },
}


def presets() -> dict:
    return deepcopy(_PRESETS)


def preset(name: str) -> dict:
    if name not in _PRESETS:
        raise ValueError(f"Unknown preset: {name}")
    return deepcopy(_PRESETS[name])

