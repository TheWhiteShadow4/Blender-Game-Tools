# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Material export functions for Unity/Godot."""

import os
import json
import shutil
from .. import constants


def correct_color(color, apply_gamma):
	"""Applies gamma correction to a color if the flag is set."""
	if not apply_gamma:
		return list(color)
	# Convert Linear to sRGB color space for Unity.
	return [
		pow(color[0], 1.0/constants.GAMMA_CORRECTION_FACTOR),
		pow(color[1], 1.0/constants.GAMMA_CORRECTION_FACTOR),
		pow(color[2], 1.0/constants.GAMMA_CORRECTION_FACTOR),
		color[3] # Alpha is linear
	]


def copy_texture_and_get_path(tex_node, unity_props, export_path, operator, texture_cache):
	"""Copies a texture to the export directory and returns its relative path for Unity."""
	if not tex_node.image:
		operator.report({'WARNING'}, f"Texture node '{tex_node.name}' has no image assigned.")
		return None

	# Duplicate-copy prevention via instance cache
	cached_path = texture_cache.get(tex_node.image.name)
	if cached_path:
		return cached_path

	# Zielverzeichnis vorbereiten
	texture_export_dir = os.path.join(export_path, constants.TEXTURE_EXPORT_DIR)
	os.makedirs(texture_export_dir, exist_ok=True)

	# Prüfen, ob das Image intern ist (nicht auf der Festplatte gespeichert)
	is_internal = not tex_node.image.filepath or tex_node.image.filepath.startswith("//") or tex_node.image.packed_file

	try:
		if is_internal:
			# Für interne Bilder schreiben wir immer als PNG
			dest_path = os.path.join(texture_export_dir, tex_node.image.name + ".png")
			tex_node.image.filepath_raw = dest_path
			tex_node.image.file_format = 'PNG'
			tex_node.image.save()
			operator.report({'INFO'}, f"Internal Texture saved to: '{dest_path}'")
		else:
			source_path = tex_node.image.filepath_from_user()
			if not os.path.exists(source_path):
				operator.report({'ERROR'}, f"Texture file not found: {source_path}")
				return None
			# Behalte die Original-Endung
			dest_path = os.path.join(texture_export_dir, os.path.basename(source_path))
			# Wenn die Datei bereits am Ziel liegt, nicht erneut kopieren
			if os.path.abspath(source_path) != os.path.abspath(dest_path):
				try:
					shutil.copy(source_path, dest_path)
				except shutil.SameFileError:
					pass  # Quelle == Ziel, nichts zu tun
			else:
				# Datei liegt bereits am Zielort
				pass

		relative_texture_path = os.path.join(unity_props.export_path, constants.TEXTURE_EXPORT_DIR, os.path.basename(dest_path))
		relative_texture_path = relative_texture_path.replace('\\', '/')
		# Cache merken
		texture_cache[tex_node.image.name] = relative_texture_path
		return relative_texture_path
	except Exception as e:
		operator.report({'ERROR'}, f"Could not copy or save texture '{tex_node.image.name}': {e}")
		return None


TEXTURE_NAME_SUFFIXES = ("map", "tex", "texture", "mask", "normal", "noise")
COLOR_NAME_SUFFIXES = ("color", "colour")


def _is_texture_property(name):
	"""True if the socket name follows Unity's texture-property naming convention."""
	return name.lower().endswith(TEXTURE_NAME_SUFFIXES)


def _is_color_property(name):
	"""True if the socket name follows Unity's color-property naming convention."""
	return name.lower().endswith(COLOR_NAME_SUFFIXES)


SEPARATE_COLOR_CHANNELS = {'Red': 'R', 'Green': 'G', 'Blue': 'B'}

def _classify_texture_type(socket, is_non_color):
	"""Bestimmt die Textur-Verwendungsart aus dem Blender-Socket-Typ.

	- Value/Int/Boolean-Socket -> "Value" (Daten-Textur).
	- Color/RGBA-Socket -> "Color". Ob es sich um eine Normal-Map handelt,
	  entscheidet erst der Importer anhand des Ziel-Shaders.
	"""
	if socket and socket.type in {'VECTOR'}:
		return "Normal"
	if socket and (is_non_color or socket.type in {'VALUE', 'INT', 'BOOLEAN'}):
		return "Value"

	return "Color"


