"""test_frames — PlumbDataFrame + combinators. Requires the [pandas] extra."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # primitives/python

import pandas as pd
import pytest
import frames  # primitives/python/frames.py


def _df(**cols):
    return pd.DataFrame(cols)


def test_construct_sets_meta_and_value():
    df = _df(a=[1, 2])
    pdf = frames.PlumbDataFrame(df, source="real", confidence="high")
    assert pdf.meta["source"] == "real"
    assert pdf.meta["confidence"] == "high"
    assert pdf.value is df
    assert pdf.unwrap() is df
    assert pdf.meta_of() is pdf.meta


def test_construct_wrong_type_raises_typeerror():
    with pytest.raises(TypeError):
        frames.PlumbDataFrame({"a": [1]})  # a dict, not a DataFrame


def test_clean_real_frame_audits_clean():
    pdf = frames.PlumbDataFrame(_df(a=[1]), source="real", confidence="high")
    assert pdf.audit() == []


def test_concat_propagates_mock_taint_and_weakest_confidence():
    real = frames.PlumbDataFrame(_df(a=[1]), source="real", confidence="high")
    mock = frames.PlumbDataFrame(_df(a=[2]), source="mock", confidence="low")
    out = frames.plumb_concat([real, mock])
    assert out.meta["derived_from_mock"] is True
    assert out.meta["confidence"] == "low"        # weakest of high/low
    assert out.meta["source"] == "derived"
    assert list(out.value["a"]) == [1, 2]         # the real pandas concat ran
    assert out.audit() == []


def test_merge_runs_join_and_combines_meta():
    left = frames.PlumbDataFrame(_df(id=[1, 2], x=[10, 20]), source="real", confidence="high")
    right = frames.PlumbDataFrame(_df(id=[1, 2], y=[30, 40]), source="mock", confidence="medium")
    out = frames.plumb_merge(left, right, on="id")
    assert out.meta["derived_from_mock"] is True
    assert out.meta["confidence"] == "medium"     # weakest of high/medium
    assert set(out.value.columns) == {"id", "x", "y"}


def test_derive_general_combinator():
    a = frames.PlumbDataFrame(_df(v=[1]), source="real", confidence="high")
    b = frames.PlumbDataFrame(_df(v=[2]), source="real", confidence="medium")
    out = frames.plumb_derive([a, b], lambda x, y: x.add(y))
    assert out.meta["source"] == "derived"
    assert out.meta["confidence"] == "medium"
    assert int(out.value["v"].iloc[0]) == 3


def test_taint_cannot_be_cleared_via_override():
    mock = frames.PlumbDataFrame(_df(a=[1]), source="mock", confidence="low")
    out = frames.plumb_derive([mock], lambda d: d, derived_from_mock=False)
    assert out.meta["derived_from_mock"] is True   # force-OR'd, cannot be cleared
