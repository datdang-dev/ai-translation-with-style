# Test Module: api_client
# Purpose: Unit tests for OpenRouterClient interface
# Author: datdang
# Created: 2024-08-20
# Framework: pytest

import pytest
from unittest.mock import MagicMock, patch
import requests
from common_modules.api_client import OpenRouterClient

##################################### Global datas ####################################################
TEST_API_URL = "https://api.openrouter.ai"
TEST_API_KEYS = ["key1", "key2"]

##################################### Test `send_request` ##################################

'''
Equivalent class of send_request(data: dict) -> requests.Response

Test case    *  data              *  API Response     *  Key State        * Expected Result 
             *                    *                   *                   *                 
TC001        *  valid dict       *  200 OK           *  Valid key        *  Success - Returns response
TC002        *  valid dict       *  429 Rate limit   *  Has more keys    *  Success - Switches key and retries
TC003        *  valid dict       *  429 Rate limit   *  No more keys     *  Failure - All keys exhausted
TC004        *  valid dict       *  500 Server err   *  Valid key        *  Failure - Server error
TC005        *  valid dict       *  400 Client err   *  Valid key        *  Failure - Client error
TC006        *  invalid data     *  Connection err   *  Valid key        *  Failure - Connection error
TC007        *  non-dict         *  200 OK           *  Valid key        *  Success - Handles non-dict data
'''

# Test Description: Verify send_request returns response for successful request
# Test type: Success
# Test Case: TC001
def utest_send_request_success():
    # Test data
    data = {"model": "test-model", "content": "test"}
    requests_mock = expected_call_requests("success", "post", None)
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    response = api_client.send_request(data)

    # Check result
    assert response.status_code == 200
    assert response.text == "success"
    logger_mock.info.assert_any_call("Using Translation Service: OpenRouter")
    logger_mock.info.assert_any_call("Requested to model: test-model")

