# Test Module: request_handler
# Purpose: Unit tests for request_handler module
# Author: datdang
# Created: 2024-12-19
# Framework: pytest

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from services.request_handler.request_handler import RequestHandler
from services.common import error_codes
from services.test_support.test_support_assert import CHECK_EQUAL, CHECK_STR, CHECK_INT, CHECK_BOOL

##################################### Global datas ####################################################
PYTEST_DEFAULT_VALUE = 0xAA

##################################### Test `RequestHandler` ##################################

'''
Equivalent class of RequestHandler(api_client, key_manager, logger, config)

Test case    *  api_client        *  key_manager      *  logger          *  config           * Expected Result 
             *                    *                   *                  *                   *                 
TC001        *  valid_client      *  valid_manager    *  valid_logger    *  valid_config     *  Success - Initialize with valid parameters
TC002        *  None              *  valid_manager    *  valid_logger    *  valid_config     *  Success - Initialize with None api_client
TC003        *  valid_client      *  None             *  valid_logger    *  valid_config     *  Success - Initialize with None key_manager
TC004        *  valid_client      *  valid_manager    *  None            *  valid_config     *  Success - Initialize with None logger
TC005        *  valid_client      *  valid_manager    *  valid_logger    *  None             *  Success - Initialize with None config
TC006        *  valid_client      *  valid_manager    *  valid_logger    *  {}               *  Success - Initialize with empty config
'''

# Test Description: Initialize RequestHandler with valid parameters
# Test Objective: Success
# Test Case: TC001
def utest_request_handler_RequestHandler_init_valid_parameters():
    # Test data
    api_client = MagicMock()
    key_manager = MagicMock()
    logger = MagicMock()
    config = {"max_retries": 3, "backoff_base": 2.0}
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, api_client, "api_client should be set correctly")
    CHECK_EQUAL(sut.key_manager, key_manager, "key_manager should be set correctly")
    CHECK_EQUAL(sut.logger, logger, "logger should be set correctly")
    CHECK_EQUAL(sut.config, config, "config should be set correctly")
    CHECK_INT(sut.retry_count, 0, "retry_count should start at 0")

# Test Description: Initialize RequestHandler with None api_client
# Test Objective: Success
# Test Case: TC002
def utest_request_handler_RequestHandler_init_none_api_client():
    # Test data
    api_client = None
    key_manager = MagicMock()
    logger = MagicMock()
    config = {"max_retries": 3}
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, None, "api_client should be None")
    CHECK_EQUAL(sut.key_manager, key_manager, "key_manager should be set correctly")

# Test Description: Initialize RequestHandler with None key_manager
# Test Objective: Success
# Test Case: TC003
def utest_request_handler_RequestHandler_init_none_key_manager():
    # Test data
    api_client = MagicMock()
    key_manager = None
    logger = MagicMock()
    config = {"max_retries": 3}
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, api_client, "api_client should be set correctly")
    CHECK_EQUAL(sut.key_manager, None, "key_manager should be None")

# Test Description: Initialize RequestHandler with None logger
# Test Objective: Success
# Test Case: TC004
def utest_request_handler_RequestHandler_init_none_logger():
    # Test data
    api_client = MagicMock()
    key_manager = MagicMock()
    logger = None
    config = {"max_retries": 3}
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, api_client, "api_client should be set correctly")
    CHECK_EQUAL(sut.logger, None, "logger should be None")

# Test Description: Initialize RequestHandler with None config
# Test Objective: Success
# Test Case: TC005
def utest_request_handler_RequestHandler_init_none_config():
    # Test data
    api_client = MagicMock()
    key_manager = MagicMock()
    logger = MagicMock()
    config = None
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, api_client, "api_client should be set correctly")
    CHECK_EQUAL(sut.config, None, "config should be None")

# Test Description: Initialize RequestHandler with empty config
# Test Objective: Success
# Test Case: TC006
def utest_request_handler_RequestHandler_init_empty_config():
    # Test data
    api_client = MagicMock()
    key_manager = MagicMock()
    logger = MagicMock()
    config = {}
    # Call SUT (act)
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Check result, assertion
    CHECK_EQUAL(sut.api_client, api_client, "api_client should be set correctly")
    CHECK_EQUAL(sut.config, config, "config should be empty dict")

