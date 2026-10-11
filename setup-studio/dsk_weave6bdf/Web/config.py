# SPDX-License-Identifier: MIT
"""Dusklight's settings (config.json) as the Setup Studio sets them.

Only the settings the user chooses in the Setup Studio are written; everything else in an existing
config.json (their own changes in the game's menus) stays as it is. A new installation starts
from the port's console preset (src/dusklight/ps4/default-config.json).
"""
from __future__ import annotations

import dataclasses
import json
from typing import Optional

# The port's console preset (ps4/default-config.json), for a first installation.
PRESET = {
    "game.language": 0,
    "game.enableFrameInterpolation": 0,
    "video.maxFrameRate": 60,
    "game.enableFpsOverlay": True,
    "game.enableControllerToasts": False,
    "game.enableTextureReplacements": False,
    "game.internalResolutionScale": 0,
    "backend.skipPreLaunchUI": False,
    "backend.checkForUpdates": False,
    "backend.checkForModUpdates": False,
    "video.uiScale": 100,
    "game.fastTransitions": True,
}

TWILIGHT_HD_ENABLED = "mod.org_twilight_hd__hud.enabled"


@dataclasses.dataclass
class Choices:
    language: Optional[int] = None          # dusk::GameLanguage (disc.LANG_*)
    textures: Optional[bool] = None         # HD texture pack on/off
    twilight_hd: Optional[bool] = None      # Wii U-style HUD on/off
    fast_transitions: Optional[bool] = None

    def settings(self) -> dict:
        out = {}
        if self.language is not None:
            out["game.language"] = self.language
        if self.textures is not None:
            out["game.enableTextureReplacements"] = self.textures
        if self.twilight_hd is not None:
            out[TWILIGHT_HD_ENABLED] = self.twilight_hd
        if self.fast_transitions is not None:
            out["game.fastTransitions"] = self.fast_transitions
        return out


def merged(existing: Optional[bytes], choices: Choices) -> bytes:
    """config.json content with the choices applied over the existing file (or the preset)."""
    if existing:
        try:
            config = json.loads(existing.decode("utf-8"))
            if not isinstance(config, dict):
                raise ValueError
        except ValueError:
            config = dict(PRESET)  # unreadable: start from the preset (the old file is backed up)
    else:
        config = dict(PRESET)
    config.update(choices.settings())
    return (json.dumps(config, indent=4, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