# Test Description: Verify send_request switches key and retries on rate limit
# Test type: Success
# Test Case: TC002
def utest_send_request_rate_limit():
    # Test data
    data = {"content": "test"}
    requests_mock = expected_call_requests("retry", "post", None)
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("retry", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    response = api_client.send_request(data)

    # Check result
    assert response.status_code == 200
    assert response.text == "success"
    api_key_manager_mock.switch_to_next_key.assert_called_once()  # Verify key was switched once
    assert api_key_manager_mock.get_current_key.call_count == 2  # Called twice: initial + after switch

# Test Description: Verify send_request fails when all keys are exhausted
# Test type: Failure
# Test Case: TC003
def utest_send_request_exhaust_keys():
    # Test data
    data = {"content": "test"}
    requests_mock = expected_call_requests("failed", "post", "rate_limit")
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("failed", "get_current_key", "exhausted")
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT and check result
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    with pytest.raises(RuntimeError, match="All API keys exhausted!"):
        api_client.send_request(data)

# Test Description: Verify send_request fails on server error
# Test type: Failure
# Test Case: TC004
def utest_send_request_server_error():
    # Test data
    data = {"content": "test"}
    requests_mock = expected_call_requests("failed", "post", "server")
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT and check result
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    with pytest.raises(RuntimeError, match="API server error 500"):
        api_client.send_request(data)

# Test Description: Verify send_request fails on client error
# Test type: Failure
# Test Case: TC005
def utest_send_request_client_error():
    # Test data
    data = {"content": "test"}
    requests_mock = expected_call_requests("failed", "post", "client")
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT and check result
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    with pytest.raises(RuntimeError, match="API error 400"):
        api_client.send_request(data)

# Test Description: Verify send_request fails on connection error and logs properly
# Test type: Failure
# Test Case: TC006
def utest_send_request_connection_error():
    # Test data
    data = {"content": "test"}
    requests_mock = expected_call_requests("failed", "post", "connection")
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT and check result
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    with pytest.raises(RuntimeError, match="API connection error"):
        api_client.send_request(data)
    
    # Verify error logging contains "Connection error"
    expected_log_message = f"Connection error with key {api_key_manager_mock.current_index+1}: connection error"
    logger_mock.error.assert_called_with(expected_log_message)

# Test Description: Verify logging errors during context logging don't break requests
# Test type: Error handling
# Covers api_client.py lines 57-59
def utest_connection_error_logging():
    # Test data
    data = {"model": "test-model"}
    requests_mock = expected_call_requests("success", "post", None)
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = MagicMock()
    
    # Make only the context logging calls raise exception
    def info_side_effect(msg):
        if "Using Translation Service" in msg or "Requested to model" in msg:
            raise Exception("Connection error")
        return None
    
    logger_mock.info.side_effect = info_side_effect
    
    # Call SUT
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    response = api_client.send_request(data)
    
    # Verify request still completed successfully despite logging error
    assert response.status_code == 200
    assert response.text == "success"
    
    # Verify error was logged
    logger_mock.error.assert_called_with("Connection error with key 1: Connection error")

# Test Description: Verify send_request handles non-dict data gracefully
# Test type: Success
# Test Case: TC007
def utest_send_request_non_dict_data():
    # Test data
    data = ["not a dict"]
    requests_mock = expected_call_requests("success", "post", None)
    api_key_manager_mock = expected_call_api_key_manager_get_current_key("success", "get_current_key", None)
    logger_mock = expected_call_logger_log("success", "info", None)

    # Call SUT
    api_client = OpenRouterClient(api_key_manager_mock, TEST_API_URL, logger_mock, requests_lib=requests_mock)
    response = api_client.send_request(data)

    # Check result
    assert response.status_code == 200
    assert not any("model" in str(call) for call in logger_mock.info.call_args_list)

##################################### END TEST #######################################################

######################################################################################################
# STUB/MOCK control
######################################################################################################

def expected_call_requests(instance: str, method_name: str, expected):
    """Create requests module stub with post method"""
    mock = MagicMock(name="requests")
    
    if instance == "success":
        mock_response = MagicMock(status_code=200, text="success")
        mock.post.return_value = mock_response
    elif instance == "default":
        mock_response = MagicMock(status_code=200, text="default")
        mock.post.return_value = mock_response
    elif instance == "retry":
        # First call: rate limit, Second call: success
        responses = [
            MagicMock(status_code=429, text="rate limit"),
            MagicMock(status_code=200, text="success")
        ]
        mock.post.side_effect = responses
    elif instance == "failed":
        error_responses = {
            "rate_limit": MagicMock(status_code=429, text="rate limit"),
            "server": MagicMock(status_code=500, text="server error"),
            "client": MagicMock(status_code=400, text="client error"),
            "connection": requests.RequestException("connection error")
        }
        if expected in error_responses:
            if isinstance(error_responses[expected], Exception):
                mock.post.side_effect = error_responses[expected]
            else:
                mock.post.return_value = error_responses[expected]
    else:
        raise ValueError(f"⚠️ Call instance {instance} not defined")
    return mock

def expected_call_api_key_manager_get_current_key(instance: str, method_name: str, expected):
    """Create mock for ApiKeyManager with simplified key management"""
    mock = MagicMock()
    
    if instance == "success":
        getattr(mock, method_name).return_value = TEST_API_KEYS[0]
    elif instance == "default":
        getattr(mock, method_name).return_value = TEST_API_KEYS[0]
        mock.switch_to_next_key.return_value = None  # Allow key switch
    elif instance == "retry":
        getattr(mock, method_name).side_effect = TEST_API_KEYS  # Return keys in sequence
        mock.switch_to_next_key.return_value = None  # Allow key switch
    elif instance == "failed":
        if expected == "exhausted":
            mock.switch_to_next_key.side_effect = RuntimeError("All keys exhausted")
        getattr(mock, method_name).return_value = TEST_API_KEYS[-1]
    else:
        raise ValueError(f"⚠️ Call instance {instance} not defined")
    return mock

def expected_call_logger_log(instance: str, method_name: str, expected):
    mock = MagicMock()

    if instance == "success":
        getattr(mock, method_name).return_value = None
    elif instance == "default":
        getattr(mock, method_name).return_value = None
    elif instance == "failed":
        getattr(mock, method_name).side_effect = Exception("Logger failed")
    else:
        raise ValueError(f"⚠️ Call instance {instance} not defined")
    return mock