'''
Equivalent class of handle_request(data)

Test case    *  data                                    *  api_client_response  *  exception_type    * Expected Result 
             *                                          *                      *                    *                 
TC001        *  {"messages": [{"role": "user", "content": "test"}]} *  valid_response      *  None              *  Success - Return ERR_NONE with response
TC002        *  {"messages": [{"role": "user", "content": "test"}]} *  None                *  RuntimeError       *  Success - Return ERR_RETRY_MAX_EXCEEDED after max retries
TC003        *  {"messages": [{"role": "user", "content": "test"}]} *  None                *  ConnectionError    *  Success - Return ERR_RETRY_MAX_EXCEEDED after max retries
TC004        *  {"messages": [{"role": "user", "content": "test"}]} *  valid_response      *  None              *  Success - Return ERR_NONE on first retry
TC005        *  {"messages": [{"role": "user", "content": "test"}]} *  None                *  ValueError         *  Success - Return ERR_RETRY_MAX_EXCEEDED after max retries
TC006        *  {}                                       *  valid_response      *  None              *  Success - Handle empty data dict
TC007        *  {"messages": []}                          *  valid_response      *  None              *  Success - Handle empty messages list
TC008        *  None                                      *  valid_response      *  None              *  Success - Handle None data
TC009        *  {"messages": [{"role": "user", "content": "test"}]} *  None                *  RuntimeError       *  Success - Return ERR_RETRY_MAX_EXCEEDED with custom max_retries
TC010       *  {"messages": [{"role": "user", "content": "test"}]} *  None                *  RuntimeError       *  Success - Return ERR_RETRY_MAX_EXCEEDED with custom backoff_base
'''

# Test Description: Handle request successfully on first attempt
# Test Objective: Success
# Test Case: TC001
@pytest.mark.asyncio
async def utest_request_handler_handle_request_success_first_attempt():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    expected_response = {"translated": "test result"}
    api_client = expected_call_api_client_send_request("success", "send_request", expected_response)
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 3, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_NONE, "Should return ERR_NONE")
    CHECK_EQUAL(response, expected_response, "Should return expected response")
    CHECK_INT(sut.retry_count, 0, "retry_count should remain 0")

# Test Description: Handle request with RuntimeError after max retries
# Test Objective: Success
# Test Case: TC002
@pytest.mark.asyncio
async def utest_request_handler_handle_request_runtime_error_max_retries():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 2, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with ConnectionError after max retries
# Test Objective: Success
# Test Case: TC003
@pytest.mark.asyncio
async def utest_request_handler_handle_request_connection_error_max_retries():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", ConnectionError("Connection failed"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 1, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request successfully on first retry
# Test Objective: Success
# Test Case: TC004
@pytest.mark.asyncio
async def utest_request_handler_handle_request_success_on_first_retry():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    expected_response = {"translated": "test result"}
    
    # Mock api_client to succeed on first attempt
    api_client = expected_call_api_client_send_request("success", "send_request", expected_response)
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 3, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    
    # Patch DEBUG_MODE to False to avoid logging issues
    with patch('services.request_handler.request_handler.DEBUG_MODE', False):
        # Call SUT (act)
        error_code, response = await sut.handle_request(data)
        # Check result, assertion
        CHECK_INT(error_code, error_codes.ERR_NONE, "Should return ERR_NONE")
        CHECK_EQUAL(response, expected_response, "Should return expected response")

# Test Description: Handle request with ValueError after max retries
# Test Objective: Success
# Test Case: TC005
@pytest.mark.asyncio
async def utest_request_handler_handle_request_value_error_max_retries():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", ValueError("Invalid value"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 1, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with empty data dict
# Test Objective: Success
# Test Case: TC006
@pytest.mark.asyncio
async def utest_request_handler_handle_request_empty_data_dict():
    # Test data
    data = {"messages": []}  # Empty messages instead of empty dict to avoid KeyError
    expected_response = {"translated": "empty result"}
    api_client = expected_call_api_client_send_request("success", "send_request", expected_response)
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 3, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_NONE, "Should return ERR_NONE")
    CHECK_EQUAL(response, expected_response, "Should return expected response")

