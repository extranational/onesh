import json

import onesh.cli as cli


def test_main_runs_a_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")

    captured = {}

    def fake_complete(client, config, messages):
        captured["client"] = client
        captured["messages"] = messages
        return "the answer"

    monkeypatch.setattr(cli.llm, "complete", fake_complete)

    printed = {}
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: printed.update(text=text))

    rc = cli.main(["how do I X"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})

    assert rc == 0
    assert printed["text"] == "the answer"
    assert captured["client"] == "CLIENT"
    assert captured["messages"][-1] == {"role": "user", "content": "how do I X"}

    saved = json.loads((tmp_path / "history.json").read_text())
    conv = saved["conversations"][0]
    assert conv["messages"] == [
        {"role": "user", "content": "how do I X"},
        {"role": "assistant", "content": "the answer"},
    ]


def test_main_continue_appends_to_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")
    monkeypatch.setattr(cli.llm, "complete", lambda client, config, messages: "a2")
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)

    cli.main(["first"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    cli.main(["-c", "second"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})

    saved = json.loads((tmp_path / "history.json").read_text())
    assert len(saved["conversations"]) == 1
    contents = [m["content"] for m in saved["conversations"][0]["messages"]]
    assert contents == ["first", "a2", "second", "a2"]


def test_main_missing_key_errors(tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(cli, "render_error", lambda message, **k: errors.append(message))
    rc = cli.main(["q"], config_dir=tmp_path, env={})
    assert rc == 1
    assert errors and "OPENROUTER_API_KEY" in errors[0]


def test_main_missing_prompt_usage(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "render_error", lambda message, **k: None)
    rc = cli.main([], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    assert rc == 2


def test_main_continue_nothing_to_continue(tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(cli, "render_error", lambda message, **k: errors.append(message))
    rc = cli.main(["-c", "x"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    assert rc == 1
    assert errors


def test_main_select_out_of_range(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")
    monkeypatch.setattr(cli.llm, "complete", lambda client, config, messages: "a")
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)
    errors = []
    monkeypatch.setattr(cli, "render_error", lambda message, **k: errors.append(message))

    cli.main(["first"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    rc = cli.main(["-c", "5", "x"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    assert rc == 1
    assert errors


def test_main_list(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")
    monkeypatch.setattr(cli.llm, "complete", lambda client, config, messages: "a")
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)

    listed = {}
    monkeypatch.setattr(cli, "render_list", lambda items, **k: listed.update(items=items))

    cli.main(["my question"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    rc = cli.main(["-l"], config_dir=tmp_path, env={"OPENROUTER_API_KEY": "sk"})
    assert rc == 0
    assert listed["items"] == [(1, "my question")]
