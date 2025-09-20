#!/usr/bin/env python3
"""
Unit tests for the utils.access_nested_map function.
"""
import unittest
from parameterized import parameterized
from unittest.mock import patch, Mock
from typing import (
    Mapping,
    Sequence,
    Any,
    Dict,
    Type,
)
from utils import access_nested_map, get_json, memoize


class TestAccessNestedMap(unittest.TestCase):
    """
    Test suite for the access_nested_map function.
    """
    @parameterized.expand([
        ({"a": 1}, ("a",), 1),
        ({"a": {"b": 2}}, ("a",), {"b": 2}),
        ({"a": {"b": 2}}, ("a", "b"), 2),
    ])
    def test_access_nested_map(self, nested_map: Mapping, path: Sequence,
                               expected_output: Any) -> None:
        """
        Test that access_nested_map returns the expected value.
        """
        result = access_nested_map(nested_map, path)
        self.assertEqual(result, expected_output)

    @parameterized.expand([
        ({}, ("a",), KeyError),
        ({"a": 1}, ("a", "b"), KeyError),
    ])
    def test_access_nested_map_exception(self, nested_map: Mapping, path: Sequence,
                                         expected_exception: Type[KeyError]) -> None:
        """
        Test that access_nested_map raises the correct exception.
        """
        with self.assertRaises(expected_exception) as context:
            access_nested_map(nested_map, path)
        self.assertIsInstance(context.exception, KeyError)
        self.assertEqual(str(context.exception), f"'{path[-1]}'")


class TestGetJson(unittest.TestCase):
    """
    Test suite for the get_json function.
    """
    @parameterized.expand([
        ("http://example.com", {"payload": True}),
        ("http://holberton.io", {"payload": False}),
    ])
    def test_get_json(self, test_url: str, test_payload: Dict) -> None:
        """
        Test that get_json returns the expected payload.
        """
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock()
            mock_get.return_value.json.return_value = test_payload
            
            result = get_json(test_url)
            
            mock_get.assert_called_once_with(test_url)
            self.assertEqual(result, test_payload)


class TestMemoize(unittest.TestCase):
    """
    Test suite for the memoize decorator.
    """
    def test_memoize(self) -> None:
        """
        Test that a_property returns the correct result and a_method is called once.
        """
        class TestClass:
            def a_method(self) -> int:
                return 42
            @memoize
            def a_property(self) -> int:
                return self.a_method()
        with patch.object(TestClass, 'a_method') as mock_method:
            mock_method.return_value = 42
            test_instance = TestClass()
            
            result1 = test_instance.a_property
            result2 = test_instance.a_property
            
            self.assertEqual(result1, 42)
            self.assertEqual(result2, 42)
            mock_method.assert_called_once()
