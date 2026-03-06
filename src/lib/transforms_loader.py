"""Handles loading user-provided custom modules. Its purpose is to dynamically 
import a single dedicated Python file defined by the user that contains their 
customized cleanup functions."""

import importlib.util
from pathlib import Path
from typing import Callable


class TransformsRegistry:
    """
    Loads, stores, and accesses relevant information from a user-defined
    custom-transforms module.
    """

    def __init__(self, module_path: Path):
        """
        Loads custom transforms module, loads transforms and hooks

        Module must define:
            transforms: dict
            hooks     : dict

        TODO: Implement error handling
        """

        module_name = module_path.stem
        spec   = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self._transforms = module.transforms
        self._hooks      = module.hooks


    def get_transform(self, name: str) -> Callable:
        """
        Looks up specific field-level transformations by their string name.
        TODO: Implement error handling
        """
        return self._transforms[name]

    def get_hook(self, stage: str) -> Callable:
        """
        Retrieves broad row-level or collection-level hooks.
        TODO: Implement error handling
        """
        return self._hooks[stage]
