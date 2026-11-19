from openai import OpenAI

from . import images


class LLMError(Exception):
    """Raised when the LLM API call fails (network, auth, or API error)."""


def build_client(config, api_key):
    return OpenAI(base_url=config.base_url, api_key=api_key)


def complete(client, config, messages):
    try:
        full = images.messages_for_api(
            [{"role": "system", "content": config.system_prompt}, *messages]
        )
    except images.ImageError as exc:
        raise LLMError(str(exc)) from exc

    kwargs = {
        "model": config.model,
        "temperature": config.temperature,
        "messages": full,
    }
    headers = {}
    if config.http_referer:
        headers["HTTP-Referer"] = config.http_referer
    if config.x_title:
        headers["X-Title"] = config.x_title
    if headers:
        kwargs["extra_headers"] = headers

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 - normalize any client error
        raise LLMError(str(exc)) from exc

    return response.choices[0].message.content
