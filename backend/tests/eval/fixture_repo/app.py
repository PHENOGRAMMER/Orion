# fixture_repo/app.py
"""Minimal fixture application for Orion graph QA evaluation."""

from fixture_repo.parser import parse
from fixture_repo.validator import validate


def run(data: str) -> bool:
    parsed = parse(data)
    return validate(parsed)
