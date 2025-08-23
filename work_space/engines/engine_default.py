from typing import List
import os
from common_modules.engines.base_engine import BaseEngineProcessor
from common_modules.logger import Logger

class DefaultEngineProcessor(BaseEngineProcessor):
    """A minimal default engine used for examples and tests.

    - preprocess: writes a single canonical block to the configured text_to_translate_folder
    - postprocess: reads translated merged file (if any) and returns paths (no-op)
    - send_demo_request(api_client): demonstrates how to send a simple request via
      the project's API client; it will only attempt to call the client's public
      interface if an object is provided. This method does not perform network
      calls by itself during preprocess/postprocess.
    """
    def __init__(self, logger: Logger = None):
        super().__init__(logger or Logger("default_engine").get_logger())

    @property
    def needs_preprocess(self) -> bool:
        return True

    def preprocess(self, engine_input_folder: str, text_to_translate_folder: str) -> List[str]:
        os.makedirs(text_to_translate_folder, exist_ok=True)
        sample_path = os.path.join(text_to_translate_folder, "part_1.txt")
        # Create a single canonical block in the framework format
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write("---------0\nHello from DefaultEngine!\n")
        self.logger.info(f"DefaultEngine: wrote sample canonical file: {sample_path}")
        return [sample_path]

    def postprocess(self, text_to_translate_folder: str, translate_output_folder: str) -> List[str]:
        # Minimal no-op postprocess: if merged translated file exists, log it
        merged_path = os.path.join(translate_output_folder, "merged_translated.txt")
        outputs = []
        if os.path.exists(merged_path):
            self.logger.info(f"DefaultEngine: found merged translated file: {merged_path}")
            outputs.append(merged_path)
        else:
            self.logger.info("DefaultEngine: no merged translated file to apply. Skipping.")
        return outputs

    def send_demo_request(self, api_client) -> dict:
        """Demonstration helper: if given an api_client with a compatible method,
        send a minimal request and return the client's response. This function is
        safe: it checks for the client's interface and will not attempt raw network
        calls on its own.
        """
        if api_client is None:
            self.logger.info("No api_client provided for demo request.")
            return {}

        # The project's OpenRouterClient exposes a method `send_request` (or similar).
        # We'll try to call a commonly named method. Adjust according to actual API.
        payload = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [{"role": "user", "content": "Say hello in Vietnamese."}]
        }

        # Try a few likely method names safely
        for method_name in ("send_request", "create_completion", "chat_completion"):
            method = getattr(api_client, method_name, None)
            if callable(method):
                try:
                    self.logger.info(f"DefaultEngine: sending demo request via {method_name}()")
                    resp = method(payload)
                    return {"via": method_name, "response": resp}
                except Exception as e:
                    self.logger.warning(f"Demo request via {method_name} failed: {e}")
                    return {"error": str(e), "via": method_name}

        self.logger.info("API client has no compatible demo method; skipping demo request.")
        return {}
