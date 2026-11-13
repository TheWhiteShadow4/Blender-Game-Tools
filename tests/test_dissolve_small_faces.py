# pyright: reportInvalidTypeForm=false
# pyright: reportMissingImports=false
"""Test: dissolve_small_faces entfernt tatsächlich kleine Faces."""

import sys
import bpy

def test_dissolve_small_faces():
    """Erzeugt ein Mesh mit 1 gro\xdfem + 1 winzigem Face, pr\xfcft den Cleanup."""
    print("=" * 60)
    print("  DISSOLVE SMALL FACES TEST")
    print("=" * 60)

    # Addon muss geladen sein
    import addon_utils
    try:
        addon_utils.enable("tws_game_tools", default_set=True)
    except Exception:
        pass
    if not hasattr(bpy.context.scene, "unity_tool_properties"):
        print("  [FAIL] Addon nicht installiert – kein Test möglich")
        return False

    # Mesh anlegen: 1 grosses Rechteck (1x1) + 1 winziges Dreieck (0.001x0.001)
    # Grosse Face: 4 Vertices bei (0,0,0),(1,0,0),(1,1,0),(0,1,0)
    # Kleine Face: 3 Vertices bei (2,0,0),(2.001,0,0),(2,0.001,0)
    verts = [
        (0, 0, 0),    # 0
        (1, 0, 0),    # 1
        (1, 1, 0),    # 2
        (0, 1, 0),    # 3
        (2, 0, 0),    # 4
        (2.001, 0, 0),# 5
        (2, 0.001, 0) # 6
    ]
    faces = [
        (0, 1, 2, 3),  # grosses Rechteck
        (4, 5, 6),     # winziges Dreieck
    ]

    mesh = bpy.data.meshes.new("TestSmallFaces")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("TestSmallFaces", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)

    # Vorher: 2 Faces
    before_faces = len(obj.data.polygons)
    print(f"  Faces vor Cleanup: {before_faces}")

    assert before_faces == 2, f"Erwartet 2 Faces, erhalten {before_faces}"

    # Cleanup ausf\xfchren
    from tws_game_tools.cleanup.object_cleanups import ObjectCleanupTools
    success, message = ObjectCleanupTools.dissolve_small_faces(obj, min_area=0.01)
    print(f"  Cleanup: success={success}, message={message!r}")

    # Nachher: gro\xdfes Face muss \xfcbrig bleiben, kleines weg sein
    after_faces = len(obj.data.polygons)
    print(f"  Faces nach Cleanup: {after_faces}")

    # Berechne die \xfcbrigen Face-Areas
    areas = [p.area for p in obj.data.polygons]
    print(f"  \xdcbrig gebliebene Areas: {areas}")

    # Gro\xdfes Face (Area ~1.0) muss vorhanden sein
    has_big_face = any(abs(a - 1.0) < 0.1 for a in areas)
    # Kleines Face (Area ~0.0000005) muss NICHT vorhanden sein
    has_small_face = any(a < 0.01 for a in areas)

    print(f"  Gro\xdfes Face vorhanden: {has_big_face}")
    print(f"  Kleines Face vorhanden: {has_small_face}")

    # Aufr\xe4umen
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)

    if not success:
        print("  [FAIL] Cleanup meldete Fehler")
        return False

    if after_faces != 1:
        print(f"  [FAIL] Erwartet 1 Face nach Cleanup, erhalten {after_faces}")
        return False

    if not has_big_face:
        print("  [FAIL] Gro\xdfes Face (Area~1.0) nicht mehr vorhanden")
        return False

    if has_small_face:
        print("  [FAIL] Kleines Face (Area<0.01) war nicht entfernt – Bug!")
        return False

    print("  [OK ] Gro\xdfes Face erhalten, kleines Face entfernt")
    print("=" * 60)
    print("  ALLE TESTS BESTANDEN \u2713")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = test_dissolve_small_faces()
    sys.exit(0 if ok else 1)
