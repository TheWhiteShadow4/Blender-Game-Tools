---
name: blender-addon-coding
title: Blender Addon Coding & Changes
category: software-development
---

# Blender Addon Coding Skill

## Purpose

This skill guides LLMs through making changes to Blender addon projects. It encodes general Blender addon development best practices, coding standards, and common patterns.

## Project Context

- **Project:** Blender addon (generic)
- **Python version:** 3.9+ (Blender 3.0+)
- **Tools:** `ruff`, `pyright`, `isort`, `mypy` (optional)
- **Blender version:** 5.2+ (bpy API)

## Project Structure (Generic)

A typical Blender addon structure:

```
addon/
├── __init__.py              # addon registration
├── bpy_types/               # bpy.types classes
│   ├── operators.py
│   ├── panels.py
│   ├── preferences.py
│   └── properties.py
├── utils/
│   ├── __init__.py
│   ├── geometry.py
│   ├── math_utils.py
│   └── io.py
├── ui/
│   ├── __init__.py
│   ├── icons.py
│   └── menus.py
├── preferences.py           # addon preferences
├── __manifest__.py          # addon manifest
└── tests/
    └── test_*.py
```

## Coding Standards

### Python Style

- Follow **PEP 8** and **ruff** rules
- Use **type hints** with `pyright` or `mypy` for strict checking
- Use **isort** for import sorting (standard library → third-party → local)
- Use **ruff** for linting (configured in `pyproject.toml` or `.ruff.toml`)
- Max line length: 88 characters (PEP 8)
- Use `f-strings` for string formatting
- Use `match`/`case` (Python 3.10+) for pattern matching when appropriate

### Naming Conventions

