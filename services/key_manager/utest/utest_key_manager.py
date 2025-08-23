# Test Module: key_manager
# Purpose: Unit tests for key_manager module
# Author: datdang
# Created: 2024-12-19
# Framework: pytest

import pytest
from unittest.mock import MagicMock, patch
import asyncio
import time
from services.key_manager.key_manager import KeyStatus, APIKeyManager
from services.test_support.test_support_assert import CHECK_EQUAL, CHECK_STR, CHECK_INT, CHECK_BOOL

##################################### Global datas ####################################################
PYTEST_DEFAULT_VALUE = 0xAA

##################################### Test `KeyStatus` ##################################

'''
Equivalent class of KeyStatus (enum class)

Test case    *  Description                    * Expected Result 
             *                                *                 
TC001        *  ACTIVE status value           *  Success - ACTIVE = "active"
TC002        *  RATE_LIMITED status value     *  Success - RATE_LIMITED = "rate_limited"
TC003        *  ERROR status value            *  Success - ERROR = "error"
'''

# Test Description: Verify KeyStatus enum values
# Test Objective: Success
# Test Case: TC001
def utest_key_manager_KeyStatus_ACTIVE_value():
    # Test data
    expected_value = "active"
    # Call SUT (act)
    act = KeyStatus.ACTIVE
    # Check result, assertion
    CHECK_STR(act, expected_value, "KeyStatus.ACTIVE should be 'active'")

# Test Description: Verify KeyStatus enum values
# Test Objective: Success
# Test Case: TC002
def utest_key_manager_KeyStatus_RATE_LIMITED_value():
    # Test data
    expected_value = "rate_limited"
    # Call SUT (act)
    act = KeyStatus.RATE_LIMITED
    # Check result, assertion
    CHECK_STR(act, expected_value, "KeyStatus.RATE_LIMITED should be 'rate_limited'")

# Test Description: Verify KeyStatus enum values
# Test Objective: Success
# Test Case: TC003
def utest_key_manager_KeyStatus_ERROR_value():
    # Test data
    expected_value = "error"
    # Call SUT (act)
    act = KeyStatus.ERROR
    # Check result, assertion
    CHECK_STR(act, expected_value, "KeyStatus.ERROR should be 'error'")

##################################### Test `APIKeyManager` ##################################

'''
Equivalent class of APIKeyManager(api_keys, max_retries, backoff_base, max_requests_per_minute)

Test case    *  api_keys           *  max_retries  *  backoff_base  *  max_requests_per_minute  * Expected Result 
             *                     *              *                *                          *                 
TC001        *  ["key1", "key2"]   *  3           *  2.0           *  20                      *  Success - Initialize with valid parameters
TC002        *  []                 *  3           *  2.0           *  20                      *  Success - Initialize with empty keys list
TC003        *  ["key1"]           *  0           *  1.5           *  10                      *  Success - Initialize with custom parameters
TC004        *  None               *  3           *  2.0           *  20                      *  Failure - TypeError for None api_keys
'''

# Test Description: Initialize APIKeyManager with valid parameters
# Test Objective: Success
# Test Case: TC001
def utest_key_manager_APIKeyManager_init_valid_parameters():
    # Test data
    api_keys = ["key1", "key2"]
    max_retries = 3
    backoff_base = 2.0
    max_requests_per_minute = 20
    # Call SUT (act)
    sut = APIKeyManager(api_keys, max_retries, backoff_base, max_requests_per_minute)
    # Check result, assertion
    CHECK_INT(len(sut.keys), 2, "Should have 2 keys")
    CHECK_INT(sut.max_retries, max_retries, "max_retries should match")
    CHECK_EQUAL(sut.backoff_base, backoff_base, "backoff_base should match")
    CHECK_INT(sut.max_requests_per_minute, max_requests_per_minute, "max_requests_per_minute should match")
    CHECK_INT(sut.current_index, 0, "current_index should start at 0")
    CHECK_STR(sut.keys[0]['key'], "key1", "First key should be 'key1'")
    CHECK_STR(sut.keys[0]['status'], KeyStatus.ACTIVE, "First key status should be ACTIVE")
    CHECK_STR(sut.keys[1]['key'], "key2", "Second key should be 'key2'")
    CHECK_STR(sut.keys[1]['status'], KeyStatus.ACTIVE, "Second key status should be ACTIVE")

