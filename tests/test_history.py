import json

import pytest

from onesh.history import History


def counter_clock(start=0):
    n = {"v": start}

    def _():
        n["v"] += 1
        return f"2026-01-01T00:00:{n['v']:02d}+00:00"

    return _


def test_new_conversation_sets_fields(tmp_path):
    h = History(
        tmp_path / "h.json",
        clock=lambda: "2026-01-01T00:00:00+00:00",
        uuid_factory=lambda: "uuid-1",
    )
    c = h.new_conversation("m1")
    assert c["id"] == "uuid-1"
    assert c["created_at"] == "2026-01-01T00:00:00+00:00"
    assert c["updated_at"] == "2026-01-01T00:00:00+00:00"
    assert c["model"] == "m1"
    assert c["messages"] == []
    assert h.most_recent() is c


def test_most_recent_none_when_empty(tmp_path):
    h = History(tmp_path / "h.json")
    assert h.most_recent() is None


def test_continue_bumps_to_top(tmp_path):
    ids = iter(["a", "b"])
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: next(ids))
    c1 = h.new_conversation("m")  # updated :01
    c2 = h.new_conversation("m")  # updated :02
    assert h.most_recent() is c2
    h.append_turn(c1, "hi", "yo")  # updated :03 -> c1 now top
    assert h.most_recent() is c1
    assert h.select(1) is c1
    assert h.select(2) is c2


def test_select_out_of_range(tmp_path):
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: "x")
    h.new_conversation("m")
    with pytest.raises(IndexError):
        h.select(2)
    with pytest.raises(IndexError):
        h.select(0)


def test_append_turn_adds_both_messages(tmp_path):
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: "x")
    c = h.new_conversation("m")
    h.append_turn(c, "q", "a")
    assert c["messages"] == [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "a"},
    ]


def test_list_recent_titles_and_limit(tmp_path):
    ids = iter(["a", "b"])
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: next(ids))
    c1 = h.new_conversation("m")
    h.append_turn(c1, "first q", "a1")
    c2 = h.new_conversation("m")
    h.append_turn(c2, "second q", "a2")
    assert h.list_recent(limit=1) == [(1, "second q")]
    assert h.list_recent(limit=10) == [(1, "second q"), (2, "first q")]


def test_list_recent_handles_empty_messages(tmp_path):
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: "x")
    h.new_conversation("m")
    assert h.list_recent(10) == [(1, "(no messages)")]


def test_list_recent_uses_text_part_for_image_messages(tmp_path):
    h = History(tmp_path / "h.json", clock=counter_clock(), uuid_factory=lambda: "x")
    c = h.new_conversation("m")
    h.append_turn(
        c,
        [
            {"type": "text", "text": "describe this"},
            {
                "type": "image_ref",
                "image_ref": {"path": "clip.png", "mime_type": "image/png"},
            },
        ],
        "a",
    )
    assert h.list_recent(10) == [(1, "describe this")]


def test_save_and_reload(tmp_path):
    p = tmp_path / "h.json"
    h = History(p, clock=counter_clock(), uuid_factory=lambda: "x")
    c = h.new_conversation("m")
    h.append_turn(c, "q", "a")
    h.save()
    h2 = History(p)
    mr = h2.most_recent()
    assert mr["id"] == "x"
    assert mr["messages"][0]["content"] == "q"
    assert json.loads(p.read_text(encoding="utf-8"))["conversations"][0]["id"] == "x"
