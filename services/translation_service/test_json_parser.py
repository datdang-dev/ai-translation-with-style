"""
Test file for JSONParser class
"""

import json
from services.translation_service.json_parser import JSONParser


def test_json_parser():
    """Test the JSONParser with various inputs"""
    parser = JSONParser()
    
    # Test 1: Valid JSON
    valid_json = '{"key1": "value1", "key2": "value2"}'
    result = parser.parse_response(valid_json)
    print("Test 1 - Valid JSON:", result)
    assert isinstance(result, dict) and "key1" in result
    
    # Test 2: JSON with backticks
    json_with_backticks = '```json\n{"key1": "value1", "key2": "value2"}\n```'
    result = parser.parse_response(json_with_backticks)
    print("Test 2 - JSON with backticks:", result)
    assert isinstance(result, dict) and "key1" in result
    
    # Test 3: JSON with backticks but no json specifier
    json_with_backticks_no_json = '```\n{"key1": "value1", "key2": "value2"}\n```'
    result = parser.parse_response(json_with_backticks_no_json)
    print("Test 3 - JSON with backticks but no json specifier:", result)
    assert isinstance(result, dict) and "key1" in result
    
    # Test 4: Invalid JSON that can be recovered with method 1 (regex extraction)
    invalid_json_recoverable = 'Some text before\n{"key1": "value1", "key2": "value2"}\nSome text after'
    result = parser.parse_response(invalid_json_recoverable)
    print("Test 4 - Invalid JSON recoverable with method 1:", result)
    assert isinstance(result, dict) and "key1" in result
    
    # Test 5: Invalid JSON that can be recovered with method 3 (key-value pairs)
    invalid_json_kv = 'Some text before\n"key1": "value1", "key2": "value2"\nSome text after'
    result = parser.parse_response(invalid_json_kv)
    print("Test 5 - Invalid JSON recoverable with method 3:", result)
    assert isinstance(result, dict) and "key1" in result
    
    print("All tests passed!")


if __name__ == "__main__":
    test_json_parser()