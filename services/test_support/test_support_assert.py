# test_support.py

def CHECK_U_INT(actual, expected, msg=""):
    """
    Check unsigned int equality.
    Raises AssertionError if not equal.
    """
    if not isinstance(actual, int) or not isinstance(expected, int):
        raise AssertionError(f"CHECK_U_INT failed: values must be integers. Got {type(actual)} vs {type(expected)}")

    if actual < 0 or expected < 0:
        raise AssertionError(f"CHECK_U_INT failed: values must be unsigned (>=0). Got {actual} vs {expected}")

    if actual != expected:
        raise AssertionError(f"CHECK_U_INT failed: {actual} != {expected}. {msg}")

def CHECK_INT(actual, expected, msg=""):
    """
    Check int equality.
    """
    if not isinstance(actual, int) or not isinstance(expected, int):
        raise AssertionError(f"CHECK_INT failed: values must be integers. Got {type(actual)} vs {type(expected)}")

    if actual != expected:
        raise AssertionError(f"CHECK_INT failed: {actual} != {expected}. {msg}")

def CHECK_STR(actual, expected, msg=""):
    """
    Check string equality.
    """
    if not isinstance(actual, str) or not isinstance(expected, str):
        raise AssertionError(f"CHECK_STR failed: values must be strings. Got {type(actual)} vs {type(expected)}")

    if expected not in actual:
        raise AssertionError(f"CHECK_STR failed: '{actual}' does not contain '{expected}'. {msg}")

def CHECK_BOOL(actual, expected=True, msg=""):
    """
    Check boolean.
    """
    if not isinstance(actual, bool):
        raise AssertionError(f"CHECK_BOOL failed: value must be bool. Got {type(actual)}")

    if actual != expected:
        raise AssertionError(f"CHECK_BOOL failed: {actual} != {expected}. {msg}")

def CHECK_EQUAL(actual, expected, msg=""):
    """
    Check equality of any two objects.

    Args:
        actual: The actual value.
        expected: The expected value.
        msg: Additional message to include in the assertion error.

    Raises:
        AssertionError: If the values are not equal.
    """
    if actual != expected:
        raise AssertionError(f"CHECK_EQUAL failed: {actual} != {expected}. {msg}")

