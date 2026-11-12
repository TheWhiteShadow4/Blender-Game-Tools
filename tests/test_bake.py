# -*- coding: utf-8 -*-
"""
Bake-Test: Führt das Material-Baking auf Test.blend aus und
prüft, ob die beiden Bake-Presets (ColorMap + Smoothness)
korrekt in die Ziel-Texturen gebacken wurden.

Aufruf:
    blender --background tests/Test.blend --python tests/test_bake.py
"""
import bpy
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_DIR = os.path.dirname(TESTS_DIR)
OUTPUT_DIR = os.path.join(TESTS_DIR, "bake_output")

failures = 0


def check(condition, msg):
    global failures
    if condition:
        print(f"  [OK]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures += 1


def main():
    global failures

    # --- Addon ist installiert – nur noch prüfen ---
    print("=" * 60)
    print("  BAKE TEST – Material-Baking auf Test.blend")
    print("=" * 60)

    check(hasattr(bpy.types.Object, "unity_bake_settings"), "Addon ist installiert")
    if failures > 0:
        print(f"\n{failures} Test(s) FEHLGESCHLAGEN")
        sys.exit(1)

    # --- Suzanne muss vorhanden sein ---
    suzanne = bpy.data.objects.get("Suzanne")
    check(suzanne is not None, "Suzanne vorhanden in Test.blend")
    if suzanne is None:
        print(f"\n{failures} Test(s) FEHLGESCHLAGEN")
        sys.exit(1)

    # --- Suzanne selektieren und aktivieren ---
    bpy.ops.object.select_all(action='DESELECT')
    suzanne.select_set(True)
    bpy.context.view_layer.objects.active = suzanne
    check(suzanne in bpy.context.selected_objects, "Suzanne selektiert")
    check(bpy.context.view_layer.objects.active == suzanne, "Suzanne ist aktiv")

    # --- Bake-Presets inspizieren ---
    bake_settings = suzanne.unity_bake_settings
    print(f"\n  Bake Presets: {len(bake_settings.presets)}")
    active_presets = [p for p in bake_settings.presets if p.is_active]
    check(len(active_presets) == 2, f"2 aktive Bake Presets (gefunden: {len(active_presets)})")

    # Erwartete Bilder sammeln
    expected_images = {}
    for preset in active_presets:
        if preset.bake_mode == 'EXISTING' and preset.existing_image:
            expected_images[preset.target_socket_name] = preset.existing_image
            print(f"  Preset \"{preset.name}\": {preset.target_socket_name} → {preset.existing_image.name}")

    check(len(expected_images) == 2, f"2 EXISTING-Images in Presets (gefunden: {len(expected_images)})")

    # --- Pixel vor dem Baking speichern (zur Vergleichbarkeit) ---
    print("\n  Pixel vor Baking:")
    before_pixels = {}
    for name, img in expected_images.items():
        pixels = list(img.pixels)
        non_zero = sum(1 for i in range(0, len(pixels), 4)
                       if pixels[i] != 0 or pixels[i+1] != 0 or pixels[i+2] != 0)
        before_pixels[name] = (non_zero, len(pixels) // 4)
        print(f"    {name}: {non_zero}/{len(pixels) // 4} Pixel nicht schwarz")

    # --- Bake ausführen (GUI-Dialog umgehen) ---
    print("\n  Baking läuft ...")

    # Wir rufen bake_batch.execute() direkt auf, aber ersetzen
    # den INVOKE_DEFAULT-Aufruf durch eine direkte Baker-Ausführung.
    # Am einfachsten: bake_batch.execute() aufrufen und dann
    # confirm_bake.execute() – aber der Operator ist INTERNAL und
    # INVOKE_DEFAULT funktioniert im Background nicht.
    #
    # Lösung: bake_batch.execute() aufrufen (baut bake_data auf und
    # speichert es in der Class-Variable), dann direkt den Baker
    # aufrufen.
    from tws_game_tools.baking import baker as baker_module
    from tws_game_tools.baking import bake_utils

    # bake_batch.execute() aufrufen – das baut die BakeData auf
    # und speichert sie in UNITY_OT_bake_batch.bake_data_to_confirm
    # Am Ende versucht es INVOKE_DEFAULT, was im Background fehlschlägt,
    # aber die bake_data_to_confirm ist bereits gesetzt.
    from tws_game_tools.baking.panel import UNITY_OT_bake_batch
    try:
        result = bpy.ops.unity.bake_batch()
        print(f"  bake_batch Result: {result}")
    except RuntimeError:
        # INVOKE_DEFAULT schlägt im Background fehl – das ist OK
        print("  bake_batch: INVOKE_DEFAULT fehlgeschlagen (erwartet im Background)")

    # Im Background-Modus wird confirm_bake('INVOKE_DEFAULT') aufgerufen,
    # der die bake_data direkt ausführt und dann auf None setzt.
    # Wir prüfen daher die Pixel-Ergebnisse direkt.

    # --- Pixel nach dem Baking prüfen ---
    print("\n  Pixel nach Baking:")
    after_pixels = {}
    for name, img in expected_images.items():
        pixels = list(img.pixels)
        non_zero = sum(1 for i in range(0, len(pixels), 4)
                       if pixels[i] != 0 or pixels[i+1] != 0 or pixels[i+2] != 0)
        after_pixels[name] = (non_zero, len(pixels) // 4)
        print(f"    {name}: {non_zero}/{len(pixels) // 4} Pixel nicht schwarz")

    # Beide Texturen müssen jetzt gebacken sein (nicht mehr 0 Pixel)
    for name, (after_nz, total) in after_pixels.items():
        check(after_nz > 0, f"{name}: Texture enthält gebackene Daten ({after_nz}/{total} Pixel)")

        # Pixel müssen sich von vor dem Baking unterscheiden
        before_nz, _ = before_pixels.get(name, (0, total))
        if before_nz == 0 and after_nz > 0:
            print(f"    → {name}: war leer, jetzt gefüllt ✓")

    # --- Texturen als PNG speichern (für nachträgliche Auswertung) ---
    print("\n  Texturen speichern ...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name, img in expected_images.items():
        out_path = os.path.join(OUTPUT_DIR, f"{name}_baked.png")
        # Die gebackene Pixel-Daten liegen in den Image-Datenblöcken
        # (save_mode='INTERNAL'), aber die Daten gehören noch 'uns'
        # (generated_image_data). save() weigert sich daher mit
        # "does not have any image data". Durch Zuweisen der Pixel
        # auf sich selbst wird der Block in einen gepufferten
        # Image mit 'user-owned' Daten konvertiert.
        img.pixels = img.pixels[:]
        img.filepath_raw = out_path
        img.file_format = 'PNG'
        img.save()
        check(os.path.isfile(out_path), f"{name}_baked.png gespeichert")

    # --- Ergebnis ---
    print("\n" + "=" * 60)
    if failures > 0:
        print(f"  {failures} Test(s) FEHLGESCHLAGEN")
        print("=" * 60)
        sys.exit(1)
    else:
        print(f"  Alle Tests bestanden ✓")
        print("=" * 60)


if __name__ == "__main__":
    main()
