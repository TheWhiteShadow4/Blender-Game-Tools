# Copyright (c) 2026 TheWhiteShadow

# pyright: reportMissingImports=false
import os

import bpy
from . import constants, exceptions, validation, properties
from . import export, merge, rigging, cleanup, baking
from .ui import panels_3d_view, panel_uv_editor


bl_info = {
    "name": "Game Tools",
    "author": "TheWhiteShadow",
    "version": (1, 4),
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