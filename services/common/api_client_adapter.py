from typing import Dict, Any
from .model_client import ModelClient
from .api_client import OpenRouterClient


class OpenRouterModelClient(ModelClient):
    """
    Adapter that exposes the legacy OpenRouterClient under the new ModelClient interface.
    Behavior is identical because it delegates directly to send_request().
    """

    def __init__(self, delegate: OpenRouterClient):
        self._delegate = delegate

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._delegate.send_request(payload)

