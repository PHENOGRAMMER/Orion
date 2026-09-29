# fixture_repo/validator.py
"""Validator stub for the fixture repository."""


def validate(tokens: list[str]) -> bool:
    """Return True when all tokens are non-empty strings."""
    return bool(tokens) and all(isinstance(t, str) and t for t in tokens)
