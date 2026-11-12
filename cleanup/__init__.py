# Cleanup-Feature: Objekt-Bereinigung
#
# Enthält:
# - operators.py: bpy-Operators für die Cleanup-Operationen
# - object_cleanups.py: Reine Logik (bpy-basiert, aber ohne UI)
#
# register()/unregister() werden von add-on-Root aufgerufen.

from . import operators
from . import object_cleanups


def register():
    operators.register()


def unregister():
    operators.unregister()
