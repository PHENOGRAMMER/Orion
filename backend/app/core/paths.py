"""
Filesystem path safety.

Orion's ``/graph/browse`` and ``/graph/scan`` endpoints take a path straight
from an HTTP client, which makes them the two places where a bug turns into
"any web page you visit can read your disk". Everything here exists to keep
those two endpoints inside an explicit allowlist of roots.

The important subtlety is that ``".."`` stripping is *not* enough on its own:
a symlink inside an allowed root can point anywhere. So we always
``resolve()`` first — which collapses ``..`` and follows symlinks — and only
then check containment. Checking before resolving would be trivially bypassable.

No third-party imports here, so the rules are unit testable on their own.
"""

from __future__ import annotations

import os
from pathlib import Path


class PathNotAllowed(ValueError):
    """
    Raised when a requested path resolves outside every configured root.
    """


def parse_roots(raw: str | None) -> list[Path]:
    """
    Parse a configured roots string into resolved directories.

    Accepts the OS path separator (``:`` on POSIX, ``;`` on Windows) and also
    commas, since a comma is what people reach for first in a ``.env`` file::

        ALLOWED_ROOTS=/home/me/code:/srv/repos
        ALLOWED_ROOTS=C:\\work;D:\\repos
        ALLOWED_ROOTS=/home/me/code,/srv/repos

    An empty or missing value yields an empty list, which callers should treat
    as "fall back to the default root" rather than "allow everything".
    """
    if not raw or not raw.strip():
        return []

    separators = [os.pathsep, ","]
    parts = [raw]

    for separator in separators:
        expanded: list[str] = []
        for part in parts:
            expanded.extend(part.split(separator))
        parts = expanded

    roots: list[Path] = []
    seen: set[str] = set()

    for part in parts:
        candidate = part.strip()
        if not candidate:
            continue

        try:
            resolved = Path(candidate).expanduser().resolve()
        except OSError:
            continue

        key = str(resolved)
        if key in seen:
            continue

        seen.add(key)
        roots.append(resolved)

    return roots


def is_within_roots(path: Path, roots: list[Path]) -> bool:
    """
    True when ``path`` is one of ``roots`` or sits underneath one.

    ``path`` and ``roots`` are both expected to be already resolved.
    An empty ``roots`` list denies everything — failing closed matters more
    here than convenience.
    """
    for root in roots:
        try:
            if path == root or path.is_relative_to(root):
                return True
        except (OSError, ValueError):
            continue

    return False


def safe_directory(raw_path: str, roots: list[Path]) -> Path:
    """
    Resolve ``raw_path`` and assert it is an existing directory inside ``roots``.

    Raises :class:`PathNotAllowed` on anything else, deliberately with a message
    that does not echo back whether the path merely exists — a caller probing
    for files outside the allowlist should not learn anything from the error.
    """
    try:
        resolved = Path(raw_path).expanduser().resolve()
    except OSError as exc:
        raise PathNotAllowed(f"Invalid path: {raw_path}") from exc

    if not is_within_roots(resolved, roots):
        raise PathNotAllowed(
            f"Path is outside the roots Orion is allowed to read: {raw_path}. "
            f"Add it to ALLOWED_ROOTS to permit access."
        )

    if not resolved.exists():
        raise PathNotAllowed(f"Path does not exist: {resolved}")

    if not resolved.is_dir():
        raise PathNotAllowed(f"Path is not a directory: {resolved}")

    return resolved


def default_roots() -> list[Path]:
    """
    The fallback allowlist when nothing is configured: the user's home directory.

    Chosen because the directory picker has to be able to reach the places
    people actually keep code. It is intentionally narrower than the previous
    behaviour, which was the entire filesystem.
    """
    try:
        return [Path.home().resolve()]
    except (OSError, RuntimeError):
        return []
