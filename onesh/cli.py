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
