import sys
from dataclasses import replace
from pathlib import Path

from . import images, llm
from .config import default_config_dir, load_config, resolve_api_key
from .history import History
from .render import render_answer, render_error, render_list


class UsageError(Exception):
    """Raised for malformed command-line input."""


HELP = """onesh - ask a quick question, get a one-shot answer at the terminal.

Usage:
  onesh [options] "your question"

Options:
  -c, --continue [N]   Continue a conversation. With no number, continues the
                       most recent one; with N, continues conversation #N from
                       the -l list.
  -l, --list           List recent conversations and exit.
  --image-clipboard    Attach the current clipboard image to this prompt.
  --model MODEL        Override the configured model for this call.
  -h, --help           Show this help and exit.

Examples:
  onesh "how do I list files by size"
  onesh --image-clipboard "what is in this screenshot"
  onesh -c "now sort them ascending"
  onesh -c 2 "follow up to conversation 2"
  onesh -l
"""


def parse_args(argv):
    continue_ = False
    index = None
    list_ = False
    model = None
    image_clipboard = False
    help_ = False
    rest = []

    i = 0
    while i < len(argv):
        token = argv[i]
        if token in ("-h", "--help"):
            help_ = True
            i += 1
        elif token in ("-l", "--list"):
            list_ = True
            i += 1
        elif token == "--image-clipboard":
            image_clipboard = True
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
        "image_clipboard": image_clipboard,
        "help": help_,
    }


def _history_path(config_dir):
    base = Path(config_dir) if config_dir else default_config_dir()
    return base / "history.json"


def _prune_unreferenced_images(history, cache_dir):
    images.prune_unreferenced_images(
        cache_dir,
        images.referenced_image_paths(history.state),
    )


def _messages_have_image_refs(messages):
    return any(
        any(images.image_refs_from_content(message.get("content")))
        for message in messages
    )


def _request_config(config, args, messages):
    if args["model"] is None and _messages_have_image_refs(messages):
        return replace(config, model=config.image_model)
    return config


def main(argv=None, *, config_dir=None, env=None):
    if argv is None:
        argv = sys.argv[1:]

    try:
        args = parse_args(argv)
    except UsageError as exc:
        render_error(str(exc))
        return 2

    if args["help"]:
        print(HELP)
        return 0

    if not args["list"] and not args["prompt"]:
        render_error('no prompt given. usage: onesh "your question"')
        return 2

    try:
        config = load_config({"model": args["model"]}, config_dir=config_dir)
    except (ValueError, OSError) as exc:
        render_error(f"could not read config: {exc}")
        return 1

    history_path = _history_path(config_dir)
    image_cache = images.image_cache_dir(config_dir)

    if args["list"]:
        try:
            history = History(history_path)
        except (ValueError, OSError) as exc:
            render_error(f"could not read history ({history_path}): {exc}")
            return 1
        _prune_unreferenced_images(history, image_cache)
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
        model = (
            config.image_model
            if args["image_clipboard"] and args["model"] is None
            else config.model
        )
        conversation = history.new_conversation(model)
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

    image_refs = []
    if args["image_clipboard"]:
        try:
            image_refs.append(images.capture_clipboard_image(image_cache))
        except images.ImageError as exc:
            render_error(str(exc))
            return 1

    user_content = images.build_user_content(args["prompt"], image_refs)
    messages = conversation["messages"] + [{"role": "user", "content": user_content}]
    request_config = _request_config(config, args, messages)
    client = llm.build_client(request_config, api_key)
    try:
        text = llm.complete(client, request_config, messages)
    except llm.LLMError as exc:
        _prune_unreferenced_images(history, image_cache)
        render_error(str(exc))
        return 1

    history.append_turn(conversation, user_content, text)
    history.save()
    _prune_unreferenced_images(history, image_cache)
    render_answer(text)
    return 0


def run():
    raise SystemExit(main())
