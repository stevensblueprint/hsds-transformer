"""Load and validate local, user-provided custom transform modules."""

import importlib.util
from pathlib import Path
from typing import Callable


def load_transforms_registry_if_available(module_path: str | Path | None):
    """No path opts out; an explicitly supplied invalid path is an error."""
    if module_path is None:
        return None
    return TransformsRegistry(Path(module_path).expanduser())


class TransformsRegistry:
    """A validated dictionary of named callable transforms."""

    def __init__(self, module_path: Path):
        try:
            spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
            if spec is None or spec.loader is None:
                raise ValueError("Expected a Python module file")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            transforms = getattr(module, "transforms", None)
            if not isinstance(transforms, dict):
                raise ValueError("Module must define a 'transforms' dictionary")
            for name, function in transforms.items():
                if not isinstance(name, str) or not name.strip():
                    raise ValueError("Transform names must be nonempty strings")
                if not callable(function):
                    raise ValueError(f"Transform {name!r} must be callable")
        except Exception as exc:
            raise ValueError(f"Cannot load custom transforms from '{module_path}': {exc}") from exc
        self._transforms = dict(transforms)

    def get_transform(self, name: str) -> Callable:
        try:
            return self._transforms[name]
        except KeyError as exc:
            raise ValueError(f"Unknown custom transform {name!r}") from exc


def validate_mapping_transforms(mapping, registry, **context):
    """Resolve every declaration before processing values, even filtered/blank ones."""
    if isinstance(mapping, dict):
        if "path" in mapping:
            name = mapping.get("transform")
            if name:
                location = ", ".join(f"{key}={value}" for key, value in context.items())
                try:
                    if not isinstance(name, str):
                        raise ValueError("Transform name must be a string")
                    if registry is None:
                        raise ValueError("No custom transform registry is available; use CLI --transforms")
                    if not callable(registry.get_transform(name)):
                        raise ValueError("Transform implementation must be callable")
                except Exception as exc:
                    raise ValueError(
                        f"Invalid custom transform {name!r} for {mapping['path']!r} "
                        f"({location}): {exc}"
                    ) from exc
        else:
            for value in mapping.values():
                validate_mapping_transforms(value, registry, **context)
    elif isinstance(mapping, list):
        for value in mapping:
            validate_mapping_transforms(value, registry, **context)
