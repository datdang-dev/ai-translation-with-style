# Test Module: <module_name>
# Purpose: Unit tests for <module_name>
# Author: datdang
# Created: <YYYY-MM-DD>
# Framework: pytest

import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
# from <module> import FileHandlerInterface, ProcessorInterface

##################################### Global datas ####################################################
PYTEST_DEFAULT_VALUE = 0xAA

##################################### Test `<interface_name>` ##################################

'''
Equivalent class of <interface_name>(interface_params)

Test case    *  <name_of_1st_param> * <name_of_2nd_param>  *  <name_of_Nth_param>       * Expected Result 
             *                      *                      *                            *                 
TC001        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC002        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC003        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC<number>   *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
'''

# Test Description: <Description about test case>
# Test Objective: <Success|Failure|Coverage|...>
# Test Case: TC<test_case_number>
def utest_<module_name>_<interface_name>_<scenario>():
    # Test data
    expected_value = <expected_value>
    sut = <interface_name>(...)
    # Test setup, stub, mock
    expected_call_<class_name>_<method_name>("<instance_name>", "<method_name>", expected_value)
    # Call SUT (act)
    act = sut.method_A(...)
    # Check result, assertion
    assert <expected_value> <result>
'''
Equivalent class of <other_interface_name>(other_interface_params)

Test case    *  <name_of_1st_param> * <name_of_2nd_param>  *  <name_of_Nth_param>       * Expected Result 
             *                      *                      *                            *                 
TC001        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC002        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC003        *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
TC<number>   *  <param_value>       *  <param_value>       *  <param_value>             *  <Success|Failure> - <short explanation>
'''

##################################### END TEST #######################################################

######################################################################################################
# STUB/MOCK control
######################################################################################################

def expected_call_<class_name>_<method_name>(instance: str, method_name: str, expected):

    mock = Mock()

    if instance == "success":
        getattr(mock, method_name).return_value = expected
    elif instance == "default":
        getattr(mock, method_name).return_value = expected
    elif instance == "failed":
        getattr(mock, method_name).return_value = expected
    else:
        raise ValueError(f"⚠️ Call instace not defined")
    return mock
