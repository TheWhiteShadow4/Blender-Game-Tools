# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Export-Feature: Quick Export (FBX + Material-JSON) an Unity/Godot."""

import bpy
import os
import shutil
from .. import constants
from ..properties import detect_game_engine
from . import material_export


class UNITY_OT_quick_export(bpy.types.Operator):
    """Quick export selected object to Unity project"""
    bl_idname = "export.quick_export"
    bl_label = "Quick Export"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        unity_props = scene.unity_tool_properties

        project_path = unity_props.engine_project_path
        engine = detect_game_engine(project_path)

        if engine is None:
            self.report({'ERROR'}, "Projektpfad scheint weder ein Unity- noch ein Godot-Projekt zu sein.")
            return {'CANCELLED'}

        # --- Import-Script Handling (Unity) ----------------------
        # Hinweis: Der C#-Editor-Script liegt im Addon-Root (BlenderAssetPostprocessor.cs),
        # weil er für beide Engines genutzt werden könnte (z.Z. nur Unity aktiv).
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            if engine == 'UNITY':
                editor_script_dir = os.path.join(project_path, "Assets", "Editor")
                os.makedirs(editor_script_dir, exist_ok=True)
                src = os.path.join(addon_dir, "BlenderAssetPostprocessor.cs")
                dst = os.path.join(editor_script_dir, "BlenderAssetPostprocessor.cs")
                shutil.copy(src, dst)
            # Godot-Plugin-Kopie ist aktuell deaktiviert (Feature noch unfertig).
        except Exception as e:
            self.report({'ERROR'}, f"Could not copy import script(s): {e}")
            return {'CANCELLED'}

        # --- FBX Export ---
        export_path = os.path.join(unity_props.engine_project_path, unity_props.export_path)
        try:
            os.makedirs(export_path, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Could not create export directory: {e}")
            return {'CANCELLED'}

        active_obj = context.active_object
        filepath = os.path.join(export_path, f"{active_obj.name}.fbx")

        if engine == 'UNITY':
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                global_scale=constants.UNITY_FBX_SCALE,
                axis_forward=constants.UNITY_AXIS_FORWARD,
                axis_up=constants.UNITY_AXIS_UP,
            )
        elif engine == 'GODOT':
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                global_scale=constants.GODOT_FBX_SCALE,
                axis_forward=constants.GODOT_AXIS_FORWARD,
                axis_up=constants.GODOT_AXIS_UP,
            )

        # --- Material Export ---
        material_export.export_materials(context, active_obj, export_path, filepath, self)

        self.report({'INFO'}, f"Exported {active_obj.name} to {filepath}")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(UNITY_OT_quick_export)


def unregister():
    bpy.utils.unregister_class(UNITY_OT_quick_export)