class TextureRegistry:
	"""Sammelt Texturen dedupliziert und baut die JSON-Texturliste auf."""

	def __init__(self):
		self.textures = []
		self._by_path = {}

	def register(self, tex_node, tex_path, tex_type):
		if tex_path in self._by_path:
			index = self._by_path[tex_path]
			entry = self.textures[index]
			return index

		entry = _build_texture_entry(tex_node, tex_path, tex_type)
		index = len(self.textures)
		self.textures.append(entry)
		self._by_path[tex_path] = index
		return index


def _build_texture_entry(tex_node, tex_path, tex_type):
	"""Baut den deduplizierten Textur-Eintrag inkl. Einstellungen."""
	entry = {
		"path": tex_path,
		"type": tex_type,
	}

	# Interpolation/Filter und Wrap-Mode nur übertragen, wenn aktiviert.
	if constants.TRANSFER_TEXTURE_SETTINGS:
		entry["interpolation"] = tex_node.interpolation
		entry["wrapMode"] = tex_node.extension

	return entry


def process_socket(socket, unity_props, export_path, operator, texture_cache, texture_registry):
	"""Processes a single node socket and returns a dictionary for the JSON property, or None."""
	prop_name = socket.name

	if prop_name.endswith("_Alpha"):
		return None

	prop_entry = {"name": prop_name}
	is_texture_name = _is_texture_property(prop_name)
	is_color_name = _is_color_property(prop_name)

	# Case 1: Socket is connected to another node
	if socket.is_linked:
		from_node = socket.links[0].from_node

		if from_node.type == 'TEX_IMAGE':
			# Textures are the only reliable signal for a texture property. Even if
			# the name follows the color convention, a connected Image Texture still
			# represents a texture; the Unity importer resolves the actual shader
			# property type and will warn if there is a mismatch.
			if is_color_name:
				operator.report({'WARNING'}, f"Input '{prop_name}' follows color convention but is connected to a texture.")

			tex_path = copy_texture_and_get_path(from_node, unity_props, export_path, operator, texture_cache)
			if tex_path:
				is_non_color = from_node.image.colorspace_settings.name in {"Linear", "Non-Color", "Raw"}
				from_socket = socket.links[0].from_socket
				prop_entry["type"] = "Texture"
				prop_entry["texture"] = texture_registry.register(from_node, tex_path, _classify_texture_type(socket, is_non_color))
			else:
				return None # Error was already reported by the helper

		elif from_node.type == 'RGB':
			# Export the constant color value of the RGB node.
			prop_entry["type"] = "Color"
			prop_entry["value"] = correct_color(from_node.outputs[0].default_value, unity_props.apply_gamma_correction)

		elif from_node.type == 'VALUE':
			# Export the constant float value of the Value node.
			prop_entry["type"] = "Float"
			prop_entry["floatValue"] = from_node.outputs[0].default_value

		elif from_node.type == 'SEPARATE_COLOR':
			# The input is fed by one of the Separate Color outputs (Red/Green/Blue).
			# Record the source texture and the used channel so Unity can rebuild it.
			from_socket = socket.links[0].from_socket
			channel = SEPARATE_COLOR_CHANNELS.get(from_socket.name, from_socket.name)

			# Ensure the Separate Color input is a texture.
			color_input = from_node.inputs.get('Color')
			if not color_input or not color_input.is_linked:
				operator.report({'WARNING'}, f"Input '{prop_name}' uses SEPARATE_COLOR but its Color input is not connected.")
				return None

			tex_node = color_input.links[0].from_node
			if not tex_node or tex_node.type != 'TEX_IMAGE':
				operator.report({'WARNING'}, f"Input '{prop_name}' uses SEPARATE_COLOR but its input is not a texture ('{tex_node.type if tex_node else 'None'}').")
				return None

			tex_path = copy_texture_and_get_path(tex_node, unity_props, export_path, operator, texture_cache)
			if not tex_path:
				return None

			prop_entry["type"] = "Texture"
			prop_entry["texture"] = texture_registry.register(tex_node, tex_path, _classify_texture_type(socket, True))
			prop_entry["channel"] = channel

		else:
			operator.report({'INFO'}, f"Input '{prop_name}' is connected to an unsupported node type ('{from_node.type}'). It will be ignored.")
			return None

	# Case 2: Socket is not connected, use its default value
	else:
		if is_texture_name:
			# A texture property without a connected texture should stay unassigned in
			# Unity. Exporting a color here would make Unity try to set a color on a
			# texture property, which logs an error.
			return None

		if socket.type == 'RGBA':
			prop_entry["type"] = "Color"
			color = socket.default_value
			prop_entry["value"] = correct_color(color, unity_props.apply_gamma_correction)

		elif socket.type in {'VALUE', 'INT', 'BOOLEAN'}:
			if is_color_name:
				operator.report({'WARNING'}, f"Input '{prop_name}' follows color convention but is a Float, not RGBA.")
			prop_entry["type"] = "Float"
			prop_entry["floatValue"] = float(socket.default_value)

		else: # Other unlinked socket types we don't handle
			return None

	return prop_entry


