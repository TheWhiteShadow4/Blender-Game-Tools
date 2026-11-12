# Rigging-Feature: Cloth-Rig + Animation
#
# Enthält:
# - cloth_rigger.py: Cloth-Rig-Operator
# - rotation_fix/: Rotation-Fix Sub-Feature
#
# register()/unregister() werden von add-on-Root aufgerufen.

from . import cloth_rigger
from . import rotation_fix


def register():
    cloth_rigger.register()
    rotation_fix.register()


def unregister():
    rotation_fix.unregister()
    cloth_rigger.unregister()
