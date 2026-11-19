import pytest

from onesh.config import Config
from onesh.llm import LLMError, complete


def _cfg(**overrides):
    base = dict(
        base_url="u",
        api_key_env="K",
        model="m",
        image_model="im",
        system_prompt="SYS",
        temperature=0.2,
        list_limit=20,
    )
    base.update(overrides)
    return Config(**base)


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})})]


class FakeClient:
    def __init__(self, reply="hi there"):
        self.reply = reply
        self.calls = []
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.calls.append(kwargs)
                return _Resp(outer.reply)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def test_complete_prepends_system_and_returns_text():
    client = FakeClient("answer")
    out = complete(client, _cfg(), [{"role": "user", "content": "q"}])
    assert out == "answer"
    sent = client.calls[0]
    assert sent["model"] == "m"
    assert sent["temperature"] == 0.2
    assert sent["messages"][0] == {"role": "system", "content": "SYS"}
    assert sent["messages"][1] == {"role": "user", "content": "q"}
    assert "extra_headers" not in sent


def test_complete_includes_ranking_headers_when_set():
    client = FakeClient("ok")
    complete(client, _cfg(http_referer="https://x", x_title="onesh"), [])
    assert client.calls[0]["extra_headers"] == {
        "HTTP-Referer": "https://x",
        "X-Title": "onesh",
    }


def test_complete_expands_image_refs_to_data_urls(tmp_path):
    image = tmp_path / "clip.png"
    image.write_bytes(b"abc")
    client = FakeClient("ok")

    complete(
        client,
        _cfg(),
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe"},
                    {
                        "type": "image_ref",
                        "image_ref": {
                            "path": str(image),
                            "mime_type": "image/png",
                        },
                    },
                ],
            }
        ],
    )

    content = client.calls[0]["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "describe"}
    assert content[1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,YWJj"},
    }


def test_complete_wraps_errors():
    class Boom:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("network down")

    with pytest.raises(LLMError):
        complete(Boom(), _cfg(), [])
