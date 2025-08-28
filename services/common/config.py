import json
from typing import Any, Dict


class ConfigLoader:
    """
    Minimal configuration loader that preserves existing behavior.
    - Loads JSON from the provided path and returns a dictionary.
    - Does not apply additional defaults or environment overrides by default.
    """

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as file_handle:
            return json.load(file_handle)

