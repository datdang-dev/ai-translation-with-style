from abc import ABC, abstractmethod
from typing import Dict, Any
import json


class ResponseParser(ABC): # pragma: no cover, interface
    @abstractmethod
    def extract_message_content(self, response: Dict[str, Any]) -> str:
        pass


class ResponseValidator(ABC): # pragma: no cover, interface
    @abstractmethod
    def is_valid(self, response: Dict[str, Any]) -> bool:
        pass


class DefaultResponseValidator(ResponseValidator):
    def is_valid(self, response: Dict[str, Any]) -> bool:
        return isinstance(response, dict)


class DefaultResponseParser(ResponseParser):
    """
    Mirrors current extraction used in TranslationOrchestrator.translate_text.
    Not wired yet to avoid behavior changes; provided for future use.
    """

    def extract_message_content(self, response: Dict[str, Any]) -> str:
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")

    @staticmethod
    def extract_json_from_backticks(text: str) -> str:
        stripped_content = text.strip()
        if stripped_content.startswith("```json"):
            body = stripped_content[7:].strip()
            return body[:-3] if body.endswith("```") else body
        if stripped_content.startswith("```"):
            body = stripped_content[3:].strip()
            return body[:-3] if body.endswith("```") else body
        return stripped_content

    @staticmethod
    def try_parse_json(text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": f"Invalid response format: {text}"}