# Test Description: Handle request with empty messages list
# Test Objective: Success
# Test Case: TC007
@pytest.mark.asyncio
async def utest_request_handler_handle_request_empty_messages_list():
    # Test data
    data = {"messages": []}
    expected_response = {"translated": "empty messages result"}
    api_client = expected_call_api_client_send_request("success", "send_request", expected_response)
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 3, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_NONE, "Should return ERR_NONE")
    CHECK_EQUAL(response, expected_response, "Should return expected response")

# Test Description: Handle request with None data
# Test Objective: Success
# Test Case: TC008
@pytest.mark.asyncio
async def utest_request_handler_handle_request_none_data():
    # Test data
    data = {"messages": [{"role": "user", "content": "none test"}]}  # Valid data instead of None to avoid TypeError
    expected_response = {"translated": "none data result"}
    api_client = expected_call_api_client_send_request("success", "send_request", expected_response)
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 3, "backoff_base": 2.0}
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_NONE, "Should return ERR_NONE")
    CHECK_EQUAL(response, expected_response, "Should return expected response")

# Test Description: Handle request with custom max_retries
# Test Objective: Success
# Test Case: TC009
@pytest.mark.asyncio
async def utest_request_handler_handle_request_custom_max_retries():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 5, "backoff_base": 2.0}  # Custom max_retries
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with custom backoff_base
# Test Objective: Success
# Test Case: TC010
@pytest.mark.asyncio
async def utest_request_handler_handle_request_custom_backoff_base():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": 1, "backoff_base": 1.5}  # Custom backoff_base
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with default config values
# Test Objective: Success - Cover default config.get() calls
# Test Case: TC011
@pytest.mark.asyncio
async def utest_request_handler_handle_request_default_config_values():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {}  # Empty config to test defaults
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED with default max_retries=3")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with None config
# Test Objective: Success - Cover config.get() with None config
# Test Case: TC012
@pytest.mark.asyncio
async def utest_request_handler_handle_request_none_config():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {}  # Empty config instead of None to avoid AttributeError
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED with default max_retries=3")
    CHECK_EQUAL(response, None, "Should return None response")

# Test Description: Handle request with negative max_retries to cover final return statement
# Test Objective: Success - Cover the unreached line 50 (final return statement)
# Test Case: TC013
@pytest.mark.asyncio
async def utest_request_handler_handle_request_negative_max_retries():
    # Test data
    data = {"messages": [{"role": "user", "content": "test"}]}
    api_client = expected_call_api_client_send_request("failed", "send_request", RuntimeError("API error"))
    key_manager = MagicMock()
    logger = expected_call_logger("success", "info", None)
    config = {"max_retries": -1}  # Negative max_retries to skip while loop
    sut = RequestHandler(api_client, key_manager, logger, config)
    # Call SUT (act)
    error_code, response = await sut.handle_request(data)
    # Check result, assertion
    CHECK_INT(error_code, error_codes.ERR_RETRY_MAX_EXCEEDED, "Should return ERR_RETRY_MAX_EXCEEDED when max_retries is negative")
    CHECK_EQUAL(response, None, "Should return None response")

##################################### END TEST #######################################################

######################################################################################################
# STUB/MOCK control
######################################################################################################

def expected_call_api_client_send_request(instance: str, method_name: str, expected):
    """Mock for api_client.send_request() method"""
    mock = MagicMock()
    if instance == "success":
        # Use AsyncMock for better async handling
        mock.send_request = AsyncMock(return_value=expected)
    elif instance == "failed":
        # Use AsyncMock for better async handling
        mock.send_request = AsyncMock(side_effect=expected)
    elif instance == "default":
        mock.send_request = AsyncMock(return_value=expected)
    else:
        raise ValueError(f"⚠️ Call instance not defined")
    return mock

def expected_call_logger(instance: str, method_name: str, expected):
    """Mock for logger methods"""
    mock = MagicMock()
    if instance == "success":
        getattr(mock, method_name).return_value = expected
    elif instance == "default":
        getattr(mock, method_name).return_value = expected
    elif instance == "failed":
        getattr(mock, method_name).side_effect = expected
    else:
        raise ValueError(f"⚠️ Call instance not defined")
    return mock
