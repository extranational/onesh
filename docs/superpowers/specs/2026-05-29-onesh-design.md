# onesh — design spec

**Date:** 2026-05-29
**Status:** Approved (pending written-spec review)

## Purpose

`onesh` ("one shot") is a command-line tool for asking a quick question and getting
a single answer at the terminal, instead of opening a browser and using a web AI mode.
Most uses are a single question with a single answer (e.g. "give me the command for X").
Occasionally a question extends to two or three follow-up turns, so the tool retains
conversation context on request.

The tool talks to OpenRouter via its OpenAI-compatible API. The provider base URL,
model, and answer style are configurable.

## Non-goals (YAGNI)

- No streaming output (answers are awaited, then rendered).
- No conversation browsing/search UI beyond `-l` listing and `-c N` selection.
- No multi-provider abstraction beyond "an OpenAI-compatible base URL + key".
- No GUI, no daemon, no shell-completion scripts.

## Invocation

A uv project. The console script `onesh` is the primary entry point:

```
onesh "your question"                  # one-shot, new conversation
onesh -c "follow up"                   # continue the most recent conversation
onesh -c 2 "follow up"                 # continue conversation #2 from the -l list
onesh -l                               # list recent conversations, then exit
onesh --model anthropic/claude-... "q" # override the configured model for this call
```

Run during development via `uv run onesh "..."` or `uv run python -m onesh "..."`.

## Project layout

```
onesh/                   # repo (directory name is incidental)
├─ pyproject.toml        # project metadata, deps, console-script entry "onesh"
├─ uv.lock               # generated
├─ onesh/                # package
│  ├─ __init__.py
│  ├─ __main__.py        # enables `python -m onesh`
│  ├─ cli.py             # arg parsing + orchestration (main)
│  ├─ config.py          # load user config + .env, merge CLI flags
│  ├─ history.py         # conversations JSON: load / list / select / append / save
│  ├─ llm.py             # OpenAI-compatible call to OpenRouter
│  └─ render.py          # markdown + list rendering via rich
├─ tests/                # pytest; LLM call mocked
├─ .env                  # OPENROUTER_API_KEY=...  (gitignored)
├─ .env.example
├─ .gitignore
└─ README.md
```

The package is named `onesh` (a valid Python identifier), so it doubles as the
importable module and the console-script target — no shim file is needed.

## Modules & responsibilities

Each module has one clear purpose and a small interface so it can be tested in isolation.

