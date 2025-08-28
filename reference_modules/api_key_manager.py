'''
@brief APIKeyManager module - Manages a pool of API keys and handles key rotation.
@details
- Provides current API key and rotates to next key when needed.
@constructor
- @param api_keys (list): List of API keys.
@method
- `get_current_key() -> str`
    - @return (str): The current API key.
- `switch_to_next_key() -> None`
    - @return None
    - @raises RuntimeError: If all API keys are exhausted.
'''
class APIKeyManager:
    def __init__(self, api_keys):
        '''
        @brief Constructor for APIKeyManager.
        @param api_keys (list): List of API keys.
        '''
        self.api_keys = api_keys
        self.current_index = 0

    def get_current_key(self):
        '''
        @brief Returns the current API key.
        @return (str): The current API key.
        '''
        return self.api_keys[self.current_index]

    def switch_to_next_key(self):
        '''
        @brief Switches to the next API key in the pool.
        @return None
        @raises RuntimeError: If all API keys are exhausted.
        '''
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        if self.current_index == 0:
            raise RuntimeError("🚫 All API keys exhausted!")