Blender enforces strict naming conventions for `bl_idname` to avoid collisions. See [Blender Developer Docs](https://developer.blender.org/docs/release_notes/2.80/python_api/addons/).

| Element | Convention | Example |
|---------|-----------|---------|
| Operator | `CATEGORY_OT_name` | `OBJECT_OT_delete`, `OBJECT_OT_move_x` |
| Panel | `CATEGORY_PT_name` | `OBJECT_PT_example`, `VIEW3D_PT_tools` |
| Menu | `CATEGORY_MT_name` | `VIEW3D_MT_example`, `OBJECT_MT_my_menu` |
| Header | `CATEGORY_HT_name` | `VIEW3D_HT_my_header` |
| UIList | `CATEGORY_UL_name` | `OBJECT_UL_my_list` |
| Separator | `_OT_`, `_PT_`, `_MT_`, `_HT_`, `_UL_` | |
| bl_label | Title case, no leading/trailing spaces | "Delete Selected" |
| bl_description | Sentence case, no leading/trailing spaces | "Delete selected objects" |
| bl_idname | snake_case, dots for submenus | `object.delete`, `object.move_x` |

### Type Hints

Since Blender 2.8, properties must use **type annotations** (PEP 526), not `=` assignment. Use `bpy.props` types directly.

```python
import bpy
from bpy.props import FloatProperty, IntProperty, EnumProperty, StringProperty

class MyOperator(bpy.types.Operator):
    """Delete selected objects with confirmation."""
    bl_idname = "object.my_operator"
    bl_label = "My Operator"
    bl_options = {'REGISTER', 'UNDO'}

    # Instance-level properties (per-operator instance)
    threshold: FloatProperty(
        name="Threshold",
        description="Distance threshold for selection",
        min=0.0,
        max=100.0,
        default=1.0,
    )
    mode: EnumProperty(
        name="Mode",
        description="Operation mode",
        items=(
            ("SELECT", "Select", "Select objects"),
            ("DELETE", "Delete", "Delete objects"),
            ("HIDE", "Hide", "Hide objects"),
        ),
        default="SELECT",
    )
    confirm: bool = False  # Class-level / shared across instances

    def execute(self, context):
        if not self.confirm:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        selected = bpy.context.selected_objects
        if not selected:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        for obj in selected:
            obj.select_set(False)
            obj.parent = None
            bpy.data.objects.remove(obj, do_unlink=True)

        self.report({'INFO'}, f"Deleted {len(selected)} objects.")
        return {'FINISHED'}
```

**Important:** Do **not** use `ClassVar` for properties — Blender requires type annotations with `:` syntax. Use `bool = False` for class-level flags (shared across all instances).

### Properties

- **Instance-level properties** are defined with type hints (`:`) and are unique per operator instance.
- **Class-level properties** are defined without type hints (e.g., `confirm: bool = False`) and are shared across all instances.
- Use `bpy.props` types: `FloatProperty`, `IntProperty`, `EnumProperty`, `StringProperty`, `BoolProperty`, `PointerProperty`, `CollectionProperty`.
- `subtype` can be used for advanced types like `FILE_PATH`, `RELATIVE_PATH`, etc.

## Blender API Best Practices

### Operators

```python
class OBJECT_OT_example(bpy.types.Operator):
    """Delete selected objects with confirmation."""
    bl_idname = "object.example"
    bl_label = "Example"
    bl_options = {'REGISTER', 'UNDO'}

    confirm: bool = False

    def poll(self, context):
        """Return True if the operator can execute."""
        return context.active_object is not None

    def invoke(self, context, event):
        """Handle user interaction (e.g., modal operators)."""
        if self.confirm:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # ... operator logic ...
        return {'FINISHED'}
```

**Key points:**
- `bl_idname` must follow `CATEGORY_OT_name` convention (e.g., `OBJECT_OT_delete`)
- `bl_label` uses Title Case (e.g., "Example")
- `bl_description` (tooltip) uses sentence case (e.g., "Deletes selected objects")
- `bl_options` must include `'REGISTER'` and `'UNDO'` when modifying Blender data
- `bl_idname` values are added to `bpy.ops`, making them callable (e.g., `bpy.ops.object.example()`)

### Property Groups

```python
class OBJECT_PG_example(bpy.types.PropertyGroup):
    """Custom property group for object properties."""
    my_float: bpy.props.FloatProperty(
        name="My Float",
        description="A floating point property",
        default=1.0,
    )
    my_int: bpy.props.IntProperty(
        name="My Int",
        default=0,
    )
    my_string: bpy.props.StringProperty(
        name="My String",
        description="A string property",
        default="hello",
    )
```

### Panels

```python
class OBJECT_PT_example(bpy.types.Panel):
    bl_label = "Example"
    bl_idname = "OBJECT_PT_example"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Example"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator("object.example", icon="FILE_REFRESH")
```

### Keymaps

```python
def keymap():
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(
        name="3D View", space_type="VIEW_3D", region_type="WINDOW"
    )
    kmi = km.keymap_items.new(
        "object.example", type="E", value="PRESS", ctrl=True
    )
    kmi.properties.confirm = True

def register():
    keymap()

def unregister():
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.get("3D View")
    if km:
        for kmi in km.keymap_items:
            if kmi.idname == "object.example":
                km.keymap_items.remove(kmi)
```

### `bpy.app.handlers` and `bpy.app.timers`

```python
import bpy

def depsgraph_update_post(dummy):
    """Callback when depsgraph updates."""
    print("Depsgraph updated")

def timer(interval):
    """Periodic timer callback."""
    print(f"Timer tick: {interval}s")
    return interval  # return None to stop

def register():
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)
    bpy.app.timers.register(timer, first_interval=1.0)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)
```

### Menus

```python
class VIEW3D_MT_example(bpy.types.Menu):
    bl_label = "Example"
    bl_idname = "VIEW3D_MT_example"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Example"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.example")
```

### Preferences

```python
class WM_OT_preferences(bpy.types.Operator):
    bl_idname = "wm.example_preferences"
    bl_label = "Preferences"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = context.window_manager.example_prefs
        layout = self.layout
        layout.prop(prefs, "auto_delete")
        layout.prop(prefs, "threshold")
        return {'FINISHED'}

class ExamplePrefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    auto_delete: bpy.props.BoolProperty(
        name="Auto Delete",
        default=False,
    )
    threshold: bpy.props.FloatProperty(
        name="Threshold",
        default=1.0,
    )
```

### Registration

```python
classes = (
    OBJECT_OT_example,
    WM_OT_preferences,
    VIEW3D_MT_example,
    OBJECT_PT_example,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
```

### Addon Manifest

```json
{
  "name": "Addon Name",
  "author": "Your Name",
  "description": "Addon description",
  "version": "1.0.0",
  "blender": "5.2",
  "category": "Object",
  "dependencies": []
}
```

## File Organization

### `__init__.py`

```python
import bpy
from .bpy_types import operators, panels, preferences
from .utils import geometry, math_utils
from .ui import icons, menus

classes = (
    *operators.classes,
    *panels.classes,
    *preferences.classes,
    *menus.classes,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
```

### `__manifest__.py`

```python
import json
import os

MANIFEST = {
    "name": "Addon Name",
    "author": "Your Name",
    "description": "Addon description",
    "version": "1.0.0",
    "blender": "5.2",
    "category": "Object",
    "dependencies": [],
}

def get_manifest_path() -> str:
    """Return the path to the addon manifest file."""
    return os.path.join(os.path.dirname(__file__), "__manifest__.json")
```

## Common Pitfalls

- **Don't** use `bpy.context` in background threads — always use `bpy.app.handlers.depsgraph_update_post` or `bpy.app.timers` for background work
- **Don't** use deprecated API calls like `bpy.context.scene` (use `context.scene`) or `bpy.context.active_object` (use `context.active_object`)
- **Don't** forget to call `bpy.utils.register_class` before using a class
- **Don't** use relative imports that break when the addon is loaded as a zip file (use absolute imports from the addon root)
- **Don't** hardcode file paths — use `bpy.path` for addon-relative paths
- **Don't** create circular imports between modules
- **Don't** forget to handle `{'CANCELLED'}` in operators when the user cancels
- **Don't** use `bpy.context` in operators that run from the command line (use `context` parameter)

## Verification Steps

After making changes:

1. **Lint:** `ruff check .`
2. **Type check:** `pyright` or `mypy`
3. **Format check:** `isort --check --diff .`
4. **Format fix:** `isort .` and `ruff format .`
5. **Run tests:** `pytest` (if tests exist)
6. **Manual test:** Load the addon in Blender and test each feature

## Related Skills

- `blender-addon-testing`: For running tests in a headless Blender harness
- `hermes-agent`: For general Hermes agent usage
```
