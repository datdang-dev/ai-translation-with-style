# Unit Test Writing Guide

## Core Principles
1. Test one thing at a time
2. All dependencies should be stubbed
3. No patching - inject dependencies instead
4. Follow the "Arrange-Act-Assert" pattern
5. Keep tests simple and readable

## File Structure
```python
# Test Module: <module_name>
# Purpose: Unit tests for <module_name>
# Author: datdang
# Created: <YYYY-MM-DD>
# Framework: pytest

import pytest
from unittest.mock import MagicMock
# Import modules under test
```

## Global Data Section
```python
##################################### Global datas ####################################################
TEST_DEFAULT_VALUE = 0xAA  # Default test values
TEST_DATA = {
    # Test data constants
}
```

## Test Case Documentation
```python
'''
Equivalent class of <interface_name>(interface_params)

Test case    *  <param1>    *  <param2>    *  Expected Result 
             *              *              *                 
TC001        *  valid      *  valid       *  Success - <description>
TC002        *  invalid    *  valid       *  Failure - <description>
TC003        *  valid      *  invalid     *  Failure - <description>
...          *  ...        *  ...         *  ...
'''
```

## Dependency Injection (Instead of Patching)
1. Design classes to accept dependencies:
```python
class MyClass:
    def __init__(self, logger, api_client, db=None):
        self.logger = logger
        self.api_client = api_client
        self.db = db or DatabaseClient()
```

2. Use stub control functions to create complete stubs:
```python
def expected_call_requests(instance: str, method_name: str, expected):
    """Complete stub for requests module"""
    mock = MagicMock(name="requests")  # Stub entire module
    
    if instance == "success":
        # Configure all methods
        mock_response = MagicMock(status_code=200, text="success")
        mock.get.return_value = mock_response
        mock.post.return_value = mock_response
        mock.put.return_value = mock_response
    elif instance == "failed":
        mock.post.side_effect = Exception("Failed")
        mock.get.side_effect = Exception("Failed")
    
    return mock  # Return complete module stub

# Usage in test:
requests_mock = expected_call_requests("success", "post", None)
api_client = ApiClient(logger=logger_mock, requests_lib=requests_mock)
```

## STUB/MOCK Control Pattern
```python
######################################################################################################
# STUB/MOCK control
######################################################################################################

def expected_call_<class_name>(instance: str, method_name: str, expected):
    """
    Create a complete stub for <class_name> with all methods configured
    
    Args:
        instance: One of ["success", "default", "failed"]
        method_name: Primary method being configured
        expected: Expected return value or behavior
    
    Returns:
        MagicMock object fully configured as a complete stub
    """
    mock = MagicMock(name="<class_name>")  # Name helps with debugging

    if instance == "success":
        # Configure all methods for success
        mock.method1.return_value = expected
        mock.method2.return_value = "default"
        mock.property1 = "test"
    elif instance == "default":
        # Configure all methods with defaults
        mock.method1.return_value = expected or DEFAULT_VALUE
        mock.method2.return_value = None
        mock.property1 = None
    elif instance == "failed":
        # Configure all failure modes
        mock.method1.side_effect = Exception("Failed")
        mock.method2.side_effect = Exception("Failed")
        mock.property1 = None
    else:
        raise ValueError(f"⚠️ Call instance {instance} not defined")
    
    return mock  # Return complete stub
```

## Test Case Structure
```python
# Test Description: Clear description of what is being tested
# Test type: Success|Failure|Coverage
# Test Case: TC<number>
def utest_<module_name>_<interface_name>_<scenario>():
    # Test data
    data = {...}
    expected = {...}
    
    # Create complete stubs for all dependencies
    dependency1_mock = expected_call_dependency1("success", "method1", expected)
    dependency2_mock = expected_call_dependency2("default", "method2", None)
    
    # Call SUT with injected stubs
    sut = ClassUnderTest(
        dependency1=dependency1_mock,
        dependency2=dependency2_mock
    )
    result = sut.method_under_test(data)
    
    # Check result
    assert result == expected
    dependency1_mock.method1.assert_called_once_with(data)
```

## Example Test Implementation
```python
def utest_api_client_send_request_rate_limit():
    # Test data
    data = {"content": "test"}
    
    # Create complete stubs
    requests_mock = expected_call_requests("retry", "post", None)  # Complete module stub
    api_key_manager_mock = expected_call_api_key_manager("retry", "get_current_key", None)
    logger_mock = expected_call_logger("success", "info", None)
    
    # Call SUT with injected stubs
    api_client = ApiClient(
        api_key_manager=api_key_manager_mock,
        logger=logger_mock,
        requests_lib=requests_mock  # Inject, don't patch
    )
    response = api_client.send_request(data)
    
    # Check result
    assert response.status_code == 200
    api_key_manager_mock.switch_to_next_key.assert_called_once()
```

## Key Guidelines for Stubbing

1. Stub All Dependencies:
   - External services
   - File system operations
   - System calls
   - Time-dependent operations
   - Random number generators
   - Environment variables

2. Make Dependencies Injectable:
   - Design classes to accept dependencies
   - Use default arguments for compatibility
   - Pass dependencies through constructor

3. Create Complete Stubs:
   - Stub entire modules/classes
   - Configure all methods
   - Use sensible defaults
   - Handle all scenarios

4. Use Clear Naming:
   - Name stubs after what they replace
   - Use descriptive scenarios
   - Make failure modes explicit

5. Keep Tests Simple:
   - One assertion per behavior
   - Clear setup and verification
   - No complex mock logic

## Common Mistakes to Avoid

1. ❌ Don't use patch:
```python
# Bad - Using patch
@patch('requests.post')
def test_api_client(mock_post):
    client = ApiClient()
```

2. ❌ Don't stub partial behavior:
```python
# Bad - Incomplete stub
mock = MagicMock()
mock.some_method.return_value = "test"
```

3. ✅ Do inject complete stubs:
```python
# Good - Complete stub, injected
requests_mock = expected_call_requests("success", "post", None)
client = ApiClient(requests_lib=requests_mock)
```

Remember:
- Stub all dependencies
- Create complete stubs
- Inject dependencies
- Keep tests simple
- Follow template exactly
