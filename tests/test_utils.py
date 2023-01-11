import pytest
from samesyslib.utils import hms_format, load_config


def test_missing_config():
    with pytest.raises(Exception):
        load_config("file-does-not-exist.yaml")


def test_invalid_config(tmpdir):
    yaml_contents = "%%%/n"
    tmp_config = tmpdir.join("temp-config.yaml")
    tmp_config.write_text(yaml_contents, encoding="utf-8")

    with pytest.raises(Exception):
        load_config(tmp_config.strpath)


def test_valid_config(tmpdir):
    yaml_contents = "hello: True\n" "number: 44\n"
    tmp_config = tmpdir.join("temp-config.yaml")
    tmp_config.write_text(yaml_contents, encoding="utf-8")

    parsed_config = load_config(tmp_config.strpath)

    assert parsed_config["hello"] is True
    assert parsed_config["number"] == 44


def test_valid_hms_format_call():
    assert hms_format(0) == "00:00:00.00"
    assert hms_format(10000) == "02:46:40.00"
    assert hms_format("100") == "00:01:40.00"


def test_invalid_hms_format_call():
    with pytest.raises(Exception):
        hms_format("text")
