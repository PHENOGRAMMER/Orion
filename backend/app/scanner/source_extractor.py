from __future__ import annotations
from pathlib import Path


def read_source_safe(file_path: Path) -> str:
    """Read a source file with UTF-8/UTF-8-SIG/UTF-16 fallback."""
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""

MAX_SOURCE_CHARS = 2000

def extract_symbol_source(
    file_path: Path,
    line: int,
    end_line: int,
    *,
    context_lines: int = 2,
    max_chars: int = MAX_SOURCE_CHARS
) -> str:
    """
    Return the source lines for a symbol, with a few lines of surrounding
    context. Lines are 1-indexed (matching Python AST lineno).
    """
    source = read_source_safe(file_path)
    if not source:
        return ""

    all_lines = source.splitlines()
    start = max(0, line - 1 - context_lines)
    end   = min(len(all_lines), end_line + context_lines)
    snippet = "\n".join(all_lines[start:end])

    if len(snippet)> max_chars:
        snippet = snippet[:max_chars] + "\n... [truncated]"
    return snippet