### `config.py`
- Locates and loads the user config file at `~/.config/onesh/config.json`
  (`Path.home() / ".config" / "onesh"`; on this machine `C:\Users\brett\.config\onesh\`).
- On first run, if the file is missing, writes it with the defaults below.
- Loads `.env` from the project root via `python-dotenv`, then reads the API key from
  the environment variable named by `api_key_env`. A real environment variable, if
  already set, takes precedence over `.env`.
- Merges CLI overrides (e.g. `--model`) on top of the file config and returns a single
  resolved config object.
- Default config:
  ```json
  {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY",
    "model": "google/gemini-3.5-flash",
    "system_prompt": "You are a concise terminal assistant. Answer directly and briefly. When asked for a command, give the command first, then at most one short line of explanation.",
    "temperature": 0.2,
    "list_limit": 20
  }
  ```
- Interface (illustrative): `load_config(cli_overrides: dict) -> Config`,
  `resolve_api_key(config) -> str | None`.

### `history.py`
- Reads/writes `~/.config/onesh/history.json`.
- Data structure:
  ```json
  {"conversations": [
    {
      "id": "<uuid4>",
      "created_at": "<ISO-8601>",
      "updated_at": "<ISO-8601>",
      "model": "<model used>",
      "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
      ]
    }
  ]}
  ```
  The system prompt is NOT stored in `messages`; it is added at request time by `llm.py`.
- Ordering: conversations are presented sorted by `updated_at` descending. Index `1` =
  most recently updated.
- Operations:
  - `new_conversation(model) -> conversation`
  - `most_recent() -> conversation | None`
  - `select(index: int) -> conversation` (1-based over the `updated_at`-desc ordering)
  - `append_turn(conversation, user_msg, assistant_msg)` — appends both messages and sets
    `updated_at` to now (which bumps the conversation to the top of the ordering).
  - `list_recent(limit) -> list[(index, title)]` where `title` is the first user message.
  - `save(state)`
- Timestamps are produced by injecting a clock (default real time) so tests are
  deterministic. UUIDs likewise come from an injectable factory.

### `llm.py`
- Builds an `openai.OpenAI` client with `base_url` and `api_key` from config.
- Sends `chat.completions.create(model=..., temperature=..., messages=[system, *history])`
  — non-streaming. `messages` is the conversation's stored messages with the configured
  `system_prompt` prepended.
- Optionally sets OpenRouter ranking headers (`HTTP-Referer`, `X-Title`) if present in
  config; omitted by default.
- Returns the assistant message text.
- Raises a typed error (`LLMError`) on API/network failure for the CLI to render cleanly.

### `render.py`
- `render_answer(markdown_text)` — prints the answer using `rich.markdown.Markdown`
  on a `rich.console.Console`.
- `render_list(items, console_width)` — prints the numbered conversation list, each entry
  truncated to a single terminal-width line.
- `render_error(message)` — prints a red error line to stderr.

### `cli.py`
- `main(argv=None) -> int` — parses arguments, orchestrates config → history → llm →
  render, returns an exit code.
- Argument handling (see below), then:
  1. Resolve config + API key. If key missing, render a clear error explaining how to add
     `OPENROUTER_API_KEY` to `.env`, and exit non-zero.
  2. If `-l`: load history, render the numbered list (up to `list_limit`), exit 0.
  3. Determine the target conversation:
     - no `-c` → `history.new_conversation(model)`
     - `-c` (no index) → `history.most_recent()` (error if none exists)
     - `-c N` → `history.select(N)` (error if out of range)
  4. Append the user message, call `llm`, append the assistant message, save history.
  5. Render the answer.
- Errors (missing key, no conversations to continue, bad index, LLM/network failure) are
  caught and rendered via `render_error`, returning a non-zero exit code.

## Argument parsing

The tricky case is distinguishing `onesh -c "prompt"` (continue most recent) from
`onesh -c 2 "prompt"` (continue conversation #2). Rule:

- `-c` takes an **optional** integer index. A token immediately following `-c` that is a
  bare integer is consumed as the index; anything else is left for the prompt. With no
  index, `-c` means "most recent" (index 1).
- The prompt is the remaining positional text (joined into one string).
- `-l` lists conversations and exits; a prompt is not required with `-l`.
- `--model M` overrides the configured model for this call.

This disambiguation is handled explicitly (a small custom check on the token after `-c`,
rather than relying on argparse's greedy optional-argument behavior) so both forms work
unambiguously. A prompt is required unless `-l` is given.

## Error handling

| Condition | Behavior |
|---|---|
| API key not found | Red error: how to set `OPENROUTER_API_KEY` in `.env`; exit 1 |
| `-c` with no existing conversations | Red error: nothing to continue; exit 1 |
| `-c N` out of range | Red error: show valid range; exit 1 |
| No prompt and no `-l` | Usage error; exit 2 |
| LLM / network / API failure | Red error with the underlying message; exit 1 |
| Corrupt config / history JSON | Red error naming the file to fix; exit 1 |

## Dependencies

- Runtime: `openai`, `python-dotenv`, `rich`.
- Dev: `pytest`.

## Testing

Built test-first (TDD) for the pure logic, with the network boundary mocked:

- `history.py`: new/append/select/most-recent, `updated_at`-desc ordering and top-bump on
  continue, 1-based index selection, out-of-range handling, title extraction/truncation,
  round-trip save/load. Deterministic via injected clock + uuid factory.
- `config.py`: default creation on first run, file+CLI merge precedence, API-key resolution
  (env var beats `.env`, missing key handled).
- `cli.py` argument parsing: `"q"`, `-c "q"`, `-c 2 "q"`, `-l`, `--model M "q"`, and the
  `-c "prompt"` vs `-c 2 "prompt"` disambiguation; missing-prompt usage error.
- `cli.main` smoke test with a mocked `llm` client: verifies a turn is appended and history
  saved.

`render.py` and the real network call in `llm.py` are exercised manually rather than
unit-tested for exact output.
