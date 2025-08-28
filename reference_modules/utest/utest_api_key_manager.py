# Test Module: api_key_manager
# Purpose: Unit tests for ApiKeyManager interface
# Author: datdang
# Created: 2025-08-20
# Framework: pytest

import pytest
from unittest.mock import MagicMock, patch
from common_modules.api_key_manager import ApiKeyManager

##################################### Global datas ####################################################
TEST_API_KEYS = ["key1", "key2", "key3"]
TEST_CONFIG_FILE = "test_config.json"

##################################### Test `__init__` ##################################

'''
Equivalent class of __init__(api_keys: list)

Test case    *  api_keys         *  Expected Result 
             *                   *                 
TC001        *  Valid list      *  Success - Manager initialized with keys
TC002        *  Empty list      *  Failure - Raises ValueError
TC003        *  None            *  Failure - Raises TypeError
'''

# Test Description: Verify ApiKeyManager initializes with valid keys
# Test type: Success
# Test Case: TC001
def utest_api_key_manager_init_success():
    # Test data
    api_keys = TEST_API_KEYS
    
    # Call SUT
    manager = ApiKeyManager(api_keys)
    
    # Check result
    assert manager.get_current_key() == api_keys[0]
    assert manager.get_total_keys() == len(api_keys)

# Test Description: Verify ApiKeyManager fails with empty keys
# Test type: Failure
# Test Case: TC002
def utest_api_key_manager_init_empty():
    # Test data
    api_keys = []
    
    # Call SUT and check result
    with pytest.raises(ValueError, match="API keys list cannot be empty"):
        ApiKeyManager(api_keys)

# Test Description: Verify ApiKeyManager fails with None keys
# Test type: Failure
# Test Case: TC003
def utest_api_key_manager_init_none():
    # Test data
    api_keys = None
    
    # Call SUT and check result
    with pytest.raises(TypeError, match="API keys must be a list"):
        ApiKeyManager(api_keys)

##################################### Test `get_current_key` ##################################

'''
Equivalent class of get_current_key()

Test case    *  Manager State    *  Expected Result 
             *                   *                 
TC004        *  Has keys        *  Success - Returns current key
TC005        *  All exhausted   *  Success - Returns last key
'''

# Test Description: Verify get_current_key returns current key
# Test type: Success
# Test Case: TC004
def utest_api_key_manager_get_current_key_success():
    # Test data
    api_keys = TEST_API_KEYS
    manager = ApiKeyManager(api_keys)
    
    # Call SUT
    key = manager.get_current_key()
    
    # Check result
    assert key == api_keys[0]

##################################### Test `switch_to_next_key` ##################################

'''
Equivalent class of switch_to_next_key()

Test case    *  Current Index    *  Total Keys     *  Expected Result 
             *                   *                 *                 
TC006        *  < Total-1       *  Multiple       *  Success - Switches to next key
TC007        *  Total-1         *  Multiple       *  Failure - No more keys
'''

# Test Description: Verify switch_to_next_key changes to next key
# Test type: Success
# Test Case: TC006
def utest_api_key_manager_switch_key_success():
    # Test data
    api_keys = TEST_API_KEYS
    manager = ApiKeyManager(api_keys)
    
    # Call SUT
    manager.switch_to_next_key()
    
    # Check result
    assert manager.get_current_key() == api_keys[1]

# Test Description: Verify switch_to_next_key fails when no more keys
# Test type: Failure
# Test Case: TC007
def utest_api_key_manager_switch_key_exhausted():
    # Test data
    api_keys = TEST_API_KEYS
    manager = ApiKeyManager(api_keys)
    
    # Exhaust all keys
    for _ in range(len(api_keys) - 1):
        manager.switch_to_next_key()
    
    # Call SUT and check result
    with pytest.raises(RuntimeError, match="All API keys exhausted"):
        manager.switch_to_next_key()

##################################### Test `get_total_keys` ##################################

'''
Equivalent class of get_total_keys()

Test case    *  API Keys         *  Expected Result 
             *                   *                 
TC008        *  Multiple keys    *  Success - Returns correct count
TC009        *  Single key      *  Success - Returns 1
'''

# Test Description: Verify get_total_keys returns correct count
# Test type: Success
# Test Case: TC008
def utest_api_key_manager_get_total_keys_multiple():
    # Test data
    api_keys = TEST_API_KEYS
    manager = ApiKeyManager(api_keys)
    
    # Call SUT
    total = manager.get_total_keys()
    
    # Check result
    assert total == len(api_keys)

# Test Description: Verify get_total_keys works with single key
# Test type: Success
# Test Case: TC009
def utest_api_key_manager_get_total_keys_single():
    # Test data
    api_keys = [TEST_API_KEYS[0]]
    manager = ApiKeyManager(api_keys)
    
    # Call SUT
    total = manager.get_total_keys()
    
    # Check result
    assert total == 1

##################################### END TEST #######################################################
