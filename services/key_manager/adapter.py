from typing import Dict, Optional
from .key_manager import APIKeyManager
from .interfaces import KeyProvider, KeySelectionStrategy


class DefaultKeySelectionStrategy(KeySelectionStrategy):
    """
    Default selection strategy that delegates to provider.get_next_available_key().
    Preserves existing behavior by using APIKeyManager's internal rotation logic.
    """

    async def select(self, provider: KeyProvider) -> Optional[Dict]:
        return await provider.get_next_available_key()


class APIKeyManagerProvider(KeyProvider):
    """
    Thin adapter wrapping the legacy APIKeyManager to the KeyProvider interface.
    """

    def __init__(self, manager: APIKeyManager):
        self.manager = manager

    async def get_next_available_key(self) -> Optional[Dict]:
        return await self.manager.get_next_available_key()

    async def report_key_error(self, key: str, error_code: int) -> None:
        await self.manager.report_key_error(key, error_code)

