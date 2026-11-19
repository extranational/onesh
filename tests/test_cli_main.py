import json

import onesh.cli as cli


IMAGE_MODEL = "deepseek/deepseek-v4-flash-vision-exp"


def _image_ref(path):
    return {
        "type": "image_ref",
        "image_ref": {
            "path": str(path),
            "mime_type": "image/png",
            "source": "clipboard",
        },
    }


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


def test_main_with_clipboard_image_stores_ref_and_uses_image_model(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")

    captured = {}

    def fake_complete(client, config, messages):
        captured["model"] = config.model
        captured["messages"] = messages
        return "the answer"

    monkeypatch.setattr(cli.llm, "complete", fake_complete)
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)

    ref = _image_ref(tmp_path / "tmp-images" / "clip.png")
    monkeypatch.setattr(cli.images, "capture_clipboard_image", lambda cache_dir: ref)

    rc = cli.main(
        ["--image-clipboard", "what is this"],
        config_dir=tmp_path,
        env={"OPENROUTER_API_KEY": "sk"},
    )

    assert rc == 0
    assert captured["model"] == IMAGE_MODEL
    assert captured["messages"][-1] == {
        "role": "user",
        "content": [{"type": "text", "text": "what is this"}, ref],
    }

    saved = json.loads((tmp_path / "history.json").read_text())
    conv = saved["conversations"][0]
    assert conv["model"] == IMAGE_MODEL
    assert conv["messages"][0]["content"] == [
        {"type": "text", "text": "what is this"},
        ref,
    ]


def test_model_override_wins_for_clipboard_image(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")
    models = []
    monkeypatch.setattr(
        cli.llm,
        "complete",
        lambda client, config, messages: models.append(config.model) or "a",
    )
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)
    monkeypatch.setattr(
        cli.images,
        "capture_clipboard_image",
        lambda cache_dir: _image_ref(tmp_path / "tmp-images" / "clip.png"),
    )

    rc = cli.main(
        ["--image-clipboard", "--model", "custom/vision", "what is this"],
        config_dir=tmp_path,
        env={"OPENROUTER_API_KEY": "sk"},
    )

    assert rc == 0
    assert models == ["custom/vision"]


def test_continue_with_prior_image_uses_image_model(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.llm, "build_client", lambda config, api_key: "CLIENT")
    models = []
    monkeypatch.setattr(
        cli.llm,
        "complete",
        lambda client, config, messages: models.append(config.model) or "a",
    )
    monkeypatch.setattr(cli, "render_answer", lambda text, **k: None)
    monkeypatch.setattr(
        cli.images,
        "capture_clipboard_image",
        lambda cache_dir: _image_ref(tmp_path / "tmp-images" / "clip.png"),
    )

    cli.main(
        ["--image-clipboard", "first"],
        config_dir=tmp_path,
        env={"OPENROUTER_API_KEY": "sk"},
    )
    rc = cli.main(
        ["-c", "follow up"],
        config_dir=tmp_path,
        env={"OPENROUTER_API_KEY": "sk"},
    )

    assert rc == 0
    assert models == [IMAGE_MODEL, IMAGE_MODEL]


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


def test_main_help_prints_usage(tmp_path, capsys):
    rc = cli.main(["--help"], config_dir=tmp_path, env={})
    assert rc == 0
    out = capsys.readouterr().out
    assert "onesh" in out
    assert "-c" in out
    assert "-l" in out
    assert "--model" in out
    assert "-h" in out
