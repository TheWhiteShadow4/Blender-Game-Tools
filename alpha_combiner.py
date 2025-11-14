# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""
Alpha channel combination utilities for baked textures.
Pure combination functions - no knowledge of baking passes or settings.
"""
import bpy


def validate_alpha_image(main_image, alpha_image):
	"""
	Validiert, ob die Alpha-Textur kompatibel mit der Haupttextur ist.
	
	Args:
		main_image: Haupttextur (bpy.types.Image)
		alpha_image: Alpha-Textur (bpy.types.Image)
		
	Returns:
		(bool, str): (is_valid, error_message)
	"""
	if not main_image:
		return False, "Main image is None"
	
	if not alpha_image:
		return False, "Alpha image is None"
	
	if not main_image.has_data:
		return False, f"Main image '{main_image.name}' has no pixel data"
	
	if not alpha_image.has_data:
		return False, f"Alpha image '{alpha_image.name}' has no pixel data"
	
	if main_image.size[0] != alpha_image.size[0]:
		return False, (
			f"Width mismatch: Main image '{main_image.name}' has width {main_image.size[0]}, "
			f"but alpha image '{alpha_image.name}' has width {alpha_image.size[0]}"
		)
	
	if main_image.size[1] != alpha_image.size[1]:
		return False, (
			f"Height mismatch: Main image '{main_image.name}' has height {main_image.size[1]}, "
			f"but alpha image '{alpha_image.name}' has height {alpha_image.size[1]}"
		)
	
	return True, ""


def combine_alpha_channel(main_image, alpha_image, cleanup_alpha=False):
	"""
	Kombiniert den Alpha-Kanal aus einer separaten Alpha-Textur in die Haupttextur.
	
	Die Alpha-Textur wird als Graustufen-Bild interpretiert (R-Kanal wird verwendet).
	
	Args:
		main_image: Haupttextur, in die der Alpha-Kanal geschrieben wird (bpy.types.Image)
		alpha_image: Alpha-Textur, aus der der Alpha-Kanal gelesen wird (bpy.types.Image)
		cleanup_alpha: Wenn True, wird die Alpha-Textur nach der Kombination gelöscht
		
	Returns:
		(bool, str): (success, message)
	"""
	print(f"  Combining alpha: Source='{alpha_image.name}' ({alpha_image.size[0]}x{alpha_image.size[1]}) -> Target='{main_image.name}' ({main_image.size[0]}x{main_image.size[1]})")
	
	# Validierung
	is_valid, error_msg = validate_alpha_image(main_image, alpha_image)
	if not is_valid:
		print(f"  -> Validation failed: {error_msg}")
		return False, error_msg
	
	try:
		# Pixel-Arrays sind RGBA, also 4 Werte pro Pixel
		pixel_count = main_image.size[0] * main_image.size[1]
		total_pixels = pixel_count * 4  # RGBA = 4 Werte pro Pixel
		
		# Haupttextur-Pixel lesen (RGBA)
		# pixels ist bereits ein Array, wir müssen es in eine Liste konvertieren
		main_pixels = [0.0] * total_pixels
		main_image.pixels.foreach_get(main_pixels)
		
		# Alpha-Textur-Pixel lesen (RGBA, aber wir nutzen nur R-Kanal)
		alpha_pixels = [0.0] * total_pixels
		alpha_image.pixels.foreach_get(alpha_pixels)
		
		# Alpha-Kanal aus Alpha-Textur extrahieren (R-Kanal als Alpha)
		# und in Haupttextur schreiben
		for i in range(pixel_count):
			# Index für RGBA-Array: i * 4 + channel_index
			# R=0, G=1, B=2, A=3
			alpha_value = alpha_pixels[i * 4 + 0]  # R-Kanal der Alpha-Textur
			
			# Alpha-Kanal der Haupttextur setzen
			main_pixels[i * 4 + 3] = alpha_value
		
		# Pixel-Daten zurück in Haupttextur schreiben
		main_image.pixels.foreach_set(main_pixels)
		
		# Image als geändert markieren
		main_image.update()
		
		print(f"  -> Successfully copied alpha channel from '{alpha_image.name}' to '{main_image.name}'")
		
		# Optional: Alpha-Textur löschen
		if cleanup_alpha:
			bpy.data.images.remove(alpha_image)
			print(f"  -> Removed alpha image '{alpha_image.name}' after combining.")
		
		return True, f"Successfully combined alpha channel from '{alpha_image.name}' into '{main_image.name}'"
		
	except Exception as e:
		import traceback
		print(f"  -> ERROR during alpha combination: {str(e)}")
		print(traceback.format_exc())
		return False, f"Error combining alpha channels: {str(e)}"



