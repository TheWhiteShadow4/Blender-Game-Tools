@tool
extends EditorPlugin

var import_plugin

func _enter_tree():
	import_plugin = preload("fbx_import.gd").new()
	add_scene_post_import_plugin(import_plugin)
	print("BlenderImpJson Importer registered")

func _exit_tree():
	remove_scene_post_import_plugin(import_plugin)
	import_plugin = null
	print("BlenderImpJson Importer unregistered")