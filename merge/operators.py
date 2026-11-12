# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Merge-Feature: Collection-Merge-Operator."""

import bpy
from . import hair_particle_converter


class UNITY_OT_merge_objects(bpy.types.Operator):
    """Merge objects from selected collection"""
    bl_idname = "unity.merge_objects"
    bl_label = "Merge Collection Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def _safe_name_check(self, name, data_collection):
        """Sichere Überprüfung ob ein Name in einer Blender-Datensammlung existiert"""
        try:
            return name in data_collection
        except (UnicodeError, KeyError):
            for existing_name in data_collection.keys():
                if existing_name == name:
                    return True
            return False

    def _get_mono_bone_name(self, obj):
        """Ermittelt den Bone-Namen für ein Mono Animation Object, falls vorhanden"""
        if obj.parent and obj.parent.type == 'ARMATURE' and obj.parent_bone:
            return obj.parent_bone
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.vertex_group:
                return modifier.vertex_group
        return None

    def _is_mono_animation_object(self, obj):
        """Prüft ob ein Objekt ein Mono Animation Object ist"""
        if obj.type != 'MESH':
            return False
        return self._get_mono_bone_name(obj) is not None

    def _process_mono_animation_object(self, obj):
        """Verarbeitet ein Mono Animation Object"""
        bone_name = self._get_mono_bone_name(obj)
        if not bone_name:
            return
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if bone_name not in obj.vertex_groups:
            vertex_group = obj.vertex_groups.new(name=bone_name)
        else:
            vertex_group = obj.vertex_groups[bone_name]
        vertex_indices = [v.index for v in obj.data.vertices]
        if vertex_indices:
            vertex_group.add(vertex_indices, 1.0, 'REPLACE')

    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to merge objects from"
    )

    def get_collections_enum(self, context):
        active_obj = context.active_object
        if not active_obj:
            return [('NONE', "No active object", "")]
        collections = []
        collection_index = 0
        for collection in bpy.data.collections:
            try:
                if active_obj.name in collection.objects:
                    safe_id = f"COLLECTION_{collection_index}"
                    collections.append((safe_id, collection.name, f"Merge objects from {collection.name}"))
                    collection_index += 1
            except (UnicodeError, KeyError):
                for obj in collection.objects:
                    if obj == active_obj:
                        safe_id = f"COLLECTION_{collection_index}"
                        collections.append((safe_id, collection.name, f"Merge objects from {collection.name}"))
                        collection_index += 1
                        break
        if not collections:
            return [('NONE', "No collections found", "")]
        return collections

    selected_collection: bpy.props.EnumProperty(
        name="Select Collection",
        description="Choose which collection to merge",
        items=get_collections_enum
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        if self.collection_name:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "selected_collection")

    def _resolve_source_collection(self):
        if self.collection_name:
            collection = bpy.data.collections.get(self.collection_name)
            if collection is None:
                self.report({'ERROR'}, f"Collection '{self.collection_name}' nicht gefunden")
            return collection
        if not self.selected_collection or self.selected_collection == 'NONE':
            return None
        active_obj = bpy.context.active_object
        if not active_obj:
            return None
        collection_index = 0
        for collection in bpy.data.collections:
            try:
                if active_obj.name not in collection.objects:
                    continue
            except (UnicodeError, KeyError):
                if not any(obj == active_obj for obj in collection.objects):
                    continue
            if f"COLLECTION_{collection_index}" == self.selected_collection:
                return collection
            collection_index += 1
        return None

    def execute(self, context):
        active_obj = context.active_object
        source_collection = self._resolve_source_collection()
        if not source_collection:
            self.report({'ERROR'}, "Kein gültiges Objekt oder keine Collections gefunden")
            return {'CANCELLED'}

        merged_collection_name = f"{source_collection.name}_Merged"
        merged_collection = None
        collection_was_created = False
        hair_objects_created = []

        try:
            if self._safe_name_check(merged_collection_name, bpy.data.collections):
                merged_collection = bpy.data.collections[merged_collection_name]
                objects_to_remove = list(merged_collection.objects)
                for obj in objects_to_remove:
                    merged_collection.objects.unlink(obj)
                    if not any(obj.name in col.objects for col in bpy.data.collections if col != merged_collection):
                        bpy.data.objects.remove(obj)
            else:
                merged_collection = bpy.data.collections.new(merged_collection_name)
                context.scene.collection.children.link(merged_collection)
                collection_was_created = True

            def find_layer_collection(layer_collection, name):
                if layer_collection.collection.name == name:
                    return layer_collection
                for child in layer_collection.children:
                    result = find_layer_collection(child, name)
                    if result:
                        return result
                return None

            layer_collection = find_layer_collection(context.view_layer.layer_collection, merged_collection_name)
            if layer_collection:
                layer_collection.exclude = False
            else:
                raise RuntimeError(f"Layer Collection '{merged_collection_name}' konnte nicht gefunden werden")

            objects_to_process = []
            for obj in source_collection.objects:
                new_obj = obj.copy()
                if obj.data:
                    new_obj.data = obj.data.copy()
                merged_collection.objects.link(new_obj)
                objects_to_process.append(new_obj)

            hair_converter = hair_particle_converter.HairParticleConverter(self.report)
            for obj in list(objects_to_process):
                if hair_converter.has_hair_particles(obj):
                    try:
                        converted_objects = hair_converter.convert_hair_particles(context, obj)
                        for hair_obj in converted_objects:
                            if not hair_obj:
                                continue
                            for col in hair_obj.users_collection:
                                col.objects.unlink(hair_obj)
                            if hair_obj.name not in merged_collection.objects:
                                merged_collection.objects.link(hair_obj)
                                objects_to_process.append(hair_obj)
                        hair_objects_created.extend(converted_objects)
                        self.report({'INFO'}, f"Hair-Partikel von '{obj.name}' konvertiert: {len(converted_objects)} Objekte erstellt")
                    except Exception as e:
                        self.report({'WARNING'}, f"Fehler beim Konvertieren der Hair-Partikel von '{obj.name}': {e}")

            modifier_applied_count = 0
            for obj in objects_to_process:
                if obj.type == 'MESH' and obj.modifiers:
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    modifiers_to_apply = []
                    modifiers_to_remove = []
                    for modifier in obj.modifiers:
                        if modifier.type != 'ARMATURE':
                            if modifier.show_viewport:
                                modifiers_to_apply.append(modifier.name)
                            else:
                                modifiers_to_remove.append(modifier.name)
                    for mod_name in modifiers_to_apply:
                        try:
                            bpy.ops.object.modifier_apply(modifier=mod_name)
                            modifier_applied_count += 1
                        except Exception as e:
                            self.report({'WARNING'}, f"Konnte Modifier '{mod_name}' auf {obj.name} nicht anwenden: {e}")
                    for mod_name in modifiers_to_remove:
                        try:
                            bpy.ops.object.modifier_remove(modifier=mod_name)
                        except Exception as e:
                            self.report({'WARNING'}, f"Konnte Modifier '{mod_name}' auf {obj.name} nicht entfernen: {e}")

            converted_count = 0
            for obj in objects_to_process:
                if obj.type != 'MESH':
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    original_type = obj.type
                    try:
                        if obj.type in ['CURVE', 'SURFACE', 'META', 'FONT']:
                            bpy.ops.object.convert(target='MESH')
                            converted_count += 1
                            if original_type == 'CURVE' and bpy.context.active_object and bpy.context.active_object.type == 'MESH':
                                bpy.ops.object.shade_smooth()
                        elif obj.type == 'GPENCIL':
                            bpy.ops.gpencil.convert(type='CURVE')
                            bpy.ops.object.convert(target='MESH')
                            converted_count += 1
                    except Exception as e:
                        self.report({'WARNING'}, f"Konnte {obj.name} ({obj.type}) nicht konvertieren: {e}")

            unity_props = context.scene.unity_tool_properties
            mono_objects_processed = 0
            if unity_props.isolate_mono_animation_objects:
                for obj in objects_to_process:
                    if self._is_mono_animation_object(obj):
                        try:
                            self._process_mono_animation_object(obj)
                            mono_objects_processed += 1
                        except Exception as e:
                            self.report({'WARNING'}, f"Konnte Mono Animation Object {obj.name} nicht verarbeiten: {e}")

            mesh_objects = [obj for obj in merged_collection.objects if obj.type == 'MESH']
            if len(mesh_objects) > 1:
                bpy.ops.object.select_all(action='DESELECT')
                for obj in mesh_objects:
                    obj.select_set(True)
                if mesh_objects:
                    bpy.context.view_layer.objects.active = mesh_objects[0]
                    bpy.ops.object.join()
                    merged_obj = bpy.context.active_object
                    desired_name = source_collection.name
                    if not self._safe_name_check(desired_name, bpy.data.objects):
                        merged_obj.name = desired_name
                        if merged_obj.data and not self._safe_name_check(desired_name, bpy.data.meshes):
                            merged_obj.data.name = desired_name
                        else:
                            merged_obj.data.name = f"{desired_name}_Mesh"
                    else:
                        merged_obj.name = f"{desired_name}_Merged"
                        if merged_obj.data:
                            merged_obj.data.name = f"{desired_name}_Merged_Mesh"
                    self.report({'INFO'}, f"Collection '{merged_collection_name}' erstellt. {len(objects_to_process)} Objekte zu einem Mesh gemerged. {mono_objects_processed} Mono Animation Objects verarbeitet, {modifier_applied_count} Modifier angewendet, {converted_count} Objekte zu Mesh konvertiert.")
            elif len(mesh_objects) == 1:
                single_obj = mesh_objects[0]
                desired_name = source_collection.name
                if not self._safe_name_check(desired_name, bpy.data.objects):
                    single_obj.name = desired_name
                    if single_obj.data and not self._safe_name_check(desired_name, bpy.data.meshes):
                        single_obj.data.name = desired_name
                    else:
                        single_obj.data.name = f"{desired_name}_Mesh"
                else:
                    single_obj.name = f"{desired_name}_Merged"
                    if single_obj.data:
                        single_obj.data.name = f"{desired_name}_Merged_Mesh"
                self.report({'INFO'}, f"Collection '{merged_collection_name}' erstellt mit einem Objekt. {mono_objects_processed} Mono Animation Objects verarbeitet, {modifier_applied_count} Modifier angewendet, {converted_count} Objekte zu Mesh konvertiert.")
            else:
                self.report({'WARNING'}, f"Collection '{merged_collection_name}' erstellt, aber keine Mesh-Objekte zum Mergen gefunden.")

        except Exception as e:
            self.report({'ERROR'}, f"Fehler beim Mergen der Collection: {e}")
            if merged_collection:
                objects_to_cleanup = list(merged_collection.objects)
                for obj in objects_to_cleanup:
                    try:
                        merged_collection.objects.unlink(obj)
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except Exception as cleanup_error:
                        self.report({'WARNING'}, f"Konnte Objekt {obj.name} nicht aufräumen: {cleanup_error}")
                if collection_was_created:
                    try:
                        context.scene.collection.children.unlink(merged_collection)
                        bpy.data.collections.remove(merged_collection)
                    except Exception as cleanup_error:
                        self.report({'WARNING'}, f"Konnte Collection nicht entfernen: {cleanup_error}")
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = active_obj
        return {'FINISHED'}


def register():
    bpy.utils.register_class(UNITY_OT_merge_objects)


def unregister():
    bpy.utils.unregister_class(UNITY_OT_merge_objects)
