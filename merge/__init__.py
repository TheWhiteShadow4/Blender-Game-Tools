# Merge-Feature: Collection-Merge + Hair-Particle-Konvertierung
#
# Enthält:
# - operators.py: bpy-Operator für den Collection-Merge
# - hair_particle_converter.py: Hair-Partikel-Konvertierung
#
# register()/unregister() werden von add-on-Root aufgerufen.

from . import operators
from . import hair_particle_converter


def register():
    operators.register()


def unregister():
    operators.unregister()
