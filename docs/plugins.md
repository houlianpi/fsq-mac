# Plugin Development

fsq-mac supports plugins via Python entry points. You can extend it with custom automation backends and doctor checks.

## Entry point groups

| Group | Purpose |
|-------|---------|
| `fsq_mac.adapters` | Custom automation backends |
| `fsq_mac.doctor` | Custom environment checks |

## Writing an adapter plugin

### 1. Implement the adapter

Your adapter class must implement the methods expected by `AutomationCore`. At minimum:

```python
# my_adapter/backend.py

class MyCustomAdapter:
    def __init__(self, config: dict):
        self._config = config
        self._driver = None

    def connect(self, bundle_id: str) -> dict:
        # Initialize connection to your automation backend
        ...

    @property
    def connected(self) -> bool:
        return self._driver is not None

    def disconnect(self) -> None:
        ...

    def inspect(self, max_elements: int = 200) -> list[dict]:
        # Return list of visible UI elements
        ...

    def click(self, ref, strategy="accessibility_id", timeout=5) -> dict:
        ...

    def type_text(self, ref, text, strategy="accessibility_id") -> dict:
        ...

    # ... other methods as needed
```

### 2. Create a factory function

The entry point must resolve to a callable that accepts a config dict and returns an adapter instance:

```python
# my_adapter/backend.py

def create_adapter(config: dict):
    return MyCustomAdapter(config)
```

Or you can point directly to the class (the constructor serves as the factory).

### 3. Register via entry points

In your package's `pyproject.toml`:

```toml
[project.entry-points."fsq_mac.adapters"]
my_backend = "my_adapter.backend:create_adapter"
```

Or if using `setup.cfg`:

```ini
[options.entry_points]
fsq_mac.adapters =
    my_backend = my_adapter.backend:create_adapter
```

### 4. Install and verify

```bash
pip install my-adapter-package
mac doctor plugins
```

Your backend should appear in the adapters list.

## Writing a doctor plugin

Doctor plugins add custom environment checks to `mac doctor`.

### 1. Implement check functions

Each entry point should be a callable that accepts a config dict and returns a list of check results:

```python
# my_plugin/checks.py

def my_checks(config: dict | None = None) -> list[dict]:
    results = []

    # Check #1
    try:
        # ... your check logic ...
        results.append({
            "name": "My Custom Check",
            "status": "ok",
            "detail": "Everything looks good",
        })
    except Exception as e:
        results.append({
            "name": "My Custom Check",
            "status": "fail",
            "detail": str(e),
            "fix": "Instructions to fix the issue",
        })

    return results
```

### 2. Register via entry points

```toml
[project.entry-points."fsq_mac.doctor"]
my_checks = "my_plugin.checks:my_checks"
```

### 3. Verify

```bash
mac doctor plugins
```

Your check name should appear in the doctor_plugins list.

## Discovery mechanism

Plugins are discovered at import time:

1. When `fsq_mac.adapters` is imported, `_discover_entry_points()` is called.
2. It loads all entry points in the `fsq_mac.adapters` group.
3. Each entry point's `load()` is called to get the factory callable.
4. The factory is registered with `register_adapter(name, factory)`.

Similarly for doctor plugins via `_discover_doctor_plugins()`.

## Name collision handling

- **Built-in adapters are registered first**. If an entry point has the same name as a built-in adapter (e.g., `appium_mac2`), the entry point is skipped.
- To override a built-in, you would need to modify the source. This is intentional to prevent accidental replacement.

## Error handling

- If an entry point's `load()` raises an exception (e.g., missing dependency), the plugin is silently skipped.
- Other plugins continue to load normally.
- Use `mac doctor plugins` to verify your plugin was discovered.

## Example plugin package

A minimal plugin package structure:

```
my-fsq-plugin/
  pyproject.toml
  src/
    my_fsq_plugin/
      __init__.py
      adapter.py
      checks.py
```

`pyproject.toml`:

```toml
[project]
name = "my-fsq-plugin"
version = "0.1.0"
dependencies = ["fsq-mac"]

[project.entry-points."fsq_mac.adapters"]
my_backend = "my_fsq_plugin.adapter:MyAdapter"

[project.entry-points."fsq_mac.doctor"]
my_checks = "my_fsq_plugin.checks:run_checks"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```
