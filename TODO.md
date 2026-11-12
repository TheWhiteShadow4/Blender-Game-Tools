# TODO

## Addon-Settings
- [ ] Addon-Settings-Panel anlegen (fehlt komplett)
  - [ ] Importer-Flags aus `constants.py` als Properties auslagern: `SEARCH_PROJECT_MATERIALS`, `TRANSFER_TEXTURE_SETTINGS`, `OVERWRITE_TEXTURE_SETTINGS`
  - [ ] Umgang mit internen Bildern klären: aktuell werden sie pauschal als PNG unter `export_path/Textures/` gespeichert (`export/material_export.py:43-49`). Cache/Strategie?
  - [ ] Pfad des `BlenderAssetPostprocessor.cs` konfigurierbar machen (aktuell hartkodiert auf `Assets/Editor/`, `export/operators.py:38-41`)
  - [ ] Gamma-Korrektur (`apply_gamma_correction`) bereits in `properties.py` vorhanden – in Settings-Panel einbauen

## Bugs
- [ ] Baker crasht, wenn er einen Vector-Eingang backen soll (`baking/baker.py`, kein Vector-Handling)
- [x] Bake-Presets-Button wird nicht deaktiviert, wenn keine Presets aktiv sind
- [x] Channel-Auswahl in Single-Channel-Sockets ist mehrzeilig und leer
- [x] Mesh-Symmetry-Deaktivierung im Rotation Fix (Blender 4.5+ API, Automerge bereits implementiert)

## Unity-Postprocessor (C#)
- [ ] Normal-Flag aus Shader-Property-Flags auslesen und Texture-Type setzen (`BlenderAssetPostprocessor.cs:261`, TODO im Code)
- [ ] `FindTextureMapProperty` (Fallback `Metallic` → `_MetallicGlossMap`) ist nur Best-Effort; dokumentieren oder verfeinern

## Animation Rigger
- [ ] Option: vorhandenes Rig auswählen oder Kopie-Erstellung vom Physikobjekt skippen
- [ ] Animation von/bis Frame mit Loop-Option baken
- [ ] `nth`-Option wirklich implementieren (UI aktuell auskommentiert: `ui/panels_3d_view.py`, Animation-Panel)

## Code & Struktur
- [x] ~~`ui/panel_anim.py` ist orphane~~ — **erledigt** (Datei in `f8e3e02` gelöscht, Panel lebt in `ui/panels_3d_view.py`)
- [ ] Nach Blender-5.2-Migration (`7331bb5`, 22.08.2026) alle Module manuell gegen 5.2 testen: `merge/hair_particle_converter.py`, `cleanup/operators.py`, `baking/baker.py`, `baking/bake_utils.py`
- [x] ~~`bl_info` mit `blender_manifest.toml` synchron halten~~ — **erledigt** (`load_addon_version()` liest `blender_manifest.toml` als einzige Versionsquelle)
- [ ] `blender_manifest.toml`: `blender_version_min = "4.4.0"` prüfen, ob mit 5.2-Target noch sinnvoll (Code zielt auf 5.2+)

## Refactoring & Dokumentation (nächster Schritt)
- [x] ~~Refactoring-Plan erstellen~~ — **erledigt** (Feature-Subpackages umgesetzt: `baking/`, `cleanup/`, `export/`, `merge/`, `rigging/`)
- [ ] `README.md` mit TODO-Liste und Design-Konzept (`DESIGN_CONCEPT.md`) abgleichen
- [ ] `DESIGN_CONCEPT.md` auf aktuellen Stand bringen (steht auf Meilenstein-4-Niveau, aber JSON-Struktur hat sich geändert: Texturen sind jetzt referenziert statt inline)

## Issues (später)
- [ ] GitHub-Issues durchgehen und in diese TODO-Liste übernehmen (https://github.com/TheWhiteShadow4/Blender-Game-Tools)
