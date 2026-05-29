# onesh

Ask a quick question, get a one-shot answer at the terminal — instead of opening a browser.

## Setup

1. `uv sync`
2. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.

## Usage

    uv run onesh "give me the command to list files by size"
    uv run onesh -c "now sort ascending"      # continue most recent conversation
    uv run onesh -c 2 "follow up"             # continue conversation #2 from the -l list
    uv run onesh -l                           # list recent conversations
    uv run onesh --model anthropic/claude-3.5-sonnet "q"
    uv run onesh --help                       # show all flags

Config lives at `~/.config/onesh/config.json` (created on first run); history at
`~/.config/onesh/history.json`.
