# Rotation-Fix Sub-Feature
#
# Enthält:
# - operators.py: bpy-Operator für den Rotation-Fix
# - settings.py: RotationFixSettings-Kontext-Manager
#
# register()/unregister() werden von rigging/__init__.py aufgerufen.

from . import operators
from . import settings


def register():
    operators.register()


def unregister():
    operators.unregister()
