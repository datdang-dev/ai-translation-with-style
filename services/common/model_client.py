from abc import ABC, abstractmethod
from typing import Dict, Any


class ModelClient(ABC): # pragma: no cover, interface
    @abstractmethod
    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

