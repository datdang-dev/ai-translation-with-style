"""
Error codes for the translation service request handling module.
"""

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