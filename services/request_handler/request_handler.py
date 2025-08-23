import asyncio
from typing import Dict, Optional, Tuple

from services.common import error_codes
from services.key_manager.key_manager import APIKeyManager

DEBUG_MODE = True

class RequestHandler:
    def __init__(self, api_client, key_manager: APIKeyManager, logger, config: Dict):
        self.api_client = api_client
        self.key_manager = key_manager
        self.logger = logger
        self.config = config
        self.retry_count = 0

    async def handle_request(self, data: Dict) -> Tuple[int, Optional[Dict]]:
        """
        Handle translation request
        :param data: Processed data including prompt and content to translate
        :return: Tuple of (error_code, response)
        """
        self.logger.info("Start translation request")
        
        self.retry_count = 0

        if DEBUG_MODE:
            # ----------[DEBUG: LOG the requested prompts]----------#
            # Log the full prompt and all text sent to the model
            prompt_log = "\n\n--- PROMPT TO MODEL ---\n\n"
            for msg in data['messages']:
                prompt_log += f"[{msg['role'].upper()}] {msg['content']}\n"
            self.logger.info(prompt_log)

        while self.retry_count <= self.config.get("max_retries", 3):
            try:
                # Send request and receive response as dict
                response = await self.api_client.send_request(data)
                self.logger.info("Translation request completed successfully")
                return error_codes.ERR_NONE, response
            except Exception as e:
                self.logger.error(f"Exception in translation request: {str(e)}")
                self.retry_count += 1
                if self.retry_count > self.config.get("max_retries", 3):
                    return error_codes.ERR_RETRY_MAX_EXCEEDED, None
                backoff = self.config.get("backoff_base", 2.0) ** self.retry_count
                await asyncio.sleep(backoff)

        return error_codes.ERR_RETRY_MAX_EXCEEDED, None
