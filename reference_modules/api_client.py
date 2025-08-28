from abc import ABC, abstractmethod
import requests
class APIClient(ABC): # pragma: no cover, abstract class
    @abstractmethod
    def send_request(self, data): # pragma: no cover, abstract method
        pass

'''
@brief OpenRouterClient module - Client for interacting with OpenRouter API, automatic API key management, advanced logging.
@details
- Sends requests and automatically switches API keys when rate-limited.
- Provides detailed logging for easier debugging.
- Inherits from APIClient and extends its functionality.
@constructor
- @param api_key_manager (APIKeyManager): Manages the pool of API keys.
- @param api_url (str): API endpoint URL.
- @param logger (Logger): Logger object for logging.
@method
- `send_request(payload: dict) -> dict`
    - @param payload (dict): Data to send to the API.
    - @return (dict): JSON response from the API.
    - @raises Exception: If the request fails or all keys are exhausted.
'''
class OpenRouterClient(APIClient):
    def __init__(self, api_key_manager, api_url, logger, requests_lib=requests):
        '''
        @brief Constructor for OpenRouterClient.
        @param api_key_manager (APIKeyManager): Manages API keys.
        @param api_url (str): API endpoint URL.
        @param logger (Logger): Logger for logging events.
        @param requests_lib (module): Requests library module (default: requests)
        '''
        self.api_key_manager = api_key_manager
        self.api_url = api_url
        self.logger = logger
        self.requests_lib = requests_lib

    def send_request(self, data):
        '''
        @brief Send a request to the OpenRouter API.
        @param data (dict): Payload to send to the API.
        @return (dict): Response from the API.
        @raises Exception: If all API keys are exhausted or request fails.
        '''
        last_error = None
        # Strategy: switch key immediately on 429; stop if a full cycle is exhausted.
        while True:
                key = self.api_key_manager.get_current_key()
                self.logger.info(f"Using API key {self.api_key_manager.current_index+1}/{len(self.api_key_manager.api_keys)}...")
                # Additional contextual logs requested by user
                try:
                    service_name = 'OpenRouter'
                    model_name = data.get('model') if isinstance(data, dict) else None
                    self.logger.info(f"Using Translation Service: {service_name}")
                    if model_name:
                        self.logger.info(f"Requested to model: {model_name}")
                except Exception:
              # Don't fail the request due to logging issues
                    pass      

                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                try:
                    response = self.requests_lib.post(
                        self.api_url, headers=headers, json=data, stream=True, timeout=60
                    )
                except requests.RequestException as e:
                    last_error = str(e)
                    self.logger.error(f"Connection error with key {self.api_key_manager.current_index+1}: {e}")
                    # No backoff/rotation on connection error per requirement
                    raise RuntimeError(f"API connection error: {e}")

                if response.status_code == 200:
                    return response

                if response.status_code == 429 or "Rate limit exceeded" in response.text:
                    # Only switch key if rate limit
                    last_error = response.text
                    self.logger.warning(f"Key {self.api_key_manager.current_index+1} rate-limited, switching...")
                    try:
                        self.api_key_manager.switch_to_next_key()
                    except RuntimeError:
                        # Completed a full cycle → exhausted
                        self.logger.error("🚫 All API keys are rate-limited/exhausted!")
                        raise RuntimeError(f"🚫 All API keys exhausted! Last error: {last_error}")
                    continue
                elif response.status_code >= 500:
                    # Server error: fail immediately (no backoff)
                    last_error = response.text
                    self.logger.error(f"API server error {response.status_code}: {response.text[:200]}")
                    raise RuntimeError(f"API server error {response.status_code}")
                else:
                    # Other client errors: fail immediately
                    last_error = response.text
                    self.logger.error(f"API error {response.status_code}: {response.text[:200]}")
                    raise RuntimeError(f"API error {response.status_code}")
