# Tests

Automatisierte Tests für das Blender-Game-Tools-Addon. Läuft in Blender 5.2 (Background-Modus) – keine GUI, keine externen Python-Pakete.

## Voraussetzungen

- **Blender 5.2** (getestet: 5.2.3 LTS)
- Kein `pip install` nötig – alle Tests nutzen nur stdlib + `bpy`

## Ausführen

```bash
# Alle Tests (Smoke + Export)
blender --background --python tests/test_smoke.py
blender --background --python tests/test_export_json.py

# Einzelner Test
blender --background --python tests/test_export_json.py
```

> **Hinweis:** Die JSON-Export-Tests benötigen `Shaders.blend` im Projekt-Root.
> Die Unity-Mock-Validierung braucht `tests/unity_mock/` (liegt im Repo).

## Test-Übersicht

| Test | Date | Prüft |
|------|------|-------|
| **Smoke-Test** | `test_smoke.py` | Addon-Laden, 6 Panels, 2 PropertyGroups, Unity-Mock, Engine-Erkennung, Property-Defaults |
| **JSON-Export** | `test_export_json.py` | Quick-Export mit `Shaders.blend`, JSON-Struktur, Golden-File-Abgleich |

## Golden-File-Workflow

Die JSON-Export-Tests vergleichen das Export-Ergebnis mit einer manuell verifizierten Referenzdatei:

```
tests/golden/Suzanne.fbx.imp.json
```

### Wenn sich das JSON-Format ändert

1. Test läuft → **FAIL** (Differenz wird mit Pfadangabe angezeigt, z.B. `.materials[0].properties[2].name`)
2. Neue JSON prüfen: `tests/unity_mock/Assets/FBX/Suzanne.fbx.imp.json`
3. Wenn die Änderung beabsichtigt ist:
   ```bash
   cp tests/unity_mock/Assets/FBX/Suzanne.fbx.imp.json tests/golden/
   git add tests/golden/
   ```
4. Wenn die Änderung **unbeabsichtigt** ist: Code fixen, Golden-File bleibt unverändert

### Golden-File neu erstellen

Falls die `Shaders.blend`-Scene oder das Addon-Verhalten fundamental geändert wurde:

```python
# tests/create_golden.py (Ad-hoc-Skript)
import bpy, sys, os, json, shutil

# (1) Addon laden + registrieren
# (2) Shaders.blend laden
# (3) Suzanne selektieren + aktiv setzen
# (4) props.engine_project_path = tests/unity_mock
# (5) bpy.ops.unity.quick_export()
# (6) JSON nach tests/golden/ kopieren
# (7) JSON MANUELL PRÜFEN vor dem Commit!
```

## Projektstruktur

```
tests/
├── test_smoke.py              # Smoke-Test (17 Assertions)
├── test_export_json.py        # JSON-Export-Test (16 Assertions)
├── golden/
│   └── Suzanne.fbx.imp.json   # Referenz-JSON (manuell verifiziert)
└── unity_mock/                # Mock-Unity-Projekt
    ├── Assets/
    │   └── .gitkeep
    └── ProjectSettings/
        └── ProjectVersion.txt # "m_EditorVersion: 6.4.0f1"
```

## Geplante Tests (noch nicht vorhanden)

- **Baker-Test:** Einfaches Cycles-Bake + Vector-Bug-Reproduktion
- **Cloth-Rigger-Test:** Grundlegendes Rigging eines Grid-Mesh
