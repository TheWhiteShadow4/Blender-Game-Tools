---
name: blender-addon-coding
title: Blender Addon Coding & Changes
category: software-development
---

# Blender Addon Coding Skill

## Purpose

This skill guides LLMs through making changes to your Blender addon repository. It encodes the project's structure, coding standards, and Blender-specific best practices.

## Project Context

- **Project:** Blender Game Tools addon
- **Root:** `C:\Users\manuel.letzner\OneDrive - BiPRO e.V\Projekte\Hermes-Projekte\Blender-Game-Tools`
- **Python version:** 3.14.7 (Hermes-managed, `python` command)
- **Tools:** `ruff`, `pyright`, `isort`
- **Blender version:** 4.2+ (bpy API)

## Project Structure

The addon is organized as a Blender addon with:
- `pyproject.toml` — project metadata and dependencies
- `pyrightconfig.json` — type checking configuration
- `.ruff.toml` — linting configuration
- `.gitignore` — excludes `__pycache__`, `*.pyc`, `.venv`
- `blender_manifest.json` — addon manifest
- `README.md` — user documentation

## Coding Standards

### Python Style

- Follow **PEP 8** and **ruff** rules
- Use **type hints** with `pyright` for strict checking
- Use **isort** for import sorting
- Use **ruff** for linting (configured in `.ruff.toml`)
- Avoid deprecated bpy API calls (check Blender 4.2+ docs)

### Blender Specific

- Use `bpy.types` for new classes (avoid `bpy.utils.register_class` for simple cases)
- Use `bpy.props` for properties with `PropertyGroup`
- Use `bpy.app.version` for version checks
- Use `bpy.context` for current context (`bpy.context.active_object`, etc.)
- Avoid blocking operations in the main thread (use `bpy.app.timers`)
- Use `bpy.utils.preferred_addon_paths` for addon-relative paths

### Testing

- Tests are in `tests/` directory
- Use `pytest` with `pytest-benchmark` for performance tests
- Write unit tests for utility functions
- Write integration tests for addon registration/unregistration

## Workflow for Changes

When making changes:

1. **Understand the change:** Read existing code, understand the addon's purpose
2. **Plan the change:** Decide what files to modify, what to add, what to remove
3. **Make the change:** Edit files using `patch` or `write_file`
4. **Lint and type-check:** Run `ruff check`, `pyright`, `isort`
5. **Test:** Run relevant tests if they exist
6. **Commit:** Create a git commit with a descriptive message

## Common Tasks

### Adding a new operator

```python
import bpy

class MY_OT_foo(bpy.types.Operator):
    """Blender operator description"""
    bl_idname = "object.my_foo"
    bl_label = "Foo"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # implementation
        return {'FINISHED'}
```

### Adding a new property

```python
import bpy

class MY_OT_foo(bpy.types.Operator):
    prop_name: bpy.props.IntProperty(name="Foo", min=0, max=100)
```

### Adding a new UI panel

```python
import bpy

class MY_PT_foo(bpy.types.Panel):
    bl_label = "Foo"
    bl_idname = "OBJECT_PT_foo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Foo"

    def draw(self, context):
        layout = self.layout
        # add widgets
```

### Registering the addon

```python
classes = (MY_OT_foo, MY_PT_foo)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

## Files to Modify

| File | Purpose |
|------|---------|
| `blender_manifest.json` | Addon manifest |
| `pyproject.toml` | Dependencies |
| `pyrightconfig.json` | Type checking |
| `.ruff.toml` | Linting rules |
| `README.md` | Documentation |
| `tests/*.py` | Tests |

## Pitfalls

- **Don't** modify `__pycache__` or `*.pyc` files
- **Don't** use `bpy.context` in background threads
- **Don't** use deprecated bpy API calls (e.g., `bpy.context.scene` vs `context.scene`)
- **Don't** forget to register/unregister classes
- **Don't** use relative imports that break when the addon is loaded as a zip file
- **Don't** hardcode paths; use `bpy.utils.preferred_addon_paths`

## Verification

After making changes:

1. Run `ruff check .`
2. Run `pyright` (or `pyright --verifytypes`)
3. Run `isort --check --diff .`
4. Run the addon in Blender and test manually
5. Run any relevant tests with `pytest`

## Related Skills

- `blender-addon-testing`: For running tests in a headless Blender harness
- `hermes-agent`: For general Hermes agent usage
