"""
Error codes for the translation service request handling module.
"""

# Success code
ERR_NONE = 0

# Error codes for the translation framework
ERR_RETRY_MAX_EXCEEDED = 1001
ERR_VALIDATION_FAILED = 1002
ERR_STANDARDIZATION_FAILED = 1003
ERR_CONFIG_LOAD_FAILED = 1004
ERR_KEY_MANAGEMENT_FAILED = 1005
ERR_SCHEDULING_FAILED = 1006
ERR_REQUEST_FAILED = 1007

# Error messages
ERROR_MESSAGES = {
    ERR_NONE: "Success",
    ERR_RETRY_MAX_EXCEEDED: "Maximum retry attempts exceeded",
    ERR_VALIDATION_FAILED: "Validation failed",
    ERR_STANDARDIZATION_FAILED: "Standardization failed",
    ERR_CONFIG_LOAD_FAILED: "Configuration load failed",
    ERR_KEY_MANAGEMENT_FAILED: "Key management failed",
    ERR_SCHEDULING_FAILED: "Scheduling failed",
    ERR_REQUEST_FAILED: "Request failed"
}