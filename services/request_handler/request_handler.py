import asyncio
from typing import Dict, Optional, Tuple

from services.common import error_codes
from services.key_manager.key_manager import APIKeyManager
from services.request_handler.retry import DefaultRetryPolicy, ExponentialBackoff

DEBUG_MODE = False

class RequestHandler:
    def __init__(self, api_client, key_manager: APIKeyManager, logger, config: Dict):
        self.api_client = api_client
        self.key_manager = key_manager
        self.logger = logger
        self.config = config
        self.retry_count = 0
        # Compose retry policy to mirror legacy behavior
        self._retry_policy = DefaultRetryPolicy(
            ExponentialBackoff(self.config.get("backoff_base", 2.0))
        )

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

        max_retries = self.config.get("max_retries", 3)
        while self._retry_policy.should_retry(self.retry_count, max_retries):
            try:
                # Send request and receive response as dict
                response = await self.api_client.send_request(data)
                self.logger.info("Translation request completed successfully")
                return error_codes.ERR_NONE, response
            except Exception as e:
                self.logger.error(f"Exception in translation request (attempt {self.retry_count + 1}): {str(e)}")
                # Log full exception details
                import traceback
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
                self.logger.error(f"Exception type: {type(e).__name__}")
                if hasattr(e, '__dict__'):
                    self.logger.error(f"Exception attributes: {e.__dict__}")
                
                self.retry_count += 1
                if not self._retry_policy.should_retry(self.retry_count, max_retries):
                    self.logger.error(f"Max retries exceeded ({self.retry_count} attempts)")
                    return error_codes.ERR_RETRY_MAX_EXCEEDED, None
                backoff = self._retry_policy.backoff.compute_delay_seconds(self.retry_count)
                self.logger.info(f"Retrying in {backoff:.1f}s (attempt {self.retry_count})")
                await self._retry_policy.wait_before_retry(self.retry_count)

        return error_codes.ERR_RETRY_MAX_EXCEEDED, None
