# Baking-Feature: Material-Baking für Unity/Godot
#
# Enthält:
# - baker.py: Kern-Baking-Logik (Baker-Klasse)
# - bake_utils.py: Bake-Datenmodell (BakeData, BakePass, etc.)
# - alpha_combiner.py: Alpha-Kanal-Merge-Logik
# - panel.py: Baking-UI (Panels, PropertyGroups, Operators)
#
# register()/unregister() werden von add-on-Root aufgerufen.

from . import baker
from . import bake_utils
from . import alpha_combiner
from . import panel


def register():
    panel.register()


def unregister():
    panel.unregister()
