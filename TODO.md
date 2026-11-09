# TODO

## Addon-Settings
- [ ] Addon-Settings-Panel anlegen (fehlt komplett)
  - [ ] Importer-Flags aus `constants.py` als Properties auslagern: `SEARCH_PROJECT_MATERIALS`, `TRANSFER_TEXTURE_SETTINGS`, `OVERWRITE_TEXTURE_SETTINGS`
  - [ ] Umgang mit internen Bildern klären: aktuell werden sie pauschal als PNG unter `export_path/Textures/` gespeichert (`material_export.py:43-49`). Cache/Strategie?
  - [ ] Pfad des `BlenderAssetPostprocessor.cs` konfigurierbar machen (aktuell hartkodiert auf `Assets/Editor/`, `operators.py:38-41`)
  - [ ] Gamma-Korrektur (`apply_gamma_correction`) bereits in `properties.py` vorhanden – in Settings-Panel einbauen

## Bugs
- [ ] Baker crasht, wenn er einen Vector-Eingang backen soll (`baker.py`, kein Vector-Handling)
- [x] Bake-Presets-Button wird nicht deaktiviert, wenn keine Presets aktiv sind
- [x] Channel-Auswahl in Single-Channel-Sockets ist mehrzeilig und leer
- [x] Mesh-Symmetry-Deaktivierung im Rotation Fix (Blender 4.5+ API, Automerge bereits implementiert)

## Unity-Postprocessor (C#)
- [ ] Normal-Flag aus Shader-Property-Flags auslesen und Texture-Type setzen (`BlenderAssetPostprocessor.cs:261`, TODO im Code)
- [ ] `FindTextureMapProperty` (Fallback `Metallic` → `_MetallicGlossMap`) ist nur Best-Effort; dokumentieren oder verfeinern

## Animation Rigger
- [ ] Option: vorhandenes Rig auswählen oder Kopie-Erstellung vom Physikobjekt skippen
- [ ] Animation von/bis Frame mit Loop-Option baken
- [ ] `nth`-Option wirklich implementieren (UI aktuell auskommentiert: `ui/panel_anim.py:22`)

## Code & Struktur
- [ ] `ui/panel_anim.py` ist orphane – nie in `__init__.py` importiert/registriert. Die Animation-Panel-Klasse ist doppelt in `ui/panels_3d_view.py` (Zeile 145) implementiert. Entscheiden: `panel_anim.py` löschen oder als Quelle etablieren.
- [ ] Nach Blender-5.2-Migration (`7331bb5`, 22.08.2026) alle Module manuell gegen 5.2 testen: `hair_particle_converter.py`, `cleanup_operators.py`, `baker.py`, `bake_utils.py`
- [ ] `bl_info` (`__init__.py:11`, aktuell `(1, 4)`) mit `blender_manifest.toml` (`version`) in Zukunft synchron halten – Version nur an einer Stelle pflegen
- [ ] `blender_manifest.toml`: `blender_version_min = "4.4.0"` prüfen, ob mit 5.2-Target noch sinnvoll (Code zielt auf 5.2+)

## Refactoring & Dokumentation (nächster Schritt)
- [ ] Refactoring-Plan erstellen (Modul-Grenzen, API-Konsistenz, DRY)
- [ ] `README.md` mit TODO-Liste und Design-Konzept (`DESIGN_CONCEPT.md`) abgleichen
- [ ] `DESIGN_CONCEPT.md` auf aktuellen Stand bringen (steht auf Meilenstein-4-Niveau, aber JSON-Struktur hat sich geändert: Texturen sind jetzt referenziert statt inline)

## Issues (später)
- [ ] GitHub-Issues durchgehen und in diese TODO-Liste übernehmen (https://github.com/TheWhiteShadow4/Blender-Game-Tools)