# Test Description: Initialize APIKeyManager with empty keys list
# Test Objective: Success
# Test Case: TC002
def utest_key_manager_APIKeyManager_init_empty_keys():
    # Test data
    api_keys = []
    # Call SUT (act)
    sut = APIKeyManager(api_keys)
    # Check result, assertion
    CHECK_INT(len(sut.keys), 0, "Should have 0 keys")
    CHECK_INT(sut.current_index, 0, "current_index should be 0")

# Test Description: Initialize APIKeyManager with custom parameters
# Test Objective: Success
# Test Case: TC003
def utest_key_manager_APIKeyManager_init_custom_parameters():
    # Test data
    api_keys = ["key1"]
    max_retries = 0
    backoff_base = 1.5
    max_requests_per_minute = 10
    # Call SUT (act)
    sut = APIKeyManager(api_keys, max_retries, backoff_base, max_requests_per_minute)
    # Check result, assertion
    CHECK_INT(len(sut.keys), 1, "Should have 1 key")
    CHECK_INT(sut.max_retries, max_retries, "max_retries should match")
    CHECK_EQUAL(sut.backoff_base, backoff_base, "backoff_base should match")
    CHECK_INT(sut.max_requests_per_minute, max_requests_per_minute, "max_requests_per_minute should match")

# Test Description: Initialize APIKeyManager with None api_keys
# Test Objective: Failure
# Test Case: TC004
def utest_key_manager_APIKeyManager_init_none_api_keys():
    # Test data
    api_keys = None
    # Call SUT (act) and check exception
    with pytest.raises(TypeError):
        APIKeyManager(api_keys)

'''
Equivalent class of get_next_available_key()

Test case    *  Description                    * Expected Result 
             *                                *                 
TC001        *  All keys available            *  Success - Return first available key
TC002        *  All keys rate limited         *  Success - Return None
TC003        *  All keys in error state       *  Success - Return None
TC004        *  Mixed key states              *  Success - Return first available key
TC005        *  Rate limit exceeded           *  Success - Return None when all keys exceed rate limit
TC006        *  All keys unavailable after rotation *  Success - Return None after checking all keys
TC007        *  Empty keys list               *  Success - Return None when no keys available
TC008        *  All keys fail conditions     *  Success - Return None after for loop completes
'''

# Test Description: Get next available key when all keys are available
# Test Objective: Success
# Test Case: TC001
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_all_keys_available():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys)
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is not None, True, "Should return a key")
    CHECK_STR(result['key'], "key1", "Should return first key")
    CHECK_STR(result['status'], KeyStatus.ACTIVE, "Key status should be ACTIVE")
    CHECK_INT(len(result['timestamps']), 1, "Should have 1 timestamp")

# Test Description: Get next available key when all keys are rate limited
# Test Objective: Success
# Test Case: TC002
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_all_keys_rate_limited():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys)
    # Setup - mark all keys as rate limited with past retry time
    for key_info in sut.keys:
        key_info['status'] = KeyStatus.RATE_LIMITED
        key_info['next_retry_time'] = time.time() - 1  # Past time to trigger rotation
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None when all keys rate limited")

# Test Description: Get next available key when all keys are in error state
# Test Objective: Success
# Test Case: TC003
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_all_keys_error():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys)
    # Setup - mark all keys as error
    for key_info in sut.keys:
        key_info['status'] = KeyStatus.ERROR
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None when all keys in error state")

# Test Description: Get next available key with mixed key states
# Test Objective: Success
# Test Case: TC004
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_mixed_key_states():
    # Test data
    api_keys = ["key1", "key2", "key3"]
    sut = APIKeyManager(api_keys)
    # Setup - mixed states
    sut.keys[0]['status'] = KeyStatus.RATE_LIMITED
    sut.keys[1]['status'] = KeyStatus.ACTIVE
    sut.keys[2]['status'] = KeyStatus.ERROR
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is not None, True, "Should return a key")
    CHECK_STR(result['key'], "key2", "Should return the active key")
    CHECK_STR(result['status'], KeyStatus.ACTIVE, "Returned key should be ACTIVE")

# Test Description: Get next available key when rate limit exceeded
# Test Objective: Success
# Test Case: TC005
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_rate_limit_exceeded():
    # Test data
    api_keys = ["key1"]
    sut = APIKeyManager(api_keys, max_requests_per_minute=2)
    # Setup - add timestamps to exceed rate limit
    sut.keys[0]['timestamps'] = [time.time() - 30, time.time() - 20]  # Recent timestamps
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None when rate limit exceeded")

