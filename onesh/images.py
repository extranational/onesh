import base64
import mimetypes
import os
import subprocess
import sys
import uuid
from pathlib import Path

from .config import default_config_dir


IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}


class ImageError(Exception):
    """Raised when image capture, encoding, or cache maintenance fails."""


def image_cache_dir(config_dir=None):
    base = Path(config_dir) if config_dir else default_config_dir()
    return base / "tmp-images"


def make_image_ref(path, *, mime_type=None, source=None):
    image_ref = {
        "path": str(Path(path)),
        "mime_type": mime_type or guess_mime_type(path),
    }
    if source:
        image_ref["source"] = source
    return {"type": "image_ref", "image_ref": image_ref}


def build_user_content(prompt, image_refs=None):
    image_refs = image_refs or []
    if not image_refs:
        return prompt
    return [{"type": "text", "text": prompt}, *image_refs]


def capture_clipboard_image(cache_dir=None):
    cache_dir = Path(cache_dir) if cache_dir else image_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"clipboard-{uuid.uuid4().hex}.png"
    try:
        _save_clipboard_image_as_png(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return make_image_ref(path, mime_type="image/png", source="clipboard")


def _save_clipboard_image_as_png(path):
    if sys.platform != "win32":
        raise ImageError("clipboard image capture is currently supported on Windows only")

    script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$path = $env:ONESH_CLIPBOARD_IMAGE_PATH
$image = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $image) {
    [Console]::Error.WriteLine('clipboard does not contain an image')
    exit 3
}
try {
    $image.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $image.Dispose()
}
"""
    env = dict(os.environ)
    env["ONESH_CLIPBOARD_IMAGE_PATH"] = str(path)
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            env=env,
            text=True,
            timeout=20,
        )
    except FileNotFoundError as exc:
        raise ImageError("powershell.exe is required to read clipboard images") from exc
    except subprocess.TimeoutExpired as exc:
        raise ImageError("timed out reading clipboard image") from exc

    if result.returncode != 0:
        detail = (
            result.stderr or result.stdout or "clipboard does not contain an image"
        ).strip()
        raise ImageError(detail)


def guess_mime_type(path):
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def messages_for_api(messages):
    converted = []
    for message in messages:
        api_message = dict(message)
        api_message["content"] = content_for_api(message["content"])
        converted.append(api_message)
    return converted


def content_for_api(content):
    if not isinstance(content, list):
        return content

    return [_part_for_api(part) for part in content if isinstance(part, dict)]


def _part_for_api(part):
    if part.get("type") != "image_ref":
        return part

    image_ref = part.get("image_ref") or {}
    path = Path(image_ref.get("path", ""))
    mime_type = image_ref.get("mime_type") or guess_mime_type(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ImageError(
            f"could not read image referenced in history ({path}): {exc}"
        ) from exc

    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
    }


def referenced_image_paths(state):
    paths = set()
    for conversation in state.get("conversations", []):
        for message in conversation.get("messages", []):
            for image_ref in image_refs_from_content(message.get("content")):
                path = image_ref.get("path")
                if path:
                    paths.add(Path(path))
    return paths


def image_refs_from_content(content):
    if not isinstance(content, list):
        return
    for part in content:
        if isinstance(part, dict) and part.get("type") == "image_ref":
            image_ref = part.get("image_ref")
            if isinstance(image_ref, dict):
                yield image_ref


def prune_unreferenced_images(cache_dir, referenced_paths):
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return

    cache_root = cache_dir.resolve()
    referenced = {
        Path(path).resolve()
        for path in referenced_paths
        if _is_relative_to(Path(path).resolve(), cache_root)
    }

    for candidate in cache_dir.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            if candidate.resolve() not in referenced:
                candidate.unlink()
        except OSError:
            pass


def _is_relative_to(path, parent):
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
