"""Handles loading user-provided custom modules. Its purpose is to dynamically
import a single dedicated Python file defined by the user that contains their
customized cleanup functions."""

import importlib.util
from pathlib import Path
from typing import Callable

__all__ = ["TransformsRegistry", "load_transforms_registry_if_available"]


def load_transforms_registry_if_available(
    module_path: str | Path | None,
) -> "TransformsRegistry | None":
    """
    Load a TransformsRegistry from a file path, or return None when custom
    transforms should not be used (no path, empty path, or missing file).
    """
    if module_path is None:
        return None
    if isinstance(module_path, str) and not module_path.strip():
        return None
    path = Path(module_path).expanduser()
    try:
        path = path.resolve()
    except OSError:
        return None
    if not path.is_file():
        return None
    return TransformsRegistry(path)


class TransformsRegistry:
    """
    Loads, stores, and accesses relevant information from a user-defined
    custom-transforms module.
    """

    def __init__(self, module_path: Path):
        """
        Loads custom transforms module. Module must define a `transforms` dict.
        TODO: Implement error handling
        """

        module_name = module_path.stem
        spec   = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._transforms = module.transforms

    def get_transform(self, name: str) -> Callable:
        """
        Looks up specific field-level transformations by their string name.
        TODO: Implement error handling
        """
        return self._transforms[name]