# Test Description: Get next available key when all keys are not available after rotation
# Test Objective: Success
# Test Case: TC006
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_all_unavailable_after_rotation():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_requests_per_minute=2)
    # Setup - all keys have exceeded rate limit
    for key_info in sut.keys:
        key_info['timestamps'] = [time.time() - 30, time.time() - 20]  # Recent timestamps
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None after checking all keys")

# Test Description: Get next available key with empty keys list
# Test Objective: Success
# Test Case: TC007
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_empty_keys_list():
    # Test data
    api_keys = []
    sut = APIKeyManager(api_keys)
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None when no keys available")

# Test Description: Get next available key when all keys fail conditions
# Test Objective: Success - Cover return None after for loop
# Test Case: TC008
@pytest.mark.asyncio
async def utest_key_manager_get_next_available_key_all_keys_fail_conditions():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_requests_per_minute=1)
    now = time.time()
    
    # Setup - make all keys fail the if condition in different ways
    # Key 1: status is RATE_LIMITED
    sut.keys[0]['status'] = KeyStatus.RATE_LIMITED
    sut.keys[0]['next_retry_time'] = now + 100  # Future time
    
    # Key 2: status is ACTIVE but timestamps exceed rate limit
    sut.keys[1]['status'] = KeyStatus.ACTIVE
    sut.keys[1]['next_retry_time'] = 0
    sut.keys[1]['timestamps'] = [now - 30]  # Recent timestamp, rate limit = 1
    
    # Call SUT (act)
    result = await sut.get_next_available_key()
    # Check result, assertion
    CHECK_BOOL(result is None, True, "Should return None when all keys fail conditions")

'''
Equivalent class of report_key_error(key, error_code)

Test case    *  key    *  error_code  * Expected Result 
             *         *              *                 
TC001        *  "key1" *  429         *  Success - Mark key as rate limited with retry count
TC002        *  "key1" *  500         *  Success - Mark key as rate limited for server error
TC003        *  "key1" *  200         *  Success - Mark key as active for success code
TC004        *  "key1" *  404         *  Success - Mark key as active for client error
TC005        *  "key2" *  429         *  Success - No effect when key not found
TC006        *  "key1" *  429         *  Success - Mark key as error after max retries
TC007        *  "key1" *  500         *  Success - Mark key as error after max retries (server error)
'''

# Test Description: Report rate limit error (429)
# Test Objective: Success
# Test Case: TC001
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_rate_limit_429():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=3)
    key = "key1"
    error_code = 429
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    key_info = next(k for k in sut.keys if k['key'] == key)
    CHECK_STR(key_info['status'], KeyStatus.RATE_LIMITED, "Status should be RATE_LIMITED")
    CHECK_INT(key_info['retry_count'], 1, "Retry count should be 1")
    CHECK_BOOL(key_info['next_retry_time'] > time.time(), True, "Next retry time should be in future")

# Test Description: Report server error (500)
# Test Objective: Success
# Test Case: TC002
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_server_error_500():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=3)
    key = "key1"
    error_code = 500
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    key_info = next(k for k in sut.keys if k['key'] == key)
    CHECK_STR(key_info['status'], KeyStatus.RATE_LIMITED, "Status should be RATE_LIMITED")
    CHECK_INT(key_info['retry_count'], 1, "Retry count should be 1")
    CHECK_BOOL(key_info['next_retry_time'] > time.time(), True, "Next retry time should be in future")

# Test Description: Report success code (200)
# Test Objective: Success
# Test Case: TC003
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_success_200():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=3)
    key = "key1"
    error_code = 200
    # Setup - mark key as rate limited first
    key_info = next(k for k in sut.keys if k['key'] == key)
    key_info['status'] = KeyStatus.RATE_LIMITED
    key_info['retry_count'] = 2
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    CHECK_STR(key_info['status'], KeyStatus.ACTIVE, "Status should be ACTIVE")
    CHECK_INT(key_info['retry_count'], 0, "Retry count should be reset to 0")
    CHECK_INT(key_info['next_retry_time'], 0, "Next retry time should be reset to 0")

# Test Description: Report client error (404)
# Test Objective: Success
# Test Case: TC004
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_client_error_404():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=3)
    key = "key1"
    error_code = 404
    # Setup - mark key as rate limited first
    key_info = next(k for k in sut.keys if k['key'] == key)
    key_info['status'] = KeyStatus.RATE_LIMITED
    key_info['retry_count'] = 1
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    CHECK_STR(key_info['status'], KeyStatus.ACTIVE, "Status should be ACTIVE")
    CHECK_INT(key_info['retry_count'], 0, "Retry count should be reset to 0")
    CHECK_INT(key_info['next_retry_time'], 0, "Next retry time should be reset to 0")

