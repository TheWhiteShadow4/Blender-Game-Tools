# Copyright (c) 2026 TheWhiteShadow

# pyright: reportMissingImports=false
import ast
import os

import bpy
from . import constants, exceptions, validation, properties
from . import export, merge, rigging, cleanup, baking
from .ui import panels_3d_view, panel_uv_editor


def load_addon_version():
    """
    Liest die Versionsnummer aus blender_manifest.toml (z. B. "1.4.0")
    und liefert sie als (major, minor) Tuple für bl_info.

    blender_manifest.toml ist die einzige Versionsquelle:
      - Das Extension-System nutzt sie direkt (blender_manifest.toml:version)
      - Dieses Addon liest sie hier für die klassische Addon-API (bl_info)

    Wenn die Datei nicht existiert oder nicht parsbar ist, wird (1, 0)
    als Fallback verwendet, damit das Addon trotzdem lädt.
    """
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "blender_manifest.toml")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("version"):
                    # Zeile hat die Form: version = "1.4.0"
                    # Wir parsen das Literal rechts von "=" als Python-Literal,
                    # weil TOML-Strings hier mit doppelten Anführungszeichen
                    # angegeben sind und so gleichzeitig valide Python-Strings.
                    value = line.split("=", 1)[1].strip()
                    version_str = ast.literal_eval(value)
                    parts = version_str.split(".")
                    major = int(parts[0])
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    return (major, minor)
    except (OSError, ValueError, IndexError, SyntaxError):
        pass
    return (1, 0)


bl_info = {
    "name": "Game Tools",
    "author": "TheWhiteShadow",
    "version": load_addon_version(),
    "blender": (5, 2, 0),
    "description": "Game Helper Tools",
    "warning": "",
    "wiki_url": "",
    "category": "System"
}

if "bpy" in locals():
    import importlib
    importlib.reload(constants)
    importlib.reload(exceptions)
    importlib.reload(validation)
    importlib.reload(properties)
    importlib.reload(export)
    importlib.reload(merge)
    importlib.reload(rigging)
    importlib.reload(cleanup)
    importlib.reload(baking)
    importlib.reload(panels_3d_view)
    importlib.reload(panel_uv_editor)

def validate_and_refresh_ui():
    """
    Performs the validation and UI update.
    Called from a handler and on registration via a timer.
    Returns None so the timer only runs once.
    """
    if bpy.context and bpy.context.scene:
        props = bpy.context.scene.unity_tool_properties
        if props:
            properties.update_project_path(props, bpy.context)
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            region.tag_redraw()
    return None

def on_load_handler(dummy):
    """Wrapper to call the validation from the load_post handler."""
    # The timer is more reliable for startup
    if not bpy.app.timers.is_registered(validate_and_refresh_ui):
        bpy.app.timers.register(validate_and_refresh_ui)

def register():
	properties.register()
	export.register()
	merge.register()
	rigging.register()
	cleanup.register()
	baking.register()
	panels_3d_view.register()
	panel_uv_editor.register()
	
	bpy.app.handlers.load_post.append(on_load_handler)
	
	# Schedule the validation to run once, very soon after registration,
    # when the context is available.
	if not bpy.app.timers.is_registered(validate_and_refresh_ui):
		bpy.app.timers.register(validate_and_refresh_ui)


def unregister():
	panel_uv_editor.unregister()
	panels_3d_view.unregister()
	baking.unregister()
	cleanup.unregister()
	rigging.unregister()
	merge.unregister()
	export.unregister()
	properties.unregister()
	
	if on_load_handler in bpy.app.handlers.load_post:
		bpy.app.handlers.load_post.remove(on_load_handler)
	
	if bpy.app.timers.is_registered(validate_and_refresh_ui):
		bpy.app.timers.unregister(validate_and_refresh_ui)


if __name__ == "__main__":
	register()