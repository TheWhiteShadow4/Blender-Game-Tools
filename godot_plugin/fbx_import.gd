@tool
extends EditorScenePostImportPlugin

const MATERIALS_DIR := "Materials"

# Name des Post-Importers (wird im Import-Dock angezeigt)
func _get_name() -> String:
	return "BlenderImpJsonPost"

# Höhere Priorität stellt sicher, dass wir nach dem Built-in laufen
func _get_priority() -> float:
	return 5.0

# Haupt-Callback: Szene wurde bereits von Godot importiert
func _post_import(scene: Node, path: String, _preset_idx: int) -> Node:
	var json_path: String = path + ".imp.json"
	if !FileAccess.file_exists(json_path):
		# Keine Zusatzdaten vorhanden
		return scene

	print("BlenderImpJsonPost: Processing ", json_path)
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(data) != TYPE_DICTIONARY:
		printerr("BlenderImpJsonPost: JSON parse error")
		return scene

	var mat_dir: String = path.get_base_dir().path_join(MATERIALS_DIR)
	if !DirAccess.dir_exists_absolute(mat_dir):
		DirAccess.make_dir_recursive_absolute(mat_dir)

	# Erstelle Materialien und ersetze sie in der importierten Szene
	for mat_data in data.get("materials", []):
		var mat := StandardMaterial3D.new()
		mat.resource_name = mat_data.get("materialName", "Mat")

		for prop in mat_data.get("properties", []):
			match prop.get("type", ""):
				"Color":
					var v = prop["value"]
					mat.albedo_color = Color(v[0], v[1], v[2], v[3])
				"Float":
					mat.metallic = prop.get("floatValue", 0.0)
				"Texture":
					mat.albedo_texture = load(prop.get("path", ""))

		var mat_path := "%s/%s.tres" % [mat_dir, mat.resource_name]
		ResourceSaver.save(mat, mat_path)

		_assign_material(scene, mat)

	return scene

# Hilfsfunktion: traversiert Szene und ersetzt Materialien nach Name
func _assign_material(root: Node, mat: Material) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			var mesh: Mesh = child.mesh
			if mesh:
				for i in range(mesh.get_surface_count()):
					if mesh.surface_get_name(i) == mat.resource_name:
						child.set_surface_override_material(i, mat)
		_assign_material(child, mat)
