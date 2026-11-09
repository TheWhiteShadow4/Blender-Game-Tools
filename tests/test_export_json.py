"""
Test: Material-Export JSON – Golden-File-Abgleich.

Fährt den Quick-Export mit Shaders.blend (Suzanne, Mat_Suzanne1)
und vergleicht die erzeugte JSON mit der manuell verifizierten
Golden-File in tests/golden/.

Ausführen:
    blender --background --python tests/test_export_json.py

Ohne pytest – nutzt ein einfaches Test-Framework (print + exit code).
"""

import sys
import os
import json
import shutil
import traceback

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
BLEND_FILE = os.path.join(PROJECT_ROOT, "Shaders.blend")
ADDON_DIR = PROJECT_ROOT
MOCK_UNITY_DIR = os.path.join(TESTS_DIR, "unity_mock")
GOLDEN_FILE = os.path.join(TESTS_DIR, "golden", "Suzanne.fbx.imp.json")
OUTPUT_FBX_DIR = os.path.join(MOCK_UNITY_DIR, "Assets", "FBX")
OUTPUT_JSON = os.path.join(OUTPUT_FBX_DIR, "Suzanne.fbx.imp.json")

# ---------------------------------------------------------------------------
# Test-Zähler
# ---------------------------------------------------------------------------
_passed = 0
_failed = 0


def check(condition: bool, description: str):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [OK ] {description}")
    else:
        _failed += 1
        print(f"  [FAIL] {description}")


def json_diff(a: dict, b: dict, path: str = "") -> list[str]:
    """Rekursiver JSON-Vergleich mit Pfadangaben.

    Nutzt nur stdlib – kein externes Package nötig.
    """
    diffs = []
    if type(a) != type(b):
        diffs.append(f"{path}: Typ {type(a).__name__} != {type(b).__name__}")
        return diffs
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a:
                diffs.append(f"{path}.{key}: fehlt in aktueller JSON")
            elif key not in b:
                diffs.append(f"{path}.{key}: fehlt in Golden-File")
            else:
                diffs.extend(json_diff(a[key], b[key], f"{path}.{key}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: Länge {len(a)} != {len(b)} (Golden)")
        for i, (ia, ib) in enumerate(zip(a, b)):
            diffs.extend(json_diff(ia, ib, f"{path}[{i}]"))
    elif a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs


# ---------------------------------------------------------------------------
# Test-Ausführung
# ---------------------------------------------------------------------------
def main():
    global _passed, _failed

    print("\n" + "=" * 60)
    print("Material-Export JSON – Golden-File-Test")
    print("=" * 60)

    # --- Golden-File vorhanden? ---
    if not os.path.isfile(GOLDEN_FILE):
        print(f"\n  [FATAL] Golden-File fehlt: {GOLDEN_FILE}")
        print("  Erstellen mit: tests/create_golden.py")
        sys.exit(1)

    print("\n--- Golden-File laden ---")
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        golden = json.load(f)
    check(True, f"Golden-File geladen ({len(json.dumps(golden)):,} chars)")
    print(f"    Materialien: {len(golden.get('materials', []))}")
    print(f"    Texturen: {len(golden.get('textures', []))}")

    # --- Vorherige Export-Dateien aufräumen (nur Dateien, kein rmtree – Windows-Locks) ---
    if os.path.isdir(OUTPUT_FBX_DIR):
        for f in os.listdir(OUTPUT_FBX_DIR):
            fpath = os.path.join(OUTPUT_FBX_DIR, f)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass  # Datei gesperrt – Quick-Export überschreibt sie ohnehin

    # --- Addon laden und registrieren ---
    print("\n--- Addon laden ---")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "tws_game_tools", os.path.join(ADDON_DIR, "__init__.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["tws_game_tools"] = module
    spec.loader.exec_module(module)
    module.register()
    check(True, "Addon geladen und registriert")

    # --- Scene einrichten ---
    import bpy

    print("\n--- Scene einrichten ---")
    props = bpy.context.scene.unity_tool_properties
    props.engine_project_path = MOCK_UNITY_DIR
    check(props.is_path_valid, f"Unity-Mock-Pfad gültig ({props.export_path})")

    # Suzanne selektieren + als aktiv setzen
    bpy.ops.object.select_all(action="DESELECT")
    suzanne = bpy.data.objects["Suzanne"]
    suzanne.select_set(True)
    bpy.context.view_layer.objects.active = suzanne
    check(
        bpy.context.view_layer.objects.active == suzanne,
        "Suzanne ist das aktive Objekt",
    )

    # --- Quick-Export ---
    print("\n--- Quick-Export ---")
    result = bpy.ops.unity.quick_export()
    check(result == {"FINISHED"}, "Quick-Export erfolgreich (FINISHED)")

    # --- Export-Dateien prüfen ---
    print("\n--- Export-Dateien ---")
    check(
        os.path.isfile(OUTPUT_JSON),
        f"JSON existiert: {os.path.basename(OUTPUT_JSON)}",
    )
    fbx_path = os.path.join(OUTPUT_FBX_DIR, "Suzanne.fbx")
    check(os.path.isfile(fbx_path), f"FBX existiert: Suzanne.fbx")

    if not os.path.isfile(OUTPUT_JSON):
        print("\n  [FATAL] Keine JSON erzeugt – Test abgebrochen.")
        sys.exit(1)

    # --- JSON laden ---
    print("\n--- JSON laden ---")
    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        current = json.load(f)
    check(True, f"Aktuelle JSON geladen ({len(json.dumps(current)):,} chars)")

    # --- Struktur-Check (Pflichtfelder) ---
    print("\n--- Struktur-Check ---")
    check("materials" in current, "Feld 'materials' vorhanden")
    check("textures" in current, "Feld 'textures' vorhanden")
    check("searchProjectMaterials" in current, "Feld 'searchProjectMaterials' vorhanden")
    check("overwriteTextureSettings" in current, "Feld 'overwriteTextureSettings' vorhanden")

    for i, mat in enumerate(current.get("materials", [])):
        check("materialName" in mat, f"materials[{i}].materialName vorhanden")
        check("shaderName" in mat, f"materials[{i}].shaderName vorhanden")
        check("properties" in mat, f"materials[{i}].properties vorhanden")

    # --- Golden-File-Abgleich ---
    print("\n--- Golden-File-Abgleich ---")
    diffs = json_diff(current, golden)

    if diffs:
        check(False, f"JSON weicht von Golden-File ab ({len(diffs)} Differenz(en)):")
        for d in diffs[:20]:  # max 20 anzeigen
            print(f"      {d}")
        if len(diffs) > 20:
            print(f"      ... und {len(diffs) - 20} weitere")
    else:
        check(True, "JSON entspricht exakt der Golden-File")

    # --- Zusammenfassung ---
    print("\n" + "=" * 60)
    total = _passed + _failed
    status = "PASS" if _failed == 0 else "FAIL"
    print(f"Ergebnis: {status} ({_passed}/{total} bestanden, {_failed} fehlgeschlagen)")
    print("=" * 60)

    sys.exit(0 if _failed == 0 else 1)


if __name__ == "__main__":
    main()
