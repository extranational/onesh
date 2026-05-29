import pytest

from onesh.cli import UsageError, parse_args


def test_plain_prompt():
    a = parse_args(["how to list files"])
    assert a["prompt"] == "how to list files"
    assert a["continue_"] is False
    assert a["index"] is None
    assert a["list"] is False
    assert a["model"] is None


def test_multiword_prompt_joined():
    a = parse_args(["hello", "world"])
    assert a["prompt"] == "hello world"


def test_continue_recent():
    a = parse_args(["-c", "follow up"])
    assert a["continue_"] is True
    assert a["index"] is None
    assert a["prompt"] == "follow up"


def test_continue_indexed():
    a = parse_args(["-c", "2", "follow up"])
    assert a["continue_"] is True
    assert a["index"] == 2
    assert a["prompt"] == "follow up"


def test_continue_bare_index_no_prompt():
    a = parse_args(["-c", "2"])
    assert a["index"] == 2
    assert a["prompt"] is None


def test_continue_word_is_prompt_not_index():
    a = parse_args(["-c", "hello"])
    assert a["index"] is None
    assert a["prompt"] == "hello"


def test_list_flag():
    a = parse_args(["-l"])
    assert a["list"] is True
    assert a["prompt"] is None


def test_model_override_space():
    a = parse_args(["--model", "x/y", "q"])
    assert a["model"] == "x/y"
    assert a["prompt"] == "q"


def test_model_override_equals():
    a = parse_args(["--model=x/y", "q"])
    assert a["model"] == "x/y"
    assert a["prompt"] == "q"


def test_model_requires_value():
    with pytest.raises(UsageError):
        parse_args(["--model"])


def test_help_short_flag():
    a = parse_args(["-h"])
    assert a["help"] is True


def test_help_long_flag():
    a = parse_args(["--help"])
    assert a["help"] is True


def test_help_defaults_false():
    a = parse_args(["q"])
    assert a["help"] is False
