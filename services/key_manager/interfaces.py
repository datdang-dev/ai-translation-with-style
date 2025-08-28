from abc import ABC, abstractmethod
from typing import Dict, Optional


class KeyProvider(ABC): # pragma: no cover, interface
    @abstractmethod
    async def get_next_available_key(self) -> Optional[Dict]:
        pass

    @abstractmethod
    async def report_key_error(self, key: str, error_code: int) -> None:
        pass


class KeyStateStore(ABC): # pragma: no cover, interface
    @abstractmethod
    async def get_state(self, key: str) -> Dict:
        pass

    @abstractmethod
    async def set_state(self, key: str, state: Dict) -> None:
        pass


class KeySelectionStrategy(ABC): # pragma: no cover, interface
    @abstractmethod
    async def select(self, provider: KeyProvider) -> Optional[Dict]:
        pass

