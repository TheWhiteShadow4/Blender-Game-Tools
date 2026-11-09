"""
Smoke-Test für das TWS Game Tools Addon.

Wird ausgeführt mit:
    blender --background --python tests/test_smoke.py

Prüft:
- Addon wird ohne Exception geladen
- Panels sind registriert
- PropertyGroups an Scene vorhanden
- Unity-Mock-Projekt wird als gültig erkannt

HINWEIS: Der Addon-Ordner heißt 'Blender-Game-Tools', aber der Manifest-ID
ist 'tws_game_tools'. Dieser Test importiert das Addon direkt per sys.path,
um das addon_enable()-System zu umgehen.
"""

import sys
import bpy
from pathlib import Path

# --- sys.path vorbereiten -------------------------------------------------

# Addon-Verzeichnis zum Python-Pfad hinzufügen
# So kann `import Blender-Game-Tools` (als Modul) funktionieren
addon_dir = Path(__file__).resolve().parent.parent  # .../Blender-Game-Tools
if str(addon_dir) not in sys.path:
    sys.path.insert(0, str(addon_dir))

# --- Test-Suite -----------------------------------------------------------

_failures = []


def check(label, condition):
    status = "OK " if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        _failures.append(label)


# --- 1. Addon laden --------------------------------------------------------

print("\n=== 1. Addon laden ===")

try:
    # Importiere das Addon direkt – der Modulname ist der Verzeichnisname
    # 'Blender-Game-Tools' ist kein gültiger Python-Modulname,
    # daher nutzen wir importlib mit dem Pfad.
    import importlib.util

    addon_init = addon_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location("tws_game_tools", str(addon_init))
    module = importlib.util.module_from_spec(spec)
    sys.modules["tws_game_tools"] = module
    spec.loader.exec_module(module)
    # __init__.py ruft register() nur bei __name__ == "__main__" auf,
    # das ist hier nicht der Fall – daher explizit aufrufen.
    module.register()
    print("  [OK ] Addon 'tws_game_tools' erfolgreich geladen und registriert.")
    addon_loaded = True
except Exception as e:
    import traceback
    print(f"  [FAIL] Addon konnte nicht geladen werden: {e}")
    traceback.print_exc()
    addon_loaded = False

check("Addon 'tws_game_tools' ist geladen", addon_loaded)

# --- 2. Panels registriert -------------------------------------------------

print("\n=== 2. Panel-Registrierung ===")

expected_panels = [
    "UNITY_PT_main_panel",
    "UNITY_PT_cleanup_panel",
    "UNITY_PT_animation_panel",
    "UNITY_PT_export_panel",
    "UNITY_PT_merge_panel",
    "UNITY_PT_baking_shortcut_panel",
]

def find_panel(idname):
    """Finde eine Panel-Klasse per bl_idname."""
    for cls in bpy.types.Panel.__subclasses__():
        if getattr(cls, "bl_idname", None) == idname:
            return cls
    return None

for idname in expected_panels:
    panel_cls = find_panel(idname)
    check(f"Panel '{idname}' ist registriert", panel_cls is not None)

# --- 3. PropertyGroups -----------------------------------------------------

print("\n=== 3. PropertyGroups an Scene ===")

scene = bpy.context.scene
check(
    "scene.unity_tool_properties existiert",
    hasattr(scene, "unity_tool_properties")
    and scene.unity_tool_properties is not None,
)
check(
    "scene.unity_cloth_rig_properties existiert",
    hasattr(scene, "unity_cloth_rig_properties")
    and scene.unity_cloth_rig_properties is not None,
)

# --- 4. Unity-Mock-Projekt validieren --------------------------------------

print("\n=== 4. Unity-Mock-Projekt ===")

# Pfade relativ zu diesem Script auflösen
test_dir = Path(__file__).resolve().parent
mock_project = test_dir / "unity_mock"

check(f"Mock-Projekt existiert: {mock_project}", mock_project.is_dir())
check(
    "Mock-Projekt hat Assets/Ordner",
    (mock_project / "Assets").is_dir(),
)
check(
    "Mock-Projekt hat ProjectSettings/Ordner",
    (mock_project / "ProjectSettings").is_dir(),
)
check(
    "ProjectVersion.txt vorhanden",
    (mock_project / "ProjectSettings" / "ProjectVersion.txt").is_file(),
)

# Validierungsfunktion aus dem Addon nutzen
try:
    from tws_game_tools import validation
    is_valid = validation.validate_unity_project(str(mock_project))
    check("validation.validate_unity_project(Mock) → True", is_valid is True)
except Exception as e:
    print(f"  [FAIL] Validierung konnte nicht importiert/aufgerufen werden: {e}")
    check("validation.validate_unity_project(Mock) → True", False)

# --- 5. Engine-Erkennung ---------------------------------------------------

print("\n=== 5. Engine-Erkennung ===")

try:
    from tws_game_tools import properties as tws_props
    engine = tws_props.detect_game_engine(str(mock_project))
    check(f"Engine-Erkennung: erwartet 'UNITY', erhalten '{engine}'", engine == "UNITY")
except Exception as e:
    print(f"  [FAIL] detect_game_engine fehlgeschlagen: {e}")
    check("Engine-Erkennung", False)

# --- 6. Property-Werte ------------------------------------------------------

print("\n=== 6. Property-Default-Werte ===")

tool_props = scene.unity_tool_properties
check(
    "engine_project_path ist StringProperty",
    isinstance(tool_props.engine_project_path, str),
)
check(
    "export_path Default = 'Assets/FBX'",
    tool_props.export_path == "Assets/FBX",
)
check(
    "apply_gamma_correction Default = False",
    tool_props.apply_gamma_correction is False,
)

cloth_props = scene.unity_cloth_rig_properties
check(
    "cloth_rig mode Default = 'VERTICES'",
    cloth_props.mode == "VERTICES",
)
check(
    "cloth_rig nth Default = 1",
    cloth_props.nth == 1,
)

# --- Zusammenfassung -------------------------------------------------------

print("\n" + "=" * 50)
if _failures:
    print(f"ERGEBNIS: {len(_failures)} FEHLGESCHLAGEN von {14 + len(_failures)} Tests")
    for f in _failures:
        print(f"  ✗ {f}")
    # Blender-Exit-Code für CI-Kompatibilität
    sys.exit(1)
else:
    print("ERGEBNIS: ALLE TESTS BESTANDEN ✓")
    sys.exit(0)
