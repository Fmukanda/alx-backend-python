#!/usr/bin/env python3
"""
Unit tests for the utils.access_nested_map function.
"""
import unittest
from parameterized import parameterized
from utils import access_nested_map


class TestAccessNestedMap(unittest.TestCase):
    """
    Test class for the access_nested_map function.
    """
    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2),
    ])
    def test_access_nested_map(self, nested_map, path, expected_output):
        """
        Test that access_nested_map returns the expected value.
        """
        result = access_nested_map(nested_map, path)
        self.assertEqual(result, expected_output)

