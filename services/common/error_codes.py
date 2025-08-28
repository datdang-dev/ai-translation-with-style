"""
Error codes for the translation service request handling module.

This module preserves the original integer constants and messages to avoid
behavior changes, while adding a small typed layer (enum and exceptions)
that other modules can opt into gradually.
"""

from enum import IntEnum
from typing import Optional

# Success code
ERR_NONE = 0

# Error codes
CHUNK_MALFORMED = 1001
ERR_LIMITED_ALL_KEYS = 1002
ERR_RETRY_MAX_EXCEEDED = 1003
ERR_CONNECTION_FAILED = 1004
ERR_SERVER_ERROR = 1005
ERR_CLIENT_ERROR = 1006

# Error messages
ERROR_MESSAGES = {
    ERR_NONE: "Success",
    CHUNK_MALFORMED: "Chunk is malformed",
    ERR_LIMITED_ALL_KEYS: "All API keys are rate-limited/exhausted",
    ERR_RETRY_MAX_EXCEEDED: "Maximum retry attempts exceeded",
    ERR_CONNECTION_FAILED: "Connection to API failed",
    ERR_SERVER_ERROR: "API server error",
    ERR_CLIENT_ERROR: "API client error"
}


class ErrorCode(IntEnum):
    """Typed mirror of the legacy integer error codes."""
    ERR_NONE = ERR_NONE
    CHUNK_MALFORMED = CHUNK_MALFORMED
    ERR_LIMITED_ALL_KEYS = ERR_LIMITED_ALL_KEYS
    ERR_RETRY_MAX_EXCEEDED = ERR_RETRY_MAX_EXCEEDED
    ERR_CONNECTION_FAILED = ERR_CONNECTION_FAILED
    ERR_SERVER_ERROR = ERR_SERVER_ERROR
    ERR_CLIENT_ERROR = ERR_CLIENT_ERROR


def get_message(code: int) -> str:
    """Return the legacy error message for a given code."""
    return ERROR_MESSAGES.get(code, "Unknown error")


class ServiceError(Exception):
    """
    Typed exception carrying an error code. The string representation remains
    the legacy message, preserving current logs when used.
    """

    def __init__(self, code: int, detail: Optional[str] = None):
        self.code = int(code)
        self.message = get_message(self.code)
        self.detail = detail
        text = self.message if detail is None else f"{self.message} | {detail}"
        super().__init__(text)


class ChunkMalformedError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(CHUNK_MALFORMED, detail)


class LimitedAllKeysError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ERR_LIMITED_ALL_KEYS, detail)


class RetryMaxExceededError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ERR_RETRY_MAX_EXCEEDED, detail)


class ConnectionFailedError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ERR_CONNECTION_FAILED, detail)


class ServerError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ERR_SERVER_ERROR, detail)


class ClientError(ServiceError):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ERR_CLIENT_ERROR, detail)


def exception_from_http_status(status_code: int, detail: Optional[str] = None) -> ServiceError:
    """Map an HTTP status to a typed ServiceError, preserving legacy codes."""
    if status_code == 429:
        return LimitedAllKeysError(detail)
    if 500 <= status_code < 600:
        return ServerError(detail)
    if 400 <= status_code < 500:
        return ClientError(detail)
    return ServiceError(ERR_NONE, detail)