# Test Description: Report error for non-existent key
# Test Objective: Success
# Test Case: TC005
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_key_not_found():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=3)
    key = "key3"  # Non-existent key
    error_code = 429
    # Call SUT (act) - should not raise exception
    await sut.report_key_error(key, error_code)
    # Check result, assertion - no keys should be modified
    for key_info in sut.keys:
        CHECK_STR(key_info['status'], KeyStatus.ACTIVE, "Key status should remain ACTIVE")
        CHECK_INT(key_info['retry_count'], 0, "Retry count should remain 0")

# Test Description: Report error after max retries exceeded
# Test Objective: Success
# Test Case: TC006
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_max_retries_exceeded_429():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=2)
    key = "key1"
    error_code = 429
    # Setup - mark key as having max retries
    key_info = next(k for k in sut.keys if k['key'] == key)
    key_info['retry_count'] = 2
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    CHECK_STR(key_info['status'], KeyStatus.ERROR, "Status should be ERROR")
    CHECK_INT(key_info['retry_count'], 3, "Retry count should be 3")

# Test Description: Report server error after max retries exceeded
# Test Objective: Success - Cover line 63 (server error -> ERROR status)
# Test Case: TC007
@pytest.mark.asyncio
async def utest_key_manager_report_key_error_server_error_max_retries_500():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys, max_retries=2)
    key = "key1"
    error_code = 500
    # Setup - mark key as having max retries
    key_info = next(k for k in sut.keys if k['key'] == key)
    key_info['retry_count'] = 2
    # Call SUT (act)
    await sut.report_key_error(key, error_code)
    # Check result, assertion
    CHECK_STR(key_info['status'], KeyStatus.ERROR, "Status should be ERROR")
    CHECK_INT(key_info['retry_count'], 3, "Retry count should be 3")

'''
Equivalent class of _rotate_index()

Test case    *  Description                    * Expected Result 
             *                                *                 
TC001        *  Rotate with multiple keys     *  Success - Index rotates correctly
TC002        *  Rotate with single key        *  Success - Index stays at 0
TC003        *  Rotate multiple times         *  Success - Index cycles correctly
'''

# Test Description: Rotate index with multiple keys
# Test Objective: Success
# Test Case: TC001
def utest_key_manager_rotate_index_multiple_keys():
    # Test data
    api_keys = ["key1", "key2", "key3"]
    sut = APIKeyManager(api_keys)
    # Call SUT (act)
    sut._rotate_index()
    # Check result, assertion
    CHECK_INT(sut.current_index, 1, "Index should be 1 after first rotation")
    sut._rotate_index()
    CHECK_INT(sut.current_index, 2, "Index should be 2 after second rotation")
    sut._rotate_index()
    CHECK_INT(sut.current_index, 0, "Index should wrap around to 0")

# Test Description: Rotate index with single key
# Test Objective: Success
# Test Case: TC002
def utest_key_manager_rotate_index_single_key():
    # Test data
    api_keys = ["key1"]
    sut = APIKeyManager(api_keys)
    # Call SUT (act)
    sut._rotate_index()
    # Check result, assertion
    CHECK_INT(sut.current_index, 0, "Index should stay at 0 for single key")

# Test Description: Rotate index multiple times
# Test Objective: Success
# Test Case: TC003
def utest_key_manager_rotate_index_multiple_rotations():
    # Test data
    api_keys = ["key1", "key2"]
    sut = APIKeyManager(api_keys)
    # Call SUT (act) - rotate 5 times
    for _ in range(5):
        sut._rotate_index()
    # Check result, assertion
    CHECK_INT(sut.current_index, 1, "Index should be 1 after 5 rotations (5 % 2 = 1)")

##################################### END TEST #######################################################

######################################################################################################
# STUB/MOCK control
######################################################################################################

def expected_call_time_time(instance: str, method_name: str, expected):
    """Mock for time.time() function"""
    mock = MagicMock()
    if instance == "success":
        mock.return_value = expected
    elif instance == "default":
        mock.return_value = expected
    elif instance == "failed":
        mock.return_value = expected
    else:
        raise ValueError(f"⚠️ Call instance not defined")
    return mock
