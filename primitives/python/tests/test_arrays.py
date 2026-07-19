"""test_arrays — PlumbArray + combinators. Requires the [numpy] extra."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # primitives/python

import numpy as np
import pytest
import arrays  # primitives/python/arrays.py


def test_construct_sets_meta_and_value():
    a = np.array([1, 2, 3])
    pa = arrays.PlumbArray(a, source="real", confidence="high")
    assert pa.meta["source"] == "real"
    assert pa.value is a
    assert pa.audit() == []


def test_construct_wrong_type_raises_typeerror():
    with pytest.raises(TypeError):
        arrays.PlumbArray([1, 2, 3])  # a list, not an ndarray


def test_concatenate_propagates_taint():
    real = arrays.PlumbArray(np.array([1, 2]), source="real", confidence="high")
    mock = arrays.PlumbArray(np.array([3, 4]), source="mock", confidence="low")
    out = arrays.plumb_concatenate([real, mock])
    assert out.meta["derived_from_mock"] is True
    assert out.meta["confidence"] == "low"
    assert out.meta["source"] == "derived"
    assert list(out.value) == [1, 2, 3, 4]
    assert out.audit() == []


def test_stack_propagates_taint():
    real = arrays.PlumbArray(np.array([1, 2]), source="real", confidence="high")
    mock = arrays.PlumbArray(np.array([3, 4]), source="mock", confidence="medium")
    out = arrays.plumb_stack([real, mock])
    assert out.meta["derived_from_mock"] is True
    assert out.meta["confidence"] == "medium"
    assert out.value.shape == (2, 2)
    assert out.audit() == []                      # combinator output audits clean


def test_derive_general_and_taint_not_clearable():
    mock = arrays.PlumbArray(np.array([1, 2]), source="mock", confidence="low")
    out = arrays.plumb_derive([mock], lambda x: x * 2, derived_from_mock=False)
    assert out.meta["derived_from_mock"] is True
    assert list(out.value) == [2, 4]
    assert out.audit() == []                      # combinator output audits clean (dfm=True is honest, not laundering)
