# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Rotation-Fix-Operator."""

import bpy
import math
from ... import constants
from . import settings


class UNITY_OT_apply_rotation_fix(bpy.types.Operator):
    """Apply rotation fix for Unity export"""
    bl_idname = "unity.apply_rotation_fix"
    bl_label = "Apply Rotation Fix"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        active_obj = context.active_object

        if any(abs(angle) > constants.ROTATION_TOLERANCE for angle in active_obj.rotation_euler):
            self.report({'WARNING'}, "Operation nur für Objekte ohne Rotation möglich.")
            return {'CANCELLED'}

        with settings.RotationFixSettings(context):
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.view3d.snap_cursor_to_selected()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X', orient_type='CURSOR')
            bpy.ops.object.mode_set(mode='OBJECT')
            active_obj.rotation_euler.x += math.radians(90)

        self.report({'INFO'}, "Rotation fix applied")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(UNITY_OT_apply_rotation_fix)


def unregister():
    bpy.utils.unregister_class(UNITY_OT_apply_rotation_fix)
