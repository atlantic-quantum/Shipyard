"""Tests for error handling/raising in the shipyard package"""

import pytest

import shipyard.compiler_error as error


def test_error():
    E = error.Error(error_code=error.ErrorCode.DUPLICATE_ID, message="test_msg")
    assert E.error_code == error.ErrorCode.DUPLICATE_ID
    assert E.message == "Error: (ErrorCode.DUPLICATE_ID) test_msg"

    with pytest.raises(error.Error):
        raise E
