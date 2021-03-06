import pytest
from samesyslib.utils import hms_format

def test_valid_hms_format_call():
    assert hms_format(0) == '00:00:00.00'
    assert hms_format(10000) == '02:46:40.00'
    assert hms_format('100') == '00:01:40.00'


def test_invalid_hms_format_call():
    with pytest.raises(Exception):
        hms_format('text')