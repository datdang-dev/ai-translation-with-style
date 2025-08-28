import json
import copy
from typing import Dict, Any

from services.common.model_client import ModelClient
from services.common.response import DefaultResponseParser, DefaultResponseValidator
from services.common.error_codes import ERR_NONE


class TranslationService:
    """
    Application-level orchestrator that mirrors current behavior in a single place.
    Not yet wired to replace existing applet orchestrator.
    """

    def __init__(self, model_client: ModelClient, logger, config: Dict[str, Any]):
        self.model_client = model_client
        self.logger = logger
        self.config = config
        self._parser = DefaultResponseParser()
        self._validator = DefaultResponseValidator()

    async def translate_text_dict(self, text_dict: Dict[str, str]) -> Dict[str, Any]:
        data = copy.deepcopy(self.config)
        if 'messages' not in data or not isinstance(data['messages'], list):
            data['messages'] = []

        json_text = json.dumps(text_dict, ensure_ascii=False, indent=2)
        data['messages'].extend([
            {
                'role': 'user',
                'content': "Now below is the text block you must translate, let's begin translate the text inside the triple backticks block: \n " + "\n```\n" + json_text + "\n```\n"
            }
        ])
        data['stream'] = True

        response = await self.model_client.send(data)
        if not self._validator.is_valid(response):
            return {"error": "Invalid response"}

        translated_content = self._parser.extract_message_content(response)
        stripped = self._parser.extract_json_from_backticks(translated_content)
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {"error": f"Invalid response format: {translated_content}"}
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON response: {translated_content}"}

