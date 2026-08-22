# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Zentrale Konstanten für Unity Tools Addon."""

# ===== File Paths (mehrfach verwendet) =====
DUMMY_IMAGE_NAME = "__DummyImage"  # Verwendet in baker.py und bake_utils.py
DEFAULT_EXPORT_PATH = "Assets/FBX"
TEXTURE_EXPORT_DIR = "Textures"

# ===== Export Settings (mehrfach verwendet) =====
UNITY_FBX_SCALE = 0.01
UNITY_AXIS_FORWARD = 'Z'
UNITY_AXIS_UP = 'Y'
GODOT_FBX_SCALE = 1.0
GODOT_AXIS_FORWARD = '-Z'
GODOT_AXIS_UP = 'Y'

# ===== Material Import =====
# Beim Unity-Import projektweit nach vorhandenen Materialien mit gleichem Namen suchen,
# bevor ein neues Material angelegt wird. (Flag wird in die .imp.json geschrieben.)
SEARCH_PROJECT_MATERIALS = True

# Textur-Einstellungen übertragen (Interpolation/Filter und Wrap-Mode).
# Der Farbraum (sRGB/Non-Color) wird unabhängig davon immer übertragen.
TRANSFER_TEXTURE_SETTINGS = True

# Bestehende Texturen in Unity überschreiben (Blender als "Wahrheit") oder
# manuelle Änderungen in Unity respektieren. (Flag wird in die .imp.json geschrieben.)
OVERWRITE_TEXTURE_SETTINGS = True

# ===== Tolerances =====
ROTATION_TOLERANCE = 0.0001
GAMMA_CORRECTION_FACTOR = 2.2

