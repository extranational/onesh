from rich.console import Console
from rich.markdown import Markdown


def render_answer(text, console=None):
    console = console or Console()
    console.print(Markdown(text))


def render_list(items, console=None):
    console = console or Console()
    if not items:
        console.print("[dim]No conversations yet.[/dim]")
        return
    width = console.width
    for index, title in items:
        prefix = f"{index:>3}  "
        available = max(10, width - len(prefix))
        if len(title) > available:
            title = title[: available - 1] + "…"
        console.print(f"{prefix}{title}")


def render_error(message, console=None):
    console = console or Console(stderr=True)
    console.print(f"[red]error:[/red] {message}")