def export_materials(context, obj, export_path, fbx_filepath, operator):
	"""Exports ALL materials of the given object into a single *.imp.json file."""
	unity_props = context.scene.unity_tool_properties
	materials_data = []
	texture_cache = {}
	texture_registry = TextureRegistry()

	# Iterate over every material slot on the object
	for mat_slot in obj.material_slots:
		mat = mat_slot.material
		if not mat:
			continue

		# Skip materials without proper node setup
		if not mat.node_tree or not mat.node_tree.nodes:
			operator.report({'INFO'}, f"Material '{mat.name}' has no node tree, skipping")
			continue

		# Find interface node inside this material
		output_node = next((n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
		if not (output_node and output_node.inputs['Surface'].links):
			operator.report({'INFO'}, f"Material '{mat.name}' has no valid output connection, skipping")
			continue

		interface_node = output_node.inputs['Surface'].links[0].from_node

		# Check if this is a supported shader node (with node_tree attribute)
		if not hasattr(interface_node, 'node_tree') or not interface_node.node_tree:
			operator.report({'INFO'}, f"Material '{mat.name}' uses unsupported node type '{interface_node.type}', exporting material reference only")
			# Export minimal material data so Unity can try to find it by name
			materials_data.append({
				"materialName": mat.name,
				"shaderName": None,  # Unity importer will search for existing material
				"properties": []
			})
			continue

		material_data = {
			"materialName": mat.name,
			"shaderName": interface_node.node_tree.name,
			"properties": []
		}

		try:
			for socket in interface_node.inputs:
				prop_entry = process_socket(socket, unity_props, export_path, operator, texture_cache, texture_registry)
				if prop_entry:
					material_data["properties"].append(prop_entry)
		except Exception as e:
			operator.report({'WARNING'}, f"Error processing material '{mat.name}': {e}. Material reference exported.")

		# Add material data (even if properties list is empty, so Unity knows the material name)
		materials_data.append(material_data)

	# Nothing to export
	if not materials_data:
		return

	json_filepath = fbx_filepath + ".imp.json"
	try:
		with open(json_filepath, 'w') as f:
			json.dump({
				"materials": materials_data,
				"textures": texture_registry.textures,
				"searchProjectMaterials": constants.SEARCH_PROJECT_MATERIALS,
				"overwriteTextureSettings": constants.OVERWRITE_TEXTURE_SETTINGS,
			}, f, indent=4)
		operator.report({'INFO'}, f"Exported material data for {len(materials_data)} materials.")
	except Exception as e:
		operator.report({'WARNING'}, f"Could not write material json: {e}")
