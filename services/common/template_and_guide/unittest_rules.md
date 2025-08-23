# Unit Test Writing Guide

## Core Principles
1. Test one thing at a time
2. All dependencies should be stubbed
3. No patching - inject dependencies instead
4. Follow the "Arrange-Act-Assert" pattern
5. Keep tests simple and readable
6. Cover all public functions/methods including:
   - Normal success cases  
   - Failure/exception cases  
   - Edge cases (boundary values, empty inputs, `None`, negative numbers, max/min values, etc.)
7. For each method an equivalent class MUST be created to derive a test case


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
