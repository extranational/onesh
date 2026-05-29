import json
import sys
from pathlib import Path

from . import llm
from .config import default_config_dir, load_config, resolve_api_key
from .history import History
from .render import render_answer, render_error, render_list


class UsageError(Exception):
    """Raised for malformed command-line input."""


def parse_args(argv):
    continue_ = False
    index = None
    list_ = False
    model = None
    rest = []

    i = 0
    while i < len(argv):
        token = argv[i]
        if token in ("-l", "--list"):
            list_ = True
            i += 1
        elif token in ("-c", "--continue"):
            continue_ = True
            i += 1
            if i < len(argv) and argv[i].isdigit():
                index = int(argv[i])
                i += 1
        elif token == "--model":
            i += 1
            if i >= len(argv):
                raise UsageError("--model requires a value")
            model = argv[i]
            i += 1
        elif token.startswith("--model="):
            model = token.split("=", 1)[1]
            i += 1
        else:
            rest.append(token)
            i += 1

    return {
        "prompt": " ".join(rest) if rest else None,
        "continue_": continue_,
        "index": index,
        "list": list_,
        "model": model,
    }


def _history_path(config_dir):
    base = Path(config_dir) if config_dir else default_config_dir()
    return base / "history.json"


def main(argv=None, *, config_dir=None, env=None):
    if argv is None:
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)
    except UsageError as exc:
        render_error(str(exc))
        return 2

    if not args["list"] and not args["prompt"]:
        render_error('no prompt given. usage: onesh "your question"')
        return 2

    try:
        config = load_config({"model": args["model"]}, config_dir=config_dir)
    except (ValueError, OSError) as exc:
        render_error(f"could not read config: {exc}")
        return 1

    history_path = _history_path(config_dir)

    if args["list"]:
        try:
            history = History(history_path)
        except (ValueError, OSError) as exc:
            render_error(f"could not read history ({history_path}): {exc}")
            return 1
        render_list(history.list_recent(config.list_limit))
        return 0

    api_key = resolve_api_key(config, env=env)
    if not api_key:
        render_error(
            f"{config.api_key_env} not set. Add it to .env or your environment, e.g.\n"
            f"  echo {config.api_key_env}=sk-... >> .env"
        )
        return 1

    try:
        history = History(history_path)
    except (ValueError, OSError) as exc:
        render_error(f"could not read history ({history_path}): {exc}")
        return 1

    if not args["continue_"]:
        conversation = history.new_conversation(config.model)
    elif args["index"] is not None:
        try:
            conversation = history.select(args["index"])
        except IndexError as exc:
            render_error(str(exc))
            return 1
    else:
        conversation = history.most_recent()
        if conversation is None:
            render_error("no conversations to continue.")
            return 1

    messages = conversation["messages"] + [{"role": "user", "content": args["prompt"]}]
    client = llm.build_client(config, api_key)
    try:
        text = llm.complete(client, config, messages)
    except llm.LLMError as exc:
        render_error(str(exc))
        return 1

    history.append_turn(conversation, args["prompt"], text)
    history.save()
    render_answer(text)
    return 0


def run():
    raise SystemExit(main